"""Generic connector base for HTML template-driven retailers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus

import httpx
import yaml

from pricerecon.connectors.base import BaseConnector
from pricerecon.connectors.flaresolverr import FlareSolverrClient
from pricerecon.connectors.html import SelectorConfig, parse_listings_from_html
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


class TemplateConnector(BaseConnector):
    template_name: str = ""
    connector_id_override: str | None = None

    def __init__(self, *, flaresolverr_url: str | None = None, base_url: str | None = None) -> None:
        config = self._load_yaml(self.template_name)
        self.template = TemplateDefinition(
            name=config.get("name", self.template_name),
            source_type=SourceType(config.get("source_type", "retailer")),
            base_url=(base_url or config["base_url"]).rstrip("/"),
            search_url=config["search_url"],
            selectors=SelectorConfig(**config["selectors"]),
            pagination_next=config.get("pagination_next"),
            use_flare_solverr=bool(config.get("use_flare_solverr", False)),
            flaresolverr_url=flaresolverr_url or config.get("flaresolverr_url"),
            category=config.get("category"),
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
                raise ValueError(f"{self.template_name} requires flaresolverr_url")
            client = FlareSolverrClient(endpoint)
            return await client.request_html(url)

        response = await self._client.get(url, headers={"User-Agent": "Mozilla/5.0 (compatible; PriceRecon/1.0)"})
        response.raise_for_status()
        return response.text

    async def search(self, query: str, filters: dict[str, Any] | None = None) -> list[NormalizedListing]:
        html = await self._fetch_html(self._format_search_url(query))
        return parse_listings_from_html(
            html,
            base_url=self.template.base_url,
            source=self.connector_id,
            source_type=self.template.source_type,
            selector=self.template.selectors,
            category=self.template.category,
        )

    async def initialize(self) -> None:
        return None

    async def cleanup(self) -> None:
        await self._client.aclose()
