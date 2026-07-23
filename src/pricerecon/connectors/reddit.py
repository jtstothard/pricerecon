"""Reddit connector with RSS, approved API, and browser fallbacks.

RSS is intentionally attempted first because it is cheap and does not require
credentials.  A blocked or rate-limited RSS request is never represented as an
empty result: the connector either obtains data through an enabled fallback or
raises the original structured degraded error.
"""

from __future__ import annotations

import hashlib
import os
import re
from datetime import datetime, timezone
from typing import Any, Optional
from urllib.parse import quote_plus

import httpx
from returns.result import Success
from selectolax.parser import HTMLParser

from pricerecon.connectors.browser_client import BrowserClient
from pricerecon.connectors.rss import (
    ConnectorTemplateConfig,
    FeedEntry,
    TemplateConnector,
    load_template_configs_result,
)
from pricerecon.connectors.status import ConnectorDegradedError, ConnectorStatus
from pricerecon.models import NormalizedListing, SourceType


def _load_template_or_default(
    connector_id: str,
    *,
    display_name: str,
    source_role: SourceType,
    endpoint_url: str,
) -> ConnectorTemplateConfig:
    loaded = load_template_configs_result()
    if isinstance(loaded, Success):
        template = loaded.unwrap().get(connector_id)
        if template is not None:
            return template  # type: ignore[no-any-return]
    return ConnectorTemplateConfig(
        source=connector_id,
        display_name=display_name,
        source_role=source_role,
        endpoint_url=endpoint_url,
        request_method="GET",
        request_headers={"User-Agent": "PriceRecon/0.1"},
    )


def _query_terms(query: str) -> list[str]:
    return [term for term in re.split(r"[^a-z0-9]+", query.lower()) if term]


def _filter_listings_by_query(
    listings: list[NormalizedListing], query: str
) -> list[NormalizedListing]:
    terms = _query_terms(query)
    if not terms:
        return listings
    filtered: list[NormalizedListing] = []
    for listing in listings:
        variant = listing.variant_normalized or {}
        haystack = " ".join(
            str(part).lower()
            for part in (
                listing.title_raw,
                listing.url,
                variant.get("item_description"),
                variant.get("query"),
            )
            if part
        )
        if all(term in haystack for term in terms):
            filtered.append(listing)
    return filtered


