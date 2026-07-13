"""Facebook Marketplace Playwright connector."""

from __future__ import annotations

import hashlib
import asyncio
import os
from datetime import datetime
from decimal import Decimal
from typing import Any
from urllib.parse import quote_plus

from pricerecon.connectors.base import BaseConnector
from pricerecon.connectors.browser_client import BrowserClient
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
        radius_km: int = 25,
        headless: bool = True,
        browser_client: BrowserClient | None = None,
        max_listings_per_hour: int = 150,
    ) -> None:
        self.location = location or os.getenv("FB_MARKETPLACE_LOCATION", "United Kingdom")
        self.radius_km = radius_km
        self.headless = headless
        self.browser_client = browser_client or BrowserClient()
        self.max_listings_per_hour = max_listings_per_hour
        self._context = None
        self._page = None
        self._hourly_budget_used = 0
        self._hourly_budget_window = datetime.utcnow()
        self._last_action_at: float | None = None

    @property
    def source_role(self) -> SourceType:
        return SourceType.MARKETPLACE

    async def initialize(self) -> None:
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
        now = datetime.utcnow()
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
        location = quote_plus(str(filters.get("location") or self.location))
        radius = int(filters.get("radius_km") or self.radius_km)
        encoded = quote_plus(query)
        return (
            "https://www.facebook.com/marketplace/search/?query="
            f"{encoded}&exact=false&radius={radius}&location={location}"
        )

    async def search(
        self, query: str, filters: dict[str, Any] | None = None
    ) -> list[NormalizedListing]:
        if self._context is None or self._page is None:
            await self.initialize()
        assert self._page is not None
        await self._delay()
        try:
            await self._page.goto(
                self._search_url(query, filters), wait_until="domcontentloaded", timeout=45000
            )
            await self._page.wait_for_timeout(2500)
            cards = await self._page.locator("a[href*='/marketplace/item/']").evaluate_all(
                """els => els.map(el => {
                    const card = el.closest('div');
                    return {
                      title: (el.textContent || '').trim(),
                      url: el.href,
                      text: (card ? card.textContent : el.textContent || '') || ''
                    };
                })"""
            )
            listings: list[NormalizedListing] = []
            for idx, card in enumerate(cards):
                title = (card.get("title") or "").strip()
                if not title:
                    continue
                text = card.get("text") or ""
                price = extract_visible_gbp_price(f"{title} {text}") or Decimal("0")
                listings.append(
                    NormalizedListing(
                        source=self.connector_id,
                        source_type=SourceType.MARKETPLACE,
                        source_listing_id=hashlib.sha1(
                            (card.get("url") or title).encode()
                        ).hexdigest(),
                        title_raw=title,
                        price=price,
                        currency="GBP",
                        url=card.get("url") or "",
                        timestamp_seen=datetime.utcnow(),
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
        except ConnectorDegradedError:
            raise
        except TimeoutError as exc:
            raise ConnectorDegradedError(
                status=ConnectorStatus.timeout,
                message="Facebook Marketplace timed out",
                connector_id=self.CONNECTOR_ID,
                detail={"error": str(exc)},
            ) from exc
        except Exception as exc:
            text = str(exc).lower()
            if "checkpoint" in text or "login" in text:
                raise ConnectorDegradedError(
                    status=ConnectorStatus.bot_blocked,
                    message="Facebook Marketplace blocked the session",
                    connector_id=self.CONNECTOR_ID,
                    detail={"error": str(exc)},
                ) from exc
            if "auth" in text:
                raise ConnectorDegradedError(
                    status=ConnectorStatus.auth_failed,
                    message="Facebook Marketplace auth failed",
                    connector_id=self.CONNECTOR_ID,
                    detail={"error": str(exc)},
                ) from exc
            if "parse" in text or "selector" in text:
                raise ConnectorDegradedError(
                    status=ConnectorStatus.parse_error,
                    message="Facebook Marketplace parsing failed",
                    connector_id=self.CONNECTOR_ID,
                    detail={"error": str(exc)},
                ) from exc
            raise ConnectorDegradedError(
                status=ConnectorStatus.unknown_error,
                message="Facebook Marketplace search failed",
                connector_id=self.CONNECTOR_ID,
                detail={"error": str(exc)},
            ) from exc
