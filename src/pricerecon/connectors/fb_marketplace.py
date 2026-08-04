"""Facebook Marketplace Playwright connector."""

from __future__ import annotations

import hashlib
import asyncio
import os
from datetime import datetime, timezone
from typing import Any
from urllib.parse import quote_plus

from pricerecon.connectors.base import BaseConnector
from pricerecon.connectors.browser_client import BrowserClient
from pricerecon.connectors.external_browser import as_connector_degraded_error
from pricerecon.connectors.price import extract_visible_gbp_price
from pricerecon.connectors.status import ConnectorDegradedError, ConnectorStatus
from pricerecon.models import NormalizedListing, SourceType


class FacebookMarketplaceConnector(BaseConnector):
    """Playwright-backed Facebook Marketplace connector."""

    CONNECTOR_ID = "facebook_marketplace"

    def __init__(
        self,
        *,
        location: str | None = None,
        latitude: float | None = None,
        longitude: float | None = None,
        radius_km: int = 25,
        headless: bool = True,
        browser_client: BrowserClient | None = None,
        max_listings_per_hour: int = 150,
    ) -> None:
        self.location = location or os.getenv("FB_MARKETPLACE_LOCATION")
        lat_env = os.getenv("FB_MARKETPLACE_LAT")
        lon_env = os.getenv("FB_MARKETPLACE_LON")
        self.latitude = latitude if latitude is not None else (float(lat_env) if lat_env else None)
        self.longitude = (
            longitude if longitude is not None else (float(lon_env) if lon_env else None)
        )
        self.radius_km = radius_km
        self.headless = headless
        self.browser_client = browser_client or BrowserClient()
        self.max_listings_per_hour = max_listings_per_hour
        self._context = None
        self._page = None
        self._hourly_budget_used = 0
        self._hourly_budget_window = datetime.now(timezone.utc)
        self._last_action_at: float | None = None
        self._validate_location()

    def _validate_location(self) -> None:
        """Validate coordinates are present and in range, or raise a clear error."""
        if self.latitude is None or self.longitude is None:
            raise ConnectorDegradedError(
                status=ConnectorStatus.unknown_error,
                message=(
                    "facebook_marketplace requires latitude and longitude. "
                    "Set them in sources[].config, "
                    "connectors.facebook_marketplace, or "
                    "FB_MARKETPLACE_LAT / FB_MARKETPLACE_LON env vars."
                ),
                connector_id=self.CONNECTOR_ID,
            )
        if not -90 <= self.latitude <= 90:
            raise ConnectorDegradedError(
                status=ConnectorStatus.unknown_error,
                message=f"latitude {self.latitude} out of range (-90 to 90)",
                connector_id=self.CONNECTOR_ID,
            )
        if not -180 <= self.longitude <= 180:
            raise ConnectorDegradedError(
                status=ConnectorStatus.unknown_error,
                message=f"longitude {self.longitude} out of range (-180 to 180)",
                connector_id=self.CONNECTOR_ID,
            )
        if self.radius_km <= 0:
            raise ConnectorDegradedError(
                status=ConnectorStatus.unknown_error,
                message=f"radius_km must be positive, got {self.radius_km}",
                connector_id=self.CONNECTOR_ID,
            )

    @property
    def source_role(self) -> SourceType:
        return SourceType.MARKETPLACE

    async def initialize(self) -> None:
        """Initialize only the acquisition path selected by configuration."""
        if self.has_external_browser():
            return
        cookies = self._build_cookies()
        self._context = await self.browser_client.new_context(cookies=cookies)
        self._page = await self._context.new_page() if self._context is not None else None

    async def cleanup(self) -> None:
        if self._page is not None:
            await self._page.close()
            self._page = None
        if self._context is not None:
            await self._context.close()
            self._context = None
        if not self.has_external_browser():
            await self.browser_client.close()

    def _build_cookies(self) -> list[dict[str, Any]]:
        required = {
            "c_user": os.getenv("FB_C_USER"),
            "xs": os.getenv("FB_XS"),
            "datr": os.getenv("FB_DATR"),
            "fr": os.getenv("FB_FR"),
            "sb": os.getenv("FB_SB"),
        }
        missing = [name for name, value in required.items() if not value]
        if missing:
            raise ConnectorDegradedError(
                status=ConnectorStatus.auth_failed,
                message=f"Missing Facebook Marketplace cookies: {', '.join(missing)}",
                connector_id=self.CONNECTOR_ID,
                detail={"missing": missing},
            )
        return [
            {"name": name, "value": value or "", "domain": ".facebook.com", "path": "/"}
            for name, value in required.items()
        ]

    async def _delay(self) -> None:
        now = datetime.now(timezone.utc)
        if (now - self._hourly_budget_window).total_seconds() >= 3600:
            self._hourly_budget_window = now
            self._hourly_budget_used = 0
        if self._hourly_budget_used >= self.max_listings_per_hour:
            raise ConnectorDegradedError(
                status=ConnectorStatus.rate_limited,
                message="Facebook Marketplace hourly cap reached",
                connector_id=self.CONNECTOR_ID,
            )
        self._hourly_budget_used += 1
        loop_time = asyncio.get_running_loop().time()
        if self._last_action_at is not None:
            elapsed = loop_time - self._last_action_at
            if elapsed < 2.5:
                await asyncio.sleep(2.5 - elapsed)
        self._last_action_at = asyncio.get_running_loop().time()

    def _search_url(self, query: str, filters: dict[str, Any] | None = None) -> str:
        filters = filters or {}
        latitude = filters.get("latitude") or self.latitude
        longitude = filters.get("longitude") or self.longitude
        radius = int(filters.get("radius_km") or self.radius_km)
        encoded = quote_plus(query)
        # Facebook Marketplace search uses lat/lon coordinates, not a place
        # name string.  Using a name like "United Kingdom" silently defaults
        # to Meta HQ (Menlo Park, CA) and returns US listings.
        return (
            "https://www.facebook.com/marketplace/search/?query="
            f"{encoded}&exact=false&radius={radius}"
            f"&latitude={latitude}&longitude={longitude}"
        )

    def _parse_external_html(self, html: str) -> list[NormalizedListing]:
        """Parse rendered Marketplace cards without changing listing semantics."""
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")
        cards = [
            {
                "title": link.get_text(" ", strip=True),
                "url": str(link.get("href") or ""),
                "text": link.parent.get_text(" ", strip=True) if link.parent else "",
            }
            for link in soup.select("a[href*='/marketplace/item/']")
        ]
        return self._cards_to_listings(cards)

    def _cards_to_listings(self, cards: list[dict[str, str]]) -> list[NormalizedListing]:
        """Normalize cards shared by local and external-browser acquisitions."""
        listings: list[NormalizedListing] = []
        for card in cards:
            title = (card.get("title") or "").strip()
            if not title:
                continue
            text = card.get("text") or ""
            price = extract_visible_gbp_price(f"{title} {text}")
            listings.append(
                NormalizedListing(
                    source=self.connector_id,
                    source_type=SourceType.MARKETPLACE,
                    source_listing_id=hashlib.sha1((card.get("url") or title).encode()).hexdigest(),
                    title_raw=title,
                    price=price,
                    currency="GBP" if price is not None else "UNK",
                    url=card.get("url") or "",
                    timestamp_seen=datetime.now(timezone.utc),
                    seller_or_store=None,
                    location=self.location,
                    product_normalized=None,
                    variant_normalized=None,
                    condition=None,
                    condition_raw=None,
                    shipping_cost=None,
                    total_landed_cost=None,
                    seller_feedback_score=None,
                    seller_feedback_pct=None,
                    in_stock=None,
                    stock_state=None,
                    image_url=None,
                    exact_variant_confirmed=None,
                    variant_match_confidence=None,
                    mismatch_flags=None,
                    risk_flags=None,
                    category=None,
                )
            )
        return listings

    async def search(
        self, query: str, filters: dict[str, Any] | None = None
    ) -> list[NormalizedListing]:
        external_url = self._search_url(query, filters)
        browser_result = await self.navigate_external_browser(external_url)
        if browser_result is None:
            raise ConnectorDegradedError(
                status=ConnectorStatus.unknown_error,
                message="Facebook Marketplace requires a configured external browser backend",
                connector_id=self.connector_id,
                detail={"missing": ["browser_backend"]},
            )
        if browser_result.degraded or not browser_result.rendered.html:
            raise as_connector_degraded_error(browser_result, self.connector_id)
        external_listings = self._parse_external_html(browser_result.rendered.html)
        if not external_listings:
            raise ConnectorDegradedError(
                status=ConnectorStatus.parse_error,
                message="Facebook Marketplace browser content contained no listing cards",
                connector_id=self.connector_id,
                detail=self.browser_result_detail(browser_result),
            )
        return self.annotate_browser_result(external_listings, browser_result)
