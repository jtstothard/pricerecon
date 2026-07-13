"""John Lewis UK connector."""

from __future__ import annotations

import re
from decimal import Decimal
from typing import Any
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup
from bs4.element import Tag

from pricerecon.connectors.base import BaseConnector
from pricerecon.connectors.specs import extract_specs
from pricerecon.models import NormalizedListing, SourceType

_PRICE_RE = re.compile(r"£\s?([\d,]+(?:\.\d{2})?)")


class JohnLewisConnector(BaseConnector):
    CONNECTOR_ID = "johnlewis"
    BASE_URL = "https://www.johnlewis.com"

    def __init__(
        self, base_url: str | None = None, client: httpx.AsyncClient | None = None
    ) -> None:
        self.base_url = (base_url or self.BASE_URL).rstrip("/")
        self._client = client or httpx.AsyncClient(timeout=30.0)
        self._owns_client = client is None

    @property
    def source_role(self) -> SourceType:
        return SourceType.RETAILER

    async def cleanup(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def search(
        self, query: str, filters: dict[str, Any] | None = None
    ) -> list[NormalizedListing]:
        filters = filters or {}
        response = await self._client.get(
            f"{self.base_url}/search",
            params={"search-term": query},
            headers={"User-Agent": "Mozilla/5.0 (compatible; PriceRecon/1.0)"},
        )
        response.raise_for_status()
        return self._parse_search_results(response.text, filters)

    def _parse_search_results(
        self, html: str, filters: dict[str, Any] | None = None
    ) -> list[NormalizedListing]:
        filters = filters or {}
        soup = BeautifulSoup(html, "html.parser")
        listings: list[NormalizedListing] = []
        seen_ids: set[str] = set()

        for card in soup.select("article[data-product-id]"):
            if not isinstance(card, Tag):
                continue
            product_id = str(card.get("data-product-id") or card.get("id") or "").strip()
            if not product_id or product_id in seen_ids:
                continue

            title_link = card.select_one('a[href*="/p"]')
            if not isinstance(title_link, Tag):
                continue

            title = self._extract_title(card)
            if not title:
                continue

            price = self._extract_price(card)
            if price is None:
                continue

            href = str(title_link.get("href") or "").strip()
            if not href:
                continue

            image = card.select_one("img[alt]")
            image_url = None
            if isinstance(image, Tag):
                src = image.get("src") or image.get("data-src")
                if src:
                    image_url = urljoin(self.base_url, str(src))

            listings.append(
                NormalizedListing.model_validate(
                    {
                        "source": self.connector_id,
                        "source_type": self.source_role,
                        "source_listing_id": product_id,
                        "title_raw": title,
                        "price": price,
                        "currency": "GBP",
                        "url": urljoin(self.base_url, href),
                        "product_normalized": title,
                        "variant_normalized": {
                            "johnlewis_product_id": product_id,
                            "title_normalized": title,
                            **extract_specs(title, filters.get("category")),
                        },
                        "seller_or_store": "John Lewis & Partners",
                        "in_stock": self._infer_in_stock(card),
                        "condition": None,
                        "condition_raw": None,
                        "shipping_cost": None,
                        "total_landed_cost": None,
                        "seller_feedback_score": None,
                        "seller_feedback_pct": None,
                        "location": None,
                        "stock_state": None,
                        "image_url": image_url,
                        "exact_variant_confirmed": None,
                        "variant_match_confidence": None,
                        "mismatch_flags": None,
                        "risk_flags": None,
                        "category": filters.get("category"),
                    }
                )
            )
            seen_ids.add(product_id)

        return listings

    def _extract_title(self, card: Tag) -> str:
        for selector in [
            'a[href*="/p"] h2',
            'a[href*="/p"] [data-testid="product-title"]',
            'a[href*="/p"]',
            "img[alt]",
        ]:
            node = card.select_one(selector)
            if not isinstance(node, Tag):
                continue
            if selector == "img[alt]":
                text = str(node.get("alt") or "")
            else:
                text = str(node.get_text(" ", strip=True) or node.get("aria-label") or "")
            text = re.sub(r"\s+", " ", text).strip()
            if text and text.lower() not in {"quick view", "product image carousel"}:
                return text
        return ""

    def _extract_price(self, card: Tag) -> Decimal | None:
        price_text = ""
        for node in card.find_all(string=True):
            text = str(node)
            if "£" not in text:
                continue
            match = _PRICE_RE.search(text.replace("\xa0", " "))
            if match:
                price_text = match.group(1)
                break
        if not price_text:
            price_nodes = card.select("p, span, div")
            for node in price_nodes:
                if not isinstance(node, Tag):
                    continue
                text = node.get_text(" ", strip=True)
                match = _PRICE_RE.search(text.replace("\xa0", " "))
                if match:
                    price_text = match.group(1)
                    break
        if not price_text:
            return None
        return Decimal(price_text.replace(",", ""))

    def _infer_in_stock(self, card: Tag) -> bool | None:
        text = card.get_text(" ", strip=True).lower()
        if "out of stock" in text or "sold out" in text:
            return False
        if "add to basket" in text or "add to bag" in text or "in stock" in text:
            return True
        return None
