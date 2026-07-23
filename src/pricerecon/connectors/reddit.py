"""Reddit connector with RSS, approved API, and browser fallbacks.

RSS is intentionally attempted first because it is cheap and does not require
credentials.  A blocked or rate-limited RSS request is never represented as an
empty result: the connector either obtains data through an enabled fallback or
raises the original structured degraded error.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
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


logger = logging.getLogger(__name__)


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
        self._last_rate_limit_info: dict[str, Any] | None = None

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
        if enabled not in {"1", "true", "yes"}:
            return False
        # Check either env vars or credential file
        if os.getenv("REDDIT_CLIENT_ID") and os.getenv("REDDIT_CLIENT_SECRET") and os.getenv("REDDIT_USER_AGENT"):
            return True
        cred_file = os.getenv("REDDIT_CREDENTIAL_FILE")
        if cred_file and os.path.exists(cred_file):
            return self._validate_credential_file(cred_file)
        return False

    def _validate_credential_file(self, cred_file: str) -> bool:
        """Validate that a credential file has the required fields."""
        try:
            with open(cred_file, "r") as f:
                creds = json.load(f)
            if not isinstance(creds, dict):
                return False
            return bool(creds.get("client_id") and creds.get("client_secret"))
        except (json.JSONDecodeError, OSError, ValueError):
            logger.warning(f"Reddit credential file is malformed: {cred_file}")
            return False

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
        stage_events: list[dict[str, Any]] = []

        def record_stage(stage: str, outcome: str, **details: Any) -> None:
            event = {
                "connector": self.connector_id,
                "stage": stage,
                "outcome": outcome,
                **details,
            }
            stage_events.append({key: value for key, value in event.items() if key != "connector"})
            logger.info("reddit_fallback_stage", extra=event)

        record_stage("rss", "attempted", query=query)
        try:
            listings = await super().search(query, filters)
            finalized = self._finalize(listings, query)
            record_stage("rss", "succeeded", listing_count=len(finalized))
            return finalized
        except ConnectorDegradedError as exc:
            rss_error = exc
            record_stage("rss", "failed", status=exc.status.value, error=exc.message)
        except Exception as exc:
            # Transport and parser errors are also eligible for fallback.  Letting
            # these escape here was the reason browser fallback was never reached.
            rss_error = ConnectorDegradedError(
                ConnectorStatus.unknown_error,
                "Reddit RSS acquisition failed",
                self.connector_id,
                {"error": str(exc), "error_type": type(exc).__name__},
            )
            record_stage("rss", "failed", status=rss_error.status.value, error=str(exc))

        fallback_errors: list[str] = []
        api_enabled = os.getenv(self.API_ENABLED_ENV, "").strip().lower() in {"1", "true", "yes"}
        api_approved = self._api_is_approved()
        if api_enabled and api_approved:
            record_stage("api", "attempted")
            try:
                finalized = self._finalize(await self._search_api(query, filters), query)
                record_stage("api", "succeeded", listing_count=len(finalized))
                return finalized
            except ConnectorDegradedError as exc:
                fallback_errors.append(f"api:{exc.status.value}")
                record_stage("api", "failed", status=exc.status.value, error=exc.message)
            except Exception as exc:
                # A malformed upstream response or transport-library error must
                # abort the chain before the browser fallback gets a chance.
                fallback_errors.append(f"api:{type(exc).__name__}")
                record_stage("api", "failed", status="unknown_error", error=str(exc))
        else:
            reason = "disabled" if not api_enabled else "not_approved"
            record_stage("api", "skipped", reason=reason)

        browser_configured = self._browser_is_configured()
        if browser_configured:
            record_stage("browser", "attempted")
            try:
                finalized = self._finalize(await self._search_browser(query, filters), query)
                record_stage("browser", "succeeded", listing_count=len(finalized))
                return finalized
            except ConnectorDegradedError as exc:
                fallback_errors.append(f"browser:{exc.status.value}")
                record_stage("browser", "failed", status=exc.status.value, error=exc.message)
            except Exception as exc:
                fallback_errors.append(f"browser:{type(exc).__name__}")
                record_stage("browser", "failed", status="unknown_error", error=str(exc))
        else:
            record_stage("browser", "skipped", reason="not_configured")

        # Do not turn an upstream 403/429 (or a failed configured fallback)
        # into a misleading successful empty search.
        assert rss_error is not None
        detail = dict(rss_error.detail or {})
        if fallback_errors:
            detail["fallback_errors"] = fallback_errors
        detail["fallbacks_attempted"] = bool((api_enabled and api_approved) or browser_configured)
        detail["fallback_stages"] = stage_events
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

        # Load credentials from environment or credential file
        client_id, client_secret, user_agent = self._load_api_credentials()

        try:
            token_response = await self._api_client.post(
                "https://www.reddit.com/api/v1/access_token",
                data={"grant_type": "client_credentials"},
                auth=(client_id, client_secret),
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

        # Extract and store rate limit information
        rate_limit_info = self._extract_rate_limit_info(dict(response.headers))
        if rate_limit_info:
            self._last_rate_limit_info = rate_limit_info

        children = response.json().get("data", {}).get("children", [])
        return [self._api_post_to_listing(child.get("data", {})) for child in children if child.get("data")]

    def _load_api_credentials(self) -> tuple[str, str, str]:
        """Load API credentials from environment or credential file.

        Returns:
            Tuple of (client_id, client_secret, user_agent)
        """
        cred_file = os.getenv("REDDIT_CREDENTIAL_FILE")
        if cred_file and os.path.exists(cred_file):
            import json
            with open(cred_file, "r") as f:
                creds = json.load(f)
            return (
                creds.get("client_id", ""),
                creds.get("client_secret", ""),
                creds.get("user_agent", "PriceRecon/1.0"),
            )

        return (
            os.getenv("REDDIT_CLIENT_ID", ""),
            os.getenv("REDDIT_CLIENT_SECRET", ""),
            os.getenv("REDDIT_USER_AGENT", "PriceRecon/1.0"),
        )

    def _extract_rate_limit_info(self, headers: dict[str, str]) -> dict[str, Any] | None:
        """Extract rate limit information from Reddit API response headers.

        Args:
            headers: HTTP response headers

        Returns:
            Dict with rate limit info or None if not available
        """
        info = {}
        if "x-ratelimit-remaining" in headers:
            info["remaining"] = headers["x-ratelimit-remaining"]
        if "x-ratelimit-used" in headers:
            info["used"] = headers["x-ratelimit-used"]
        if "x-ratelimit-reset" in headers:
            info["reset"] = headers["x-ratelimit-reset"]
        return info if info else None

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
        url = f"https://old.reddit.com/r/{self.SUBREDDIT}/new.json?raw_json=1&q={quote_plus(query)}&restrict_sr=1"
        context: Any = None
        content = ""
        try:
            context = await self._browser_client.new_context()
            page = await context.new_page()
            response = await page.goto(url, wait_until="domcontentloaded", timeout=config.navigation_timeout_ms)
            await page.wait_for_timeout(config.wait_after_navigation_ms)
            content = await page.content()
            status_code = getattr(response, "status", None) if response is not None else None
            if callable(status_code):
                status_code = status_code()
            if status_code in {403, 429}:
                status = ConnectorStatus.bot_blocked if status_code == 403 else ConnectorStatus.rate_limited
                raise ConnectorDegradedError(
                    status, f"Reddit browser returned HTTP {status_code}", self.connector_id,
                    {"requested_url": url, "status_code": status_code},
                )
        except ConnectorDegradedError:
            raise
        except (TimeoutError, asyncio.TimeoutError) as exc:
            raise ConnectorDegradedError(
                ConnectorStatus.timeout, "Reddit browser navigation timed out", self.connector_id,
                {"requested_url": url, "timeout_ms": config.navigation_timeout_ms},
            ) from exc
        except Exception as exc:
            if "timeout" in str(exc).lower():
                raise ConnectorDegradedError(
                    ConnectorStatus.timeout, "Reddit browser navigation timed out", self.connector_id,
                    {"requested_url": url, "timeout_ms": config.navigation_timeout_ms, "error": str(exc)},
                ) from exc
            raise ConnectorDegradedError(ConnectorStatus.unknown_error, "Reddit browser acquisition failed", self.connector_id, {"error": str(exc)}) from exc
        finally:
            if context is not None:
                await context.close()
        if _looks_blocked(content):
            raise ConnectorDegradedError(
                ConnectorStatus.bot_blocked,
                "Reddit browser page is blocked or human-gated",
                self.connector_id,
            )
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
    """Parse Reddit JSON listings, HTML, and Camofox text snapshots."""
    try:
        payload = json.loads(content)
    except (TypeError, ValueError):
        payload = None
    children = payload.get("data", {}).get("children", []) if isinstance(payload, dict) else []
    if isinstance(children, list):
        entries: list[FeedEntry] = []
        for child in children[:limit]:
            data = child.get("data", {}) if isinstance(child, dict) else {}
            if not isinstance(data, dict):
                continue
            permalink = str(data.get("permalink") or "")
            link = str(data.get("url") or (f"https://www.reddit.com{permalink}" if permalink else ""))
            if not link or not data.get("title"):
                continue
            created = data.get("created_utc")
            try:
                published = datetime.fromtimestamp(float(created), tz=timezone.utc) if created else None
            except (TypeError, ValueError, OverflowError):
                published = None
            entries.append(FeedEntry(
                id=str(data.get("id") or hashlib.sha1(link.encode()).hexdigest()),
                title=str(data.get("title") or ""), link=link,
                content=str(data.get("selftext") or ""), author=str(data.get("author") or "") or None,
                published_at=published,
            ))
        if entries:
            return entries

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
        body = anchor.parent.text(strip=True) if anchor.parent is not None else ""
        entries.append(FeedEntry(id=hashlib.sha1(link.encode()).hexdigest(), title=title, link=link, content=body))
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
