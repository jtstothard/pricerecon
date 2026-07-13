"""Dell UK connector backed by Playwright browser rendering.

Dell's public UK listings are accessible in a browser but often block direct HTTP
fetches and rely on dynamic page content. This connector uses the shared browser
client, parses visible product cards, and normalizes the result set for laptops
and other Dell UK product listing pages.
"""

from __future__ import annotations

import hashlib
import logging
import re
from decimal import Decimal, InvalidOperation
from typing import Any
from urllib.parse import quote_plus, urljoin, urlparse

from selectolax.parser import HTMLParser

from pricerecon.connectors.base import BaseConnector
from pricerecon.connectors.browser_client import BrowserClient
from pricerecon.connectors.status import ConnectorDegradedError, ConnectorStatus
from pricerecon.connectors.specs import extract_specs
from pricerecon.models import NormalizedListing, SourceType, StockState

logger = logging.getLogger(__name__)

_PRICE_PATTERNS = (
    re.compile(r"Dell Price\s*£(?P<amount>\d[\d,]*(?:\.\d{1,2})?)", re.IGNORECASE),
    re.compile(r"Base model from\s*£(?P<amount>\d[\d,]*(?:\.\d{1,2})?)", re.IGNORECASE),
    re.compile(r"Starting at\s*£(?P<amount>\d[\d,]*(?:\.\d{1,2})?)", re.IGNORECASE),
    re.compile(r"Price\s*£(?P<amount>\d[\d,]*(?:\.\d{1,2})?)", re.IGNORECASE),
    re.compile(r"£(?P<amount>\d[\d,]*(?:\.\d{1,2})?)", re.IGNORECASE),
)

_ORDER_CODE_RE = re.compile(r"Order Code\s+([A-Za-z0-9_-]+)", re.IGNORECASE)


class DellUKConnector(BaseConnector):
    """Playwright-backed Dell UK connector for product listing pages."""

    CONNECTOR_ID = "dell_uk"
    BASE_URL = "https://www.dell.com/en-uk"
    DEFAULT_LISTING_URL = "https://www.dell.com/en-uk/search/laptops"

    def __init__(self, *, browser_client: BrowserClient | None = None) -> None:
        self._browser_client = browser_client or BrowserClient()
        self._owns_browser_client = browser_client is None

    @property
    def source_role(self) -> SourceType:
        return SourceType.RETAILER

    async def initialize(self) -> None:
        return None

    async def cleanup(self) -> None:
        if self._owns_browser_client:
            await self._browser_client.close()

    def _listing_url(self, query: str, filters: dict[str, Any] | None = None) -> str:
        filters = filters or {}
        for key in ("listing_url", "category_url", "url"):
            value = filters.get(key)
            if value:
                return str(value)

        path = filters.get("path") or filters.get("category_path")
        if path:
            path = str(path).lstrip("/")
            base = self.BASE_URL.rstrip("/")
            if path.startswith("http://") or path.startswith("https://"):
                return path
            return f"{base}/{path}"

        if query.strip():
            return f"{self.DEFAULT_LISTING_URL}?text={quote_plus(query)}"
        return self.DEFAULT_LISTING_URL

    async def search(
        self, query: str, filters: dict[str, Any] | None = None
    ) -> list[NormalizedListing]:
        filters = filters or {}
        url = self._listing_url(query, filters)

        try:
            context = await self._browser_client.new_context()
            page = await context.new_page()
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=45000)
                await page.wait_for_timeout(1500)
                html = await page.content()
            finally:
                await context.close()
        except ConnectorDegradedError:
            raise
        except Exception as exc:
            logger.error("Dell UK search failed: %s", exc)
            raise ConnectorDegradedError(
                status=ConnectorStatus.unknown_error,
                message="Dell UK search failed",
                connector_id=self.connector_id,
                detail={"error": str(exc), "url": url},
            ) from exc

        listings = self._parse_listings(html, query, url)
        if not listings:
            raise ConnectorDegradedError(
                status=ConnectorStatus.parse_error,
                message="Dell UK listing parse returned no products",
                connector_id=self.connector_id,
                detail={"url": url},
            )
        return listings

    def _parse_listings(self, html: str, query: str, url: str) -> list[NormalizedListing]:
        parser = HTMLParser(html)
        listings: list[NormalizedListing] = []
        seen_ids: set[str] = set()

        for card in parser.css("article"):
            card_text = re.sub(r"\s+", " ", card.text(separator=" ", strip=True)).strip()
            if not card_text:
                continue

            title_node = self._find_title_node(card)
            if title_node is None:
                continue

            title = re.sub(r"\s+", " ", title_node.text(separator=" ", strip=True)).strip()
            href = title_node.attributes.get("href") if title_node.attributes else None
            if not title or not href:
                continue

            listing_url = self._absolute_url(href)
            source_listing_id = self._source_listing_id(listing_url, card_text)
            if source_listing_id in seen_ids:
                continue

            price = self._extract_price(card_text)
            if price is None:
                continue

            seen_ids.add(source_listing_id)
            variant = extract_specs(f"{title} {card_text}", "laptop")
            in_stock = (
                None if re.search(r"out of stock|sold out|unavailable", card_text, re.I) else True
            )

            listings.append(
                NormalizedListing(
                    source=self.connector_id,
                    source_type=self.source_role,
                    source_listing_id=source_listing_id,
                    title_raw=title,
                    price=price,
                    currency="GBP",
                    url=listing_url,
                    product_normalized=title,
                    variant_normalized=variant,
                    condition=None,
                    condition_raw=None,
                    shipping_cost=None,
                    total_landed_cost=None,
                    seller_or_store="Dell UK",
                    seller_feedback_score=None,
                    seller_feedback_pct=None,
                    location=None,
                    in_stock=in_stock,
                    stock_state=StockState.IN_STOCK if in_stock else StockState.OUT_OF_STOCK,
                    image_url=self._image_url(card),
                    exact_variant_confirmed=None,
                    variant_match_confidence=None,
                    mismatch_flags=None,
                    risk_flags=None,
                    category=variant.get("category") or "laptop",
                )
            )

        return listings

    def _find_title_node(self, card):
        for selector in (
            "h1 a[href]",
            "h2 a[href]",
            "h3 a[href]",
            "a[href*='/spd/']",
            "a[href*='/shop/laptops-2-in-1-pcs/']",
        ):
            node = card.css_first(selector)
            if node is not None:
                return node
        return None

    def _extract_price(self, card_text: str) -> Decimal | None:
        normalized = card_text.replace("\xa0", " ")
        for pattern in _PRICE_PATTERNS:
            match = pattern.search(normalized)
            if not match:
                continue
            try:
                return Decimal(match.group("amount").replace(",", ""))
            except (InvalidOperation, ValueError):
                continue
        return None

    def _source_listing_id(self, listing_url: str, card_text: str) -> str:
        order_code = _ORDER_CODE_RE.search(card_text)
        if order_code:
            return order_code.group(1)
        parsed = urlparse(listing_url)
        slug = parsed.path.rstrip("/").split("/")[-1]
        if slug:
            return slug
        return hashlib.sha1(listing_url.encode()).hexdigest()

    def _absolute_url(self, href: str) -> str:
        if href.startswith("//"):
            return f"https:{href}"
        return urljoin(self.BASE_URL, href)

    def _image_url(self, card) -> str | None:
        image = card.css_first("img")
        if image is None:
            return None
        src = image.attributes.get("src") or image.attributes.get("data-src")
        if not src:
            return None
        return self._absolute_url(src)