class _RedditConnector(TemplateConnector):
    """Shared acquisition and normalization for Reddit subreddits."""

    SUBREDDIT: str = ""
    API_ENABLED_ENV = "PRICERECON_REDDIT_API_ENABLED"

    def __init__(self, template: ConnectorTemplateConfig) -> None:
        super().__init__(template)
        self._api_client: httpx.AsyncClient | None = None
        self._browser_client: BrowserClient | None = None

    async def cleanup(self) -> None:
        await super().cleanup()
        if self._api_client is not None:
            await self._api_client.aclose()
            self._api_client = None
        if self._browser_client is not None:
            await self._browser_client.close()
            self._browser_client = None

    def _api_is_approved(self) -> bool:
        enabled = os.getenv(self.API_ENABLED_ENV, "").strip().lower()
        return enabled in {"1", "true", "yes"} and bool(
            os.getenv("REDDIT_CLIENT_ID")
            and os.getenv("REDDIT_CLIENT_SECRET")
            and os.getenv("REDDIT_USER_AGENT")
        )

    def _browser_is_configured(self) -> bool:
        # Camofox is explicit; local Playwright can be opted into separately so
        # a production worker does not unexpectedly launch a browser.
        enabled = os.getenv("PRICERECON_REDDIT_BROWSER_ENABLED", "").strip().lower()
        return bool(
            os.getenv("CAMOFOX_URL")
            or os.getenv("PRICERECON_CAMOFOX_URL")
            or enabled in {"1", "true", "yes"}
        )

    async def search(
        self, query: str, filters: Optional[dict[str, Any]] = None
    ) -> list[NormalizedListing]:
        filters = filters or {}
        rss_error: ConnectorDegradedError | None = None
        try:
            listings = await super().search(query, filters)
            return self._finalize(listings, query)
        except ConnectorDegradedError as exc:
            if exc.status not in {ConnectorStatus.bot_blocked, ConnectorStatus.rate_limited}:
                raise
            rss_error = exc

        fallback_errors: list[str] = []
        if self._api_is_approved():
            try:
                return self._finalize(await self._search_api(query, filters), query)
            except ConnectorDegradedError as exc:
                fallback_errors.append(f"api:{exc.status.value}")

        if self._browser_is_configured():
            try:
                return self._finalize(await self._search_browser(query, filters), query)
            except ConnectorDegradedError as exc:
                fallback_errors.append(f"browser:{exc.status.value}")

        # Do not turn an upstream 403/429 (or a failed configured fallback)
        # into a misleading successful empty search.
        assert rss_error is not None
        detail = dict(rss_error.detail or {})
        if fallback_errors:
            detail["fallback_errors"] = fallback_errors
        detail["fallbacks_attempted"] = bool(self._api_is_approved() or self._browser_is_configured())
        raise ConnectorDegradedError(
            status=rss_error.status,
            message=f"{self.connector_id} unavailable after RSS fallback chain",
            connector_id=self.connector_id,
            detail=detail,
        ) from rss_error

    def _finalize(self, listings: list[NormalizedListing], query: str) -> list[NormalizedListing]:
        listings = _filter_listings_by_query(listings, query)
        for listing in listings:
            listing.in_stock = None
        return listings

    async def _search_api(self, query: str, filters: dict[str, Any]) -> list[NormalizedListing]:
        if self._api_client is None:
            self._api_client = httpx.AsyncClient(timeout=30.0)
        user_agent = os.environ["REDDIT_USER_AGENT"]
        try:
            token_response = await self._api_client.post(
                "https://www.reddit.com/api/v1/access_token",
                data={"grant_type": "client_credentials"},
                auth=(os.environ["REDDIT_CLIENT_ID"], os.environ["REDDIT_CLIENT_SECRET"]),
                headers={"User-Agent": user_agent},
            )
        except httpx.HTTPError as exc:
            raise ConnectorDegradedError(
                ConnectorStatus.unknown_error, "Reddit API token request failed", self.connector_id, {"error": str(exc)}
            ) from exc
        if token_response.status_code in {401, 403}:
            raise ConnectorDegradedError(
                ConnectorStatus.auth_failed, "Reddit API authentication failed", self.connector_id,
                {"status_code": token_response.status_code},
            )
        if token_response.status_code == 429:
            raise ConnectorDegradedError(ConnectorStatus.rate_limited, "Reddit API rate limited", self.connector_id)
        token_response.raise_for_status()
        token = token_response.json().get("access_token")
        if not token:
            raise ConnectorDegradedError(ConnectorStatus.auth_failed, "Reddit API returned no access token", self.connector_id)
        url = f"https://oauth.reddit.com/r/{self.SUBREDDIT}/new.json"
        response = await self._api_client.get(
            url,
            params={"q": query, "restrict_sr": 1, "limit": int(filters.get("limit") or 25)},
            headers={"Authorization": f"bearer {token}", "User-Agent": user_agent},
        )
        if response.status_code in {401, 403}:
            raise ConnectorDegradedError(ConnectorStatus.auth_failed, "Reddit API rejected the request", self.connector_id, {"status_code": response.status_code})
        if response.status_code == 429:
            raise ConnectorDegradedError(ConnectorStatus.rate_limited, "Reddit API rate limited", self.connector_id)
        response.raise_for_status()
        children = response.json().get("data", {}).get("children", [])
        return [self._api_post_to_listing(child.get("data", {})) for child in children if child.get("data")]

    def _api_post_to_listing(self, data: dict[str, Any]) -> NormalizedListing:
        permalink = str(data.get("permalink") or "")
        url = str(data.get("url") or (f"https://www.reddit.com{permalink}" if permalink else ""))
        entry = FeedEntry(
            id=str(data.get("id") or url),
            title=str(data.get("title") or ""),
            link=url,
            content=str(data.get("selftext") or ""),
            author=str(data.get("author") or "") or None,
            published_at=datetime.fromtimestamp(float(data["created_utc"]), tz=timezone.utc) if data.get("created_utc") else None,
        )
        return self._entry_to_listing(entry)

    async def _search_browser(self, query: str, filters: dict[str, Any]) -> list[NormalizedListing]:
        from pricerecon.connectors.browser_client import BrowserSessionConfig

        camofox_url = os.getenv("CAMOFOX_URL") or os.getenv("PRICERECON_CAMOFOX_URL")
        config = BrowserSessionConfig(
            camofox_url=camofox_url,
            camofox_api_key=os.getenv("CAMOFOX_API_KEY"),
            camofox_access_key=os.getenv("CAMOFOX_ACCESS_KEY"),
            camofox_user_id=os.getenv("CAMOFOX_USER_ID"),
            camofox_session_key=os.getenv("CAMOFOX_SESSION_KEY"),
        )
        self._browser_client = self._browser_client or BrowserClient(config=config)
        context = await self._browser_client.new_context()
        page = await context.new_page()
        url = f"https://www.reddit.com/r/{self.SUBREDDIT}/new/?q={quote_plus(query)}&restrict_sr=1"
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=45000)
            await page.wait_for_timeout(2500)
            content = await page.content()
        except Exception as exc:
            raise ConnectorDegradedError(ConnectorStatus.bot_blocked, "Reddit browser acquisition failed", self.connector_id, {"error": str(exc)}) from exc
        finally:
            await context.close()
        entries = _parse_browser_posts(content, self.SUBREDDIT, int(filters.get("limit") or 25))
        if not entries:
            # A blocked RSS request followed by an unparseable browser page is
            # not evidence of zero matches; surface it as degraded instead.
            raise ConnectorDegradedError(
                ConnectorStatus.parse_error,
                "Reddit browser page contained no parseable posts",
                self.connector_id,
            )
        return [self._entry_to_listing(entry) for entry in entries]


