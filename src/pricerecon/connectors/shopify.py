"""Store-specific Shopify storefront connector and detection helpers."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from urllib.parse import quote_plus

import httpx

from pricerecon.connectors.base import BaseConnector
from pricerecon.connectors.specs import extract_specs
from pricerecon.connectors.status import ConnectorDegradedError, ConnectorStatus
from pricerecon.models import NormalizedListing, SourceType


class ShopifyConnector(BaseConnector):

    def __init__(self, base_url: str | None = None, store_url: str | None = None) -> None:
        self.base_url = (base_url or store_url or "").rstrip("/")
        self._client = httpx.AsyncClient(timeout=30.0)

    @property
    def source_role(self) -> SourceType:
        return SourceType.RETAILER

    async def initialize(self) -> None:
        return None

    async def cleanup(self) -> None:
        await self._client.aclose()

    @property
    def connector_id(self) -> str:
        return "shopify"

    def detect(self, headers: httpx.Headers, body: str) -> bool:
        return any(key.lower().startswith("x-shop") for key in headers.keys()) or "Shopify" in body

    async def search(
        self, query: str, filters: dict[str, Any] | None = None
    ) -> list[NormalizedListing]:
        if not self.base_url:
            raise ConnectorDegradedError(
                status=ConnectorStatus.auth_failed,
                message="shopify requires base_url (or store_url) for a specific storefront",
                connector_id=self.connector_id,
                detail={"missing": ["base_url"], "accepted_keys": ["base_url", "store_url"]},
            )
        await self._client.get(
            f"{self.base_url}/search?q={quote_plus(query)}&type=product",
            headers={"User-Agent": "Mozilla/5.0 (compatible; PriceRecon/1.0)"},
        )
        response = await self._client.get(
            f"{self.base_url}/products.json?limit=250",
            headers={"User-Agent": "Mozilla/5.0 (compatible; PriceRecon/1.0)"},
        )
        response.raise_for_status()
        payload = response.json()
        return self._products_to_listings(payload.get("products", []))

    async def fetch_variant_prices(self, handle: str) -> list[dict[str, Any]]:
        response = await self._client.get(
            f"{self.base_url}/products/{handle}.json",
            headers={"User-Agent": "Mozilla/5.0 (compatible; PriceRecon/1.0)"},
        )
        response.raise_for_status()
        payload = response.json()
        return payload.get("product", {}).get("variants", [])  # type: ignore[no-any-return]

    def _products_to_listings(self, products: list[dict[str, Any]]) -> list[NormalizedListing]:
        listings: list[NormalizedListing] = []
        for product in products:
            handle = product.get("handle")
            if not handle:
                continue
            title = product.get("title", "")
            product_image = product.get("image") or {}
            if isinstance(product_image, list):
                product_image = product_image[0] if product_image else {}
            for variant in product.get("variants", []):
                listings.append(
                    NormalizedListing(
                        source=self.connector_id,
                        source_type=SourceType.RETAILER,
                        source_listing_id=str(variant.get("id") or handle),
                        title_raw=title,
                        price=Decimal(str(variant.get("price") or "0")),
                        currency=(variant.get("currency") or "GBP").upper(),
                        url=f"{self.base_url}/products/{handle}",
                        timestamp_seen=datetime.utcnow(),
                        product_normalized=title,
                        variant_normalized={
                            "shopify_variant_title": variant.get("title") or title,
                            **extract_specs(
                                f"{title} {variant.get('title') or ''}", product.get("product_type")
                            ),
                        },
                        condition=None,
                        condition_raw=None,
                        shipping_cost=None,
                        total_landed_cost=None,
                        seller_or_store=self.base_url.replace("https://", "").replace(
                            "http://", ""
                        ),
                        seller_feedback_score=None,
                        seller_feedback_pct=None,
                        location=None,
                        in_stock=variant.get("available"),
                        stock_state=None,
                        image_url=(
                            product_image.get("src") if isinstance(product_image, dict) else None
                        ),
                        exact_variant_confirmed=None,
                        variant_match_confidence=None,
                        mismatch_flags=None,
                        risk_flags=None,
                        category=product.get("product_type"),
                    )
                )
        return listings
