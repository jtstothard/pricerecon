"""Generic connector base for HTML template-driven retailers."""

from __future__ import annotations

import os
import json
import re
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus

import httpx
import yaml
from pricerecon.config import load_config
from pricerecon.connectors.base import BaseConnector
from pricerecon.connectors.flaresolverr import FlareSolverrClient
from pricerecon.connectors.html import SelectorConfig, parse_listings_from_html
from pricerecon.connectors.status import ConnectorDegradedError, ConnectorStatus
from pricerecon.models import NormalizedListing, SourceType

TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"


@dataclass(slots=True)
class TemplateDefinition:
    name: str
    source_type: SourceType
    base_url: str
    search_url: str
    selectors: SelectorConfig
    pagination_next: str | None = None
    use_flare_solverr: bool = False
    flaresolverr_url: str | None = None
    category: str | None = None
    disabled: bool = False
    disabled_reason: str | None = None


class TemplateConnector(BaseConnector):
    template_name: str = ""
    connector_id_override: str | None = None

    def __init__(self, *, flaresolverr_url: str | None = None, base_url: str | None = None) -> None:
        template_config = self._load_yaml(self.template_name)
        runtime_config = load_config()
        self.template = TemplateDefinition(
            name=template_config.get("name", self.template_name),
            source_type=SourceType(template_config.get("source_type", "retailer")),
            base_url=(base_url or template_config["base_url"]).rstrip("/"),
            search_url=template_config["search_url"],
            selectors=SelectorConfig(**template_config["selectors"]),
            pagination_next=template_config.get("pagination_next"),
            use_flare_solverr=bool(template_config.get("use_flare_solverr", False)),
            flaresolverr_url=(
                flaresolverr_url
                or os.getenv("PRICERECON_FLARESOLVERR_URL")
                or runtime_config.get("flaresolverr_url")
                or template_config.get("flaresolverr_url")
            ),
            category=template_config.get("category"),
            disabled=bool(template_config.get("disabled", False)),
            disabled_reason=template_config.get("disabled_reason"),
        )
        self._client = httpx.AsyncClient(timeout=30.0)

    @property
    def source_role(self) -> SourceType:
        return self.template.source_type

    @property
    def connector_id(self) -> str:
        return self.connector_id_override or self.template_name

    @classmethod
    def _load_yaml(cls, name: str) -> dict[str, Any]:
        path = TEMPLATE_DIR / f"{name}.yml"
        if not path.exists():
            raise FileNotFoundError(f"Missing connector template: {path}")
        return yaml.safe_load(path.read_text()) or {}

    def _format_search_url(self, query: str) -> str:
        return self.template.search_url.format(query=quote_plus(query))

    async def _fetch_html(self, url: str) -> str:
        if self.template.use_flare_solverr:
            endpoint = self.template.flaresolverr_url
            if not endpoint:
                raise ConnectorDegradedError(
                    status=ConnectorStatus.auth_failed,
                    message=f"{self.template_name} requires flaresolverr_url",
                    connector_id=self.connector_id,
                    detail={"missing": ["flaresolverr_url"]},
                )
            client = FlareSolverrClient(endpoint)
            try:
                return await client.request_html(url)
            except httpx.ConnectTimeout as exc:
                raise ConnectorDegradedError(
                    status=ConnectorStatus.timeout,
                    message=f"{self.template_name} FlareSolverr connection timed out",
                    connector_id=self.connector_id,
                    detail={"endpoint": endpoint, "url": url, "error": str(exc)},
                ) from exc
            except httpx.ReadTimeout as exc:
                raise ConnectorDegradedError(
                    status=ConnectorStatus.timeout,
                    message=f"{self.template_name} FlareSolverr response timed out",
                    connector_id=self.connector_id,
                    detail={"endpoint": endpoint, "url": url, "error": str(exc)},
                ) from exc
            except httpx.HTTPError as exc:
                raise ConnectorDegradedError(
                    status=ConnectorStatus.unknown_error,
                    message=f"{self.template_name} FlareSolverr request failed",
                    connector_id=self.connector_id,
                    detail={"endpoint": endpoint, "url": url, "error": str(exc)},
                ) from exc

        response = await self._client.get(
            url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; PriceRecon/1.0)"},
        )
        response.raise_for_status()
        return response.text

    async def search(
        self, query: str, filters: dict[str, Any] | None = None
    ) -> list[NormalizedListing]:
        if self.template.disabled:
            reason = self.template.disabled_reason or "connector is disabled pending revalidation"
            raise ConnectorDegradedError(
                status=ConnectorStatus.disabled,
                message=f"{self.connector_id} is disabled: {reason}",
                connector_id=self.connector_id,
                detail={"reason": reason, "base_url": self.template.base_url},
            )
        html = await self._fetch_html(self._format_search_url(query))
        # Ebuyer: parse client-side productImpressions JSON data
        if self.connector_id == "ebuyer":
            return self._parse_ebuyer_json(html)
        return parse_listings_from_html(
            html,
            base_url=self.template.base_url,
            source=self.connector_id,
            source_type=self.template.source_type,
            selector=self.template.selectors,
            category=self.template.category,
        )

    def _parse_ebuyer_json(self, html: str) -> list[NormalizedListing]:
        """Parse Ebuyer's client-side productImpressions search data.

        NOTE: product_id format (e.g., '73468903-2267377') does not map to real product URLs.
        Current best-effort: report base search URL in url field. A proper fix requires
        mapping product codes to their detail pages, which selectors cannot provide.
        """
        match = re.search(r"var ecommerceData = ({.*?});", html, re.DOTALL)
        if not match:
            return []
        try:
            impressions = json.loads(match.group(1)).get("ecommerce", {}).get("impressions", [])
        except json.JSONDecodeError:
            return []

        listings: list[NormalizedListing] = []
        for item in impressions:
            name = str(item.get("name", "")).strip()
            product_id = str(item.get("id", "")).strip()
            try:
                price = Decimal(str(item.get("price", "")).replace(",", ""))
            except (ArithmeticError, ValueError):
                continue
            if not name or not product_id:
                continue
            listings.append(
                NormalizedListing(
                    source=self.connector_id,
                    source_type=self.template.source_type,
                    source_listing_id=product_id,
                    title_raw=name,
                    price=price,
                    currency="GBP",
                    url=f"{self.template.base_url}/searchresults?descriptionfilter={quote_plus(name)}",  # fallback to search query
                    product_normalized=None,
                    variant_normalized=None,
                    condition=None,
                    condition_raw=None,
                    shipping_cost=None,
                    total_landed_cost=None,
                    seller_or_store=None,
                    seller_feedback_score=None,
                    seller_feedback_pct=None,
                    location=None,
                    in_stock=None,
                    stock_state=None,
                    image_url=None,
                    exact_variant_confirmed=None,
                    variant_match_confidence=None,
                    mismatch_flags=None,
                    risk_flags=None,
                    category=self.template.category,
                )
            )
        return listings

    async def initialize(self) -> None:
        return None