class RedditHardwareSwapUKConnector(_RedditConnector):
    CONNECTOR_ID = "reddit_hardwareswapuk"
    SUBREDDIT = "hardwareswapuk"

    def __init__(self) -> None:
        super().__init__(_load_template_or_default(self.CONNECTOR_ID, display_name="Reddit hardwareswapuk", source_role=SourceType.MARKETPLACE, endpoint_url="https://www.reddit.com/r/hardwareswapuk/new/.rss?limit={limit}&restrict_sr=1"))


class RedditBapcSalesUKConnector(_RedditConnector):
    CONNECTOR_ID = "reddit_bapcsalesuk"
    SUBREDDIT = "bapcsalesuk"

    def __init__(self) -> None:
        super().__init__(_load_template_or_default(self.CONNECTOR_ID, display_name="Reddit bapcsalesuk", source_role=SourceType.MARKETPLACE, endpoint_url="https://www.reddit.com/r/bapcsalesuk/new/.rss?limit={limit}&restrict_sr=1"))


class HotUKDealsConnector(TemplateConnector):
    CONNECTOR_ID = "hotukdeals"

    def __init__(self) -> None:
        super().__init__(_load_template_or_default(self.CONNECTOR_ID, display_name="HotUKDeals", source_role=SourceType.SIGNAL, endpoint_url="https://www.hotukdeals.com/rss/new"))

    async def search(self, query: str, filters: Optional[dict[str, Any]] = None) -> list[NormalizedListing]:
        listings = _filter_listings_by_query(await super().search(query, filters), query)
        for listing in listings:
            listing.in_stock = None
        return listings


def _looks_blocked(content: str) -> bool:
    lowered = content.lower()
    return any(marker in lowered for marker in ("robot check", "verify you are human", "access denied", "temporarily blocked"))


def _parse_browser_posts(content: str, subreddit: str, limit: int) -> list[FeedEntry]:
    """Parse both Reddit HTML and Camofox text snapshots conservatively."""
    parser = HTMLParser(content)
    entries: list[FeedEntry] = []
    seen: set[str] = set()
    for anchor in parser.css("a[href*='/comments/']"):
        href = anchor.attributes.get("href", "")
        title = anchor.text(strip=True)
        if not title or not href:
            continue
        link = href if href.startswith("http") else f"https://www.reddit.com{href}"
        if link in seen:
            continue
        seen.add(link)
        entries.append(FeedEntry(id=hashlib.sha1(link.encode()).hexdigest(), title=title, link=link))
        if len(entries) >= limit:
            break
    # Camofox's text snapshot can omit anchor markup; retain only recognizable
    # Reddit post URLs and use the surrounding line as a title.
    if not entries:
        for match in re.finditer(r"(?P<title>.{5,200}?)\s+(?P<link>https?://(?:www\.)?reddit\.com/r/[^\s]+/comments/[^\s]+)", content):
            link = match.group("link").rstrip(".,)")
            if link in seen:
                continue
            seen.add(link)
            entries.append(FeedEntry(id=hashlib.sha1(link.encode()).hexdigest(), title=re.sub(r"\s+", " ", match.group("title")).strip(), link=link))
            if len(entries) >= limit:
                break
    return entries
