"""Reddit connector with OAuth JSON and RSS fallback support."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Optional

import httpx

from pricerecon.connectors.base import BaseConnector
from pricerecon.connectors.rss import parse_feed, parse_hardwareswapuk_post
from pricerecon.models import NormalizedListing, SourceType


class RedditConnector(BaseConnector):
    CONNECTOR_ID = "reddit"

    def __init__(
        self,
        subreddit: str = "hardwareswapuk",
        *,
        source_role: SourceType = SourceType.MARKETPLACE,
        access_token: str | None = None,
        user_agent: str = "PriceRecon/0.1",
        endpoint_mode: str = "search",
        limit: int = 25,
    ) -> None:
        self.subreddit = subreddit
        self._source_role = source_role
        self.access_token = access_token
        self.user_agent = user_agent
        self.endpoint_mode = endpoint_mode
        self.limit = limit
        self._client = httpx.AsyncClient(timeout=30.0)

    @property
    def source_role(self) -> SourceType:
        return self._source_role

    async def initialize(self) -> None:
        return None

    async def cleanup(self) -> None:
        await self._client.aclose()

    async def search(self, query: str, filters: Optional[dict[str, Any]] = None) -> list[NormalizedListing]:
        filters = filters or {}
        limit = int(filters.get("limit") or self.limit)
        if self.access_token:
            items = await self._fetch_oauth_items(query=query, limit=limit)
            return [self._item_to_listing(item, query=query) for item in items]

        entries = await self._fetch_rss_entries(query=query, limit=limit)
        return [self._entry_to_listing(entry, query=query) for entry in entries]

    async def _fetch_oauth_items(self, *, query: str, limit: int) -> list[dict[str, Any]]:
        endpoint = "search"
        params: dict[str, Any]
        if self.endpoint_mode == "new":
            endpoint = "new"
            params = {"limit": limit}
        else:
            params = {"q": query, "sort": "new", "limit": limit, "restrict_sr": 1}

        response = await self._client.get(
            f"https://oauth.reddit.com/r/{self.subreddit}/{endpoint}",
            headers={
                "Authorization": f"Bearer {self.access_token}",
                "User-Agent": self.user_agent,
            },
            params=params,
        )
        response.raise_for_status()
        payload = response.json() or {}
        children = payload.get("data", {}).get("children", [])
        return [child.get("data", {}) for child in children if isinstance(child, dict)]

    async def _fetch_rss_entries(self, *, query: str, limit: int) -> list[Any]:
        endpoint = "new.rss" if self.endpoint_mode == "new" else "search.rss"
        params: dict[str, Any]
        if self.endpoint_mode == "new":
            params = {"limit": limit}
        else:
            params = {"q": query, "sort": "new", "limit": limit, "restrict_sr": 1}
        response = await self._client.get(
            f"https://www.reddit.com/r/{self.subreddit}/{endpoint}",
            headers={"User-Agent": self.user_agent},
            params=params,
        )
        response.raise_for_status()
        return parse_feed(response.text)

    def _item_to_listing(self, item: dict[str, Any], *, query: str) -> NormalizedListing:
        title = (item.get("title") or "").strip()
        selftext = (item.get("selftext") or "").strip()
        author = item.get("author") or None
        permalink = (item.get("permalink") or "").strip()
        url = f"https://www.reddit.com{permalink}" if permalink else item.get("url") or ""
        created_utc = item.get("created_utc")
        timestamp_seen = (
            datetime.fromtimestamp(float(created_utc), tz=timezone.utc)
            if created_utc is not None
            else datetime.now(timezone.utc)
        )

        if self.subreddit.lower() == "hardwareswapuk":
            parsed = parse_hardwareswapuk_post(title, selftext, author, url)
            source_listing_id = str(item.get("id") or item.get("name") or parsed["source_listing_id"])
            return NormalizedListing(
                schema_version="1.0",
                source=self.CONNECTOR_ID,
                source_type=self.source_role,
                source_listing_id=source_listing_id,
                title_raw=parsed["title_raw"],
                price=parsed["price"],
                currency="GBP",
                url=parsed["url"],
                timestamp_seen=timestamp_seen,
                product_normalized=None,
                variant_normalized=parsed.get("variant_normalized"),
                condition=None,
                condition_raw=parsed.get("condition_raw"),
                shipping_cost=None,
                total_landed_cost=None,
                seller_or_store=parsed.get("seller_or_store"),
                seller_feedback_score=None,
                seller_feedback_pct=None,
                location=parsed.get("location"),
                in_stock=True,
                stock_state=None,
                image_url=None,
                exact_variant_confirmed=None,
                variant_match_confidence=None,
                mismatch_flags=None,
                risk_flags=None,
                category=None,
            )

        price_text = f"{title} {selftext}"
        price = _extract_price(price_text) or Decimal("0")
        source_listing_id = str(item.get("id") or item.get("name") or url or title)
        return NormalizedListing(
            schema_version="1.0",
            source=self.CONNECTOR_ID,
            source_type=self.source_role,
            source_listing_id=source_listing_id,
            title_raw=title,
            price=price,
            currency="GBP",
            url=url,
            timestamp_seen=timestamp_seen,
            product_normalized=None,
            variant_normalized={"query": query} if self.source_role == SourceType.SIGNAL else None,
            condition=None,
            condition_raw=None,
            shipping_cost=None,
            total_landed_cost=None,
            seller_or_store=author,
            seller_feedback_score=None,
            seller_feedback_pct=None,
            location=None,
            in_stock=None if self.source_role == SourceType.SIGNAL else True,
            stock_state=None,
            image_url=None,
            exact_variant_confirmed=None,
            variant_match_confidence=None,
            mismatch_flags=None,
            risk_flags=None,
            category=None,
        )

    def _entry_to_listing(self, entry: Any, *, query: str) -> NormalizedListing:
        if self.subreddit.lower() == "hardwareswapuk":
            parsed = parse_hardwareswapuk_post(entry.title, entry.content, entry.author, entry.link)
            return NormalizedListing(
                schema_version="1.0",
                source=self.CONNECTOR_ID,
                source_type=self.source_role,
                source_listing_id=parsed["source_listing_id"],
                title_raw=parsed["title_raw"],
                price=parsed["price"],
                currency="GBP",
                url=parsed["url"],
                timestamp_seen=entry.published_at or datetime.now(timezone.utc),
                product_normalized=None,
                variant_normalized=parsed.get("variant_normalized"),
                condition=None,
                condition_raw=parsed.get("condition_raw"),
                shipping_cost=None,
                total_landed_cost=None,
                seller_or_store=parsed.get("seller_or_store"),
                seller_feedback_score=None,
                seller_feedback_pct=None,
                location=parsed.get("location"),
                in_stock=True,
                stock_state=None,
                image_url=None,
                exact_variant_confirmed=None,
                variant_match_confidence=None,
                mismatch_flags=None,
                risk_flags=None,
                category=None,
            )

        price = _extract_price(f"{entry.title} {entry.content}") or Decimal("0")
        return NormalizedListing(
            schema_version="1.0",
            source=self.CONNECTOR_ID,
            source_type=self.source_role,
            source_listing_id=entry.id or entry.link or entry.title,
            title_raw=entry.title,
            price=price,
            currency="GBP",
            url=entry.link,
            timestamp_seen=entry.published_at or datetime.now(timezone.utc),
            product_normalized=None,
            variant_normalized={"query": query} if self.source_role == SourceType.SIGNAL else None,
            condition=None,
            condition_raw=None,
            shipping_cost=None,
            total_landed_cost=None,
            seller_or_store=entry.author,
            seller_feedback_score=None,
            seller_feedback_pct=None,
            location=None,
            in_stock=None if self.source_role == SourceType.SIGNAL else True,
            stock_state=None,
            image_url=None,
            exact_variant_confirmed=None,
            variant_match_confidence=None,
            mismatch_flags=None,
            risk_flags=None,
            category=None,
        )


class RedditHardwareSwapUKConnector(RedditConnector):
    CONNECTOR_ID = "reddit_hardwareswapuk"

    def __init__(self, access_token: str | None = None, **kwargs: Any) -> None:
        super().__init__(
            subreddit="hardwareswapuk",
            source_role=SourceType.MARKETPLACE,
            access_token=access_token,
            **kwargs,
        )


class RedditBapcSalesUKConnector(RedditConnector):
    CONNECTOR_ID = "reddit_bapcsalesuk"

    def __init__(self, access_token: str | None = None, **kwargs: Any) -> None:
        super().__init__(
            subreddit="bapcsalesuk",
            source_role=SourceType.SIGNAL,
            access_token=access_token,
            **kwargs,
        )

    async def search(self, query: str, filters: Optional[dict[str, Any]] = None) -> list[NormalizedListing]:
        listings = await super().search(query, filters)
        for listing in listings:
            listing.in_stock = None
        return listings


class HotUKDealsConnector(RedditConnector):
    CONNECTOR_ID = "hotukdeals"

    def __init__(self, access_token: str | None = None, **kwargs: Any) -> None:
        super().__init__(
            subreddit="hotukdeals",
            source_role=SourceType.SIGNAL,
            access_token=access_token,
            **kwargs,
        )

    async def search(self, query: str, filters: Optional[dict[str, Any]] = None) -> list[NormalizedListing]:
        listings = await super().search(query, filters)
        keyword = query.lower().strip()
        if keyword:
            listings = [
                listing
                for listing in listings
                if keyword in listing.title_raw.lower()
                or keyword in (listing.variant_normalized or {}).get("query", "").lower()
            ]
        for listing in listings:
            listing.in_stock = None
        return listings


def _extract_price(text: str) -> Optional[Decimal]:
    match = re.search(r"£\s*(\d+(?:\.\d{1,2})?)", text, flags=re.IGNORECASE)
    if match:
        return Decimal(match.group(1))
    match = re.search(r"(?:gbp\s*)?(\d+(?:\.\d{1,2})?)", text, flags=re.IGNORECASE)
    if not match:
        return None
    return Decimal(match.group(1))
