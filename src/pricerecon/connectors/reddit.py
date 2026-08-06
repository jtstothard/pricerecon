"""Reddit connector with RSS, approved API, and browser fallbacks.

RSS is intentionally attempted first because it is cheap and does not require
credentials.  A blocked or rate-limited RSS request is never represented as an
empty result: the connector either obtains data through an enabled fallback or
raises the original structured degraded error.
"""

from __future__ import annotations

import asyncio
import hashlib
import inspect
import json
import logging
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Optional, cast
from urllib.parse import quote_plus

import httpx
from returns.result import Success
from selectolax.parser import HTMLParser

from pricerecon.connectors.external_browser import BrowserDegradation, ExternalBrowserAdapter
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
        self._last_rate_limit_info: dict[str, Any] | None = None
        # Load retry configuration from environment or use defaults
        self._rss_max_retries = int(os.getenv("PRICERECON_REDDIT_RSS_MAX_RETRIES", "2"))
        self._api_max_retries = int(os.getenv("PRICERECON_REDDIT_API_MAX_RETRIES", "2"))
        self._browser_max_retries = int(os.getenv("PRICERECON_REDDIT_BROWSER_MAX_RETRIES", "1"))

    async def _retry_with_backoff(
        self,
        func: Callable[..., Any],
        max_retries: int,
        stage_name: str,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Execute a function with exponential backoff retries.

        Args:
            func: Async function to execute
            max_retries: Maximum number of retry attempts (excluding initial attempt)
            stage_name: Name of the stage (for logging)
            *args: Positional arguments to pass to func
            **kwargs: Keyword arguments to pass to func

        Returns:
            Result of func call

        Raises:
            Exception: The last exception encountered if all retries fail
        """
        last_exception: Exception | None = None
        for attempt in range(max_retries + 1):
            try:
                return await func(*args, **kwargs)
            except Exception as exc:
                last_exception = exc
                if attempt < max_retries:
                    # Exponential backoff: 1s, 2s, 4s, ...
                    backoff_seconds = 2**attempt
                    logger.warning(
                        f"{stage_name} attempt {attempt + 1}/{max_retries + 1} failed: {exc}. "
                        f"Retrying in {backoff_seconds}s..."
                    )
                    await asyncio.sleep(backoff_seconds)
                else:
                    logger.error(f"{stage_name} failed after {max_retries + 1} attempts: {exc}")
        # All retries exhausted
        assert last_exception is not None
        raise last_exception

    async def cleanup(self) -> None:
        await super().cleanup()
        if self._api_client is not None:
            await self._api_client.aclose()
            self._api_client = None

    def _api_is_approved(self) -> bool:
        enabled = os.getenv(self.API_ENABLED_ENV, "").strip().lower()
        if enabled not in {"1", "true", "yes"}:
            return False
        # Check either env vars or credential file
        if (
            os.getenv("REDDIT_CLIENT_ID")
            and os.getenv("REDDIT_CLIENT_SECRET")
            and os.getenv("REDDIT_USER_AGENT")
        ):
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

    def _camofox_is_configured(self) -> bool:
        """Return whether Reddit has an explicit persistent Camofox profile.

        Reddit browser retrieval is deliberately unavailable through local
        Playwright or an anonymous Camofox session.  A selected named Camofox
        backend is preferred; the legacy environment form remains supported
        when it names the same persistent user-scoped profile.
        """
        adapter = cast("ExternalBrowserAdapter | None", getattr(self, "_external_browser", None))
        if adapter is not None:
            return (
                adapter.has_authenticated_camofox_profile()
                or adapter.has_authenticated_cloakbrowser_reddit()
            )
        return bool(
            (os.getenv("CAMOFOX_URL") or os.getenv("PRICERECON_CAMOFOX_URL"))
            and os.getenv("PRICERECON_REDDIT_CAMOFOX_USER_ID", "").strip()
            and os.getenv("PRICERECON_REDDIT_CAMOFOX_SESSION_KEY", "").strip()
        )

    def _camofox_adapter(self) -> Any:
        """Return the configured Camofox adapter, never an anonymous browser."""
        adapter = getattr(self, "_external_browser", None)
        if adapter is not None:
            return adapter

        endpoint = os.getenv("CAMOFOX_URL") or os.getenv("PRICERECON_CAMOFOX_URL")
        backends: dict[str, dict[str, Any]] = {
            "reddit_camofox": {
                "type": "camofox",
                "endpoint": endpoint,
                "options": {
                    "user_id": os.getenv("PRICERECON_REDDIT_CAMOFOX_USER_ID", ""),
                    "session_key": os.getenv("PRICERECON_REDDIT_CAMOFOX_SESSION_KEY", ""),
                    "api_key": os.getenv("CAMOFOX_API_KEY", ""),
                },
            }
        }
        # When the CloakBrowser sidecar is configured, register it alongside the
        # persistent Camofox profile. This enables the authenticated-state bridge:
        # Camofox's storageState is fetched in memory and POSTed to the CloakBrowser
        # HTTP wrapper, which injects it into browser.newContext({storageState}).
        # The cloakbrowser endpoint is the sidecar wrapper, NOT the upstream SDK.
        cloak_endpoint = os.getenv("PRICERECON_CLOAKBROWSER_URL") or os.getenv("CLOAKBROWSER_URL")
        if cloak_endpoint:
            backends["reddit_cloakbrowser"] = {
                "type": "cloakbrowser",
                "endpoint": cloak_endpoint,
                "options": {},
            }
        return ExternalBrowserAdapter.from_config(
            {
                "browser_backends": backends,
                "browser_default": (
                    ["reddit_camofox", "reddit_cloakbrowser"]
                    if cloak_endpoint
                    else "reddit_camofox"
                ),
            }
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
            listings = await self._retry_with_backoff(
                super().search,
                self._rss_max_retries,
                f"{self.connector_id}_rss",
                query,
                filters,
            )
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
                finalized = self._finalize(
                    await self._retry_with_backoff(
                        lambda: self._search_api(query, filters),
                        self._api_max_retries,
                        f"{self.connector_id}_api",
                    ),
                    query,
                )
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

        camofox_configured = self._camofox_is_configured()
        if camofox_configured:
            record_stage("camofox", "attempted")
            try:
                finalized = self._finalize(
                    await self._retry_with_backoff(
                        lambda: self._search_camofox(query, filters),
                        self._browser_max_retries,
                        f"{self.connector_id}_camofox",
                    ),
                    query,
                )
                record_stage("camofox", "succeeded", listing_count=len(finalized))
                return finalized
            except ConnectorDegradedError as exc:
                fallback_errors.append(f"camofox:{exc.status.value}")
                record_stage("camofox", "failed", status=exc.status.value, error=exc.message)
            except Exception as exc:
                fallback_errors.append(f"camofox:{type(exc).__name__}")
                record_stage("camofox", "failed", status="unknown_error", error=str(exc))
        else:
            record_stage("camofox", "skipped", reason="authenticated_profile_not_configured")

        # Do not turn an upstream 403/429 (or a failed configured fallback)
        # into a misleading successful empty search.
        assert rss_error is not None
        detail = dict(rss_error.detail or {})
        if fallback_errors:
            detail["fallback_errors"] = fallback_errors
        detail["fallbacks_attempted"] = bool((api_enabled and api_approved) or camofox_configured)
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
                ConnectorStatus.unknown_error,
                "Reddit API token request failed",
                self.connector_id,
                {"error": str(exc)},
            ) from exc
        if token_response.status_code in {401, 403}:
            raise ConnectorDegradedError(
                ConnectorStatus.auth_failed,
                "Reddit API authentication failed",
                self.connector_id,
                {"status_code": token_response.status_code},
            )
        if token_response.status_code == 429:
            raise ConnectorDegradedError(
                ConnectorStatus.rate_limited, "Reddit API rate limited", self.connector_id
            )
        token_response.raise_for_status()
        token = token_response.json().get("access_token")
        if not token:
            raise ConnectorDegradedError(
                ConnectorStatus.auth_failed,
                "Reddit API returned no access token",
                self.connector_id,
            )
        url = f"https://oauth.reddit.com/r/{self.SUBREDDIT}/new.json"
        response = await self._api_client.get(
            url,
            params={"q": query, "restrict_sr": 1, "limit": int(filters.get("limit") or 25)},
            headers={"Authorization": f"bearer {token}", "User-Agent": user_agent},
        )
        if response.status_code in {401, 403}:
            raise ConnectorDegradedError(
                ConnectorStatus.auth_failed,
                "Reddit API rejected the request",
                self.connector_id,
                {"status_code": response.status_code},
            )
        if response.status_code == 429:
            raise ConnectorDegradedError(
                ConnectorStatus.rate_limited, "Reddit API rate limited", self.connector_id
            )
        response.raise_for_status()

        # Extract and store rate limit information
        rate_limit_info = self._extract_rate_limit_info(dict(response.headers))
        if rate_limit_info:
            self._last_rate_limit_info = rate_limit_info

        children = response.json().get("data", {}).get("children", [])
        return [
            self._api_post_to_listing(child.get("data", {}))
            for child in children
            if child.get("data")
        ]

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
            published_at=(
                datetime.fromtimestamp(float(data["created_utc"]), tz=timezone.utc)
                if data.get("created_utc")
                else None
            ),
        )
        return self._entry_to_listing(entry)

    async def _search_camofox(self, query: str, filters: dict[str, Any]) -> list[NormalizedListing]:
        """Retrieve through the configured authenticated Camofox profile only."""
        if not self._camofox_is_configured():
            raise ConnectorDegradedError(
                ConnectorStatus.auth_failed,
                "Reddit Camofox authenticated profile is not configured",
                self.connector_id,
            )

        from pricerecon.connectors.external_browser import as_connector_degraded_error

        url = f"https://www.reddit.com/r/{self.SUBREDDIT}/new/?q={quote_plus(query)}&restrict_sr=1"
        adapter = self._camofox_adapter()
        authenticated_bridge = getattr(adapter, "has_authenticated_cloakbrowser_reddit", None)
        if callable(authenticated_bridge) and authenticated_bridge():
            result = await adapter.navigate_with_camofox_storage_state(url)
        else:
            result = await adapter.navigate(url)
        if result.degraded:
            error = as_connector_degraded_error(result, self.connector_id)
            if result.degradation is BrowserDegradation.BLOCKED:
                status_codes = {
                    attempt.status for attempt in result.attempts if attempt.status is not None
                }
                if status_codes & {401, 403}:
                    error = ConnectorDegradedError(
                        ConnectorStatus.auth_failed,
                        "Reddit Camofox profile is unauthenticated or expired",
                        self.connector_id,
                        error.detail,
                    )
            raise error
        content = result.rendered.snapshot or result.rendered.html
        if _looks_authenticated_out(content):
            raise ConnectorDegradedError(
                ConnectorStatus.auth_failed,
                "Reddit Camofox profile is unauthenticated or expired",
                self.connector_id,
                self.browser_result_detail(result),
            )
        if _looks_blocked(content):
            raise ConnectorDegradedError(
                ConnectorStatus.bot_blocked,
                "Reddit Camofox page is blocked or human-gated",
                self.connector_id,
                self.browser_result_detail(result),
            )
        structured_entries: list[FeedEntry] = []
        try:
            structured = json.loads(content)
        except (TypeError, ValueError):
            structured = None
        if isinstance(structured, dict) and isinstance(structured.get("items"), list):
            for item in structured["items"]:
                if not isinstance(item, dict) or not item.get("url") or not item.get("title"):
                    continue
                structured_entries.append(
                    FeedEntry(
                        id=hashlib.sha1(str(item["url"]).encode()).hexdigest(),
                        title=str(item["title"]),
                        link=str(item["url"]),
                    )
                )
        entries = structured_entries or _parse_browser_posts(
            content, self.SUBREDDIT, int(filters.get("limit") or 25), query=query
        )
        if not entries:
            # A valid Reddit listing page can contain posts that do not match the
            # requested query.  Treat that as a healthy empty result rather than
            # misclassifying it as a malformed browser response.  Keep the
            # parse-error path for snapshots with no recognizable subreddit posts.
            subreddit_marker = re.compile(
                rf"/r/{re.escape(self.SUBREDDIT)}/comments/",
                re.IGNORECASE,
            )
            if not subreddit_marker.search(content):
                raise ConnectorDegradedError(
                    ConnectorStatus.parse_error,
                    "Reddit Camofox page contained no parseable posts",
                    self.connector_id,
                    self.browser_result_detail(result),
                )
        return self.annotate_browser_result(
            [self._entry_to_listing(entry) for entry in entries], result
        )

    async def _search_browser(self, query: str, filters: dict[str, Any]) -> list[NormalizedListing]:
        """Compatibility alias for the Camofox-only Reddit browser path."""
        return await self._search_camofox(query, filters)


class RedditHardwareSwapUKConnector(_RedditConnector):
    CONNECTOR_ID = "reddit_hardwareswapuk"
    SUBREDDIT = "hardwareswapuk"

    def __init__(self) -> None:
        super().__init__(
            _load_template_or_default(
                self.CONNECTOR_ID,
                display_name="Reddit hardwareswapuk",
                source_role=SourceType.MARKETPLACE,
                endpoint_url="https://www.reddit.com/r/hardwareswapuk/new/.rss?limit={limit}&restrict_sr=1",
            )
        )


class RedditBuildAPCSalesUKConnector(_RedditConnector):
    CONNECTOR_ID = "reddit_buildapcsalesuk"
    SUBREDDIT = "buildapcsalesuk"

    def __init__(self) -> None:
        super().__init__(
            _load_template_or_default(
                self.CONNECTOR_ID,
                display_name="Reddit buildapcsalesuk",
                source_role=SourceType.MARKETPLACE,
                endpoint_url="https://www.reddit.com/r/buildapcsalesuk/new/.rss?limit={limit}&restrict_sr=1",
            )
        )


class HotUKDealsConnector(TemplateConnector):
    CONNECTOR_ID = "hotukdeals"
    cache_retention_days = 7

    def __init__(self, cache_path: str | Path | None = None) -> None:
        super().__init__(
            _load_template_or_default(
                self.CONNECTOR_ID,
                display_name="HotUKDeals",
                source_role=SourceType.SIGNAL,
                endpoint_url="https://www.hotukdeals.com/rss/new",
            )
        )
        self._cache = _HotUKDealsCache(
            Path(cache_path or "~/.cache/pricerecon/hotukdeals.json"), self.cache_retention_days
        )

    @property
    def cache_size(self) -> int:
        return len(self._cache.entries)

    async def search(
        self, query: str, filters: Optional[dict[str, Any]] = None
    ) -> list[NormalizedListing]:
        try:
            result = self.fetch_entries(self._render_url(query=query, filters=filters or {}))
            entries = await result if inspect.isawaitable(result) else result
            self._cache.upsert(entries)
            self._cache.save()
        except Exception:
            entries = list(self._cache.entries.values())
            if not entries:
                raise
        listings = _filter_listings_by_query(
            [self._entry_to_listing(entry) for entry in entries], query
        )
        for listing in listings:
            listing.in_stock = None
        return listings


class _HotUKDealsCache:
    def __init__(self, path: Path, retention_days: int) -> None:
        self.path = path.expanduser()
        self.retention = timedelta(days=retention_days)
        self.entries: dict[str, FeedEntry] = {}
        self._load()

    def _load(self) -> None:
        try:
            payload = json.loads(self.path.read_text())
        except (OSError, ValueError):
            return
        cutoff = datetime.now(timezone.utc) - self.retention
        for raw in payload.get("entries", []) if isinstance(payload, dict) else []:
            try:
                entry = FeedEntry.model_validate(raw)
            except Exception:
                continue
            if entry.published_at is None or entry.published_at >= cutoff:
                self.entries[entry.id] = entry

    def upsert(self, entries: list[FeedEntry], seen_at: datetime | None = None) -> None:
        cutoff = datetime.now(timezone.utc) - self.retention
        for entry in entries:
            if entry.published_at is None or entry.published_at >= cutoff:
                self.entries[entry.id] = entry
        self.entries = {
            key: entry
            for key, entry in self.entries.items()
            if entry.published_at is None or entry.published_at >= cutoff
        }

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(
                {"entries": [entry.model_dump(mode="json") for entry in self.entries.values()]}
            )
        )


def _looks_authenticated_out(content: str) -> bool:
    lowered = content.lower()
    return any(
        marker in lowered
        for marker in (
            "log in to reddit",
            "sign in to reddit",
            "session has expired",
            "your session has expired",
        )
    )


def _looks_blocked(content: str) -> bool:
    lowered = content.lower()
    return any(
        marker in lowered
        for marker in (
            "robot check",
            "verify you are human",
            "access denied",
            "temporarily blocked",
        )
    )


def _parse_browser_posts(
    content: str, subreddit: str, limit: int, query: str = ""
) -> list[FeedEntry]:
    """Parse Reddit JSON listings, HTML, and Camofox text snapshots.

    Camofox returns an accessibility/text snapshot rather than guaranteed HTML.
    Those snapshots can contain pinned/sidebar links before the query results.
    When a query is supplied, select matching candidates before applying the
    limit so unrelated navigation content cannot crowd out the result set.
    """
    query_terms = _query_terms(query)

    def matches_query(entry: FeedEntry) -> bool:
        if not query_terms:
            return True
        haystack = " ".join((entry.title, entry.content, entry.link)).lower()
        return all(term in haystack for term in query_terms)

    try:
        payload = json.loads(content)
    except (TypeError, ValueError):
        payload = None
    children = payload.get("data", {}).get("children", []) if isinstance(payload, dict) else []
    if isinstance(children, list):
        entries: list[FeedEntry] = []
        for child in children:
            data = child.get("data", {}) if isinstance(child, dict) else {}
            if not isinstance(data, dict):
                continue
            permalink = str(data.get("permalink") or "")
            link = str(
                data.get("url") or (f"https://www.reddit.com{permalink}" if permalink else "")
            )
            if not link or not data.get("title"):
                continue
            created = data.get("created_utc")
            try:
                published = (
                    datetime.fromtimestamp(float(created), tz=timezone.utc) if created else None
                )
            except (TypeError, ValueError, OverflowError):
                published = None
            entry = FeedEntry(
                id=str(data.get("id") or hashlib.sha1(link.encode()).hexdigest()),
                title=str(data.get("title") or ""),
                link=link,
                content=str(data.get("selftext") or ""),
                author=str(data.get("author") or "") or None,
                published_at=published,
            )
            if matches_query(entry):
                entries.append(entry)
        if entries:
            return entries[:limit]

    # Accessibility snapshots expose post links as standalone `/url:` lines.
    # Parse this shape before HTML parsing, which can otherwise treat the
    # snapshot's textual pseudo-markup as empty anchor nodes.
    snapshot_entries: list[FeedEntry] = []
    snapshot_seen: set[str] = set()
    snapshot_lines = content.splitlines()
    for index, line in enumerate(snapshot_lines):
        url_match = re.search(
            r"/url:\s*[\"']?(?P<link>(?:https?://(?:www\.)?reddit\.com|)/r/[^\s\"']+/comments/[^\s\"']+)",
            line,
        )
        if not url_match:
            continue
        link = url_match.group("link").rstrip(".,)")
        if link.startswith("/r/"):
            link = f"https://www.reddit.com{link}"
        if f"/r/{subreddit.lower()}/comments/" not in link.lower() or link in snapshot_seen:
            continue
        snapshot_seen.add(link)
        title = ""
        for previous in reversed(snapshot_lines[max(0, index - 6) : index]):
            title_match = re.search(
                r"(?:heading|link) [\"'](.+?)[\"'](?: \[level=\d+\])?:$", previous
            )
            if title_match:
                title = title_match.group(1)
                break
        entry = FeedEntry(
            id=hashlib.sha1(link.encode()).hexdigest(),
            title=re.sub(r"\s+", " ", title).strip(),
            link=link,
        )
        if matches_query(entry):
            snapshot_entries.append(entry)
    if snapshot_entries:
        return snapshot_entries[:limit]

    parser = HTMLParser(content)
    entries = []
    seen: set[str] = set()
    for anchor in parser.css("a[href*='/comments/']"):
        href = anchor.attributes.get("href", "")
        title = anchor.text(strip=True)
        if not title or not href:
            continue
        link = href if href.startswith("http") else f"https://www.reddit.com{href}"
        if f"/r/{subreddit.lower()}/comments/" not in link.lower():
            continue
        if link in seen:
            continue
        seen.add(link)
        body = anchor.parent.text(strip=True) if anchor.parent is not None else ""
        entry = FeedEntry(
            id=hashlib.sha1(link.encode()).hexdigest(), title=title, link=link, content=body
        )
        if matches_query(entry):
            entries.append(entry)
        if len(entries) >= limit:
            break
    # Camofox's text snapshot can omit anchor markup; retain only recognizable
    # Reddit post URLs and use the surrounding line as a title. Accessibility
    # snapshots put the title and ``/url:`` on adjacent lines, so handle both
    # that shape and the older same-line fallback.
    if not entries:
        candidates: list[FeedEntry] = []
        snapshot_lines = content.splitlines()
        for index, line in enumerate(snapshot_lines):
            url_match = re.search(
                r"/url:\s*[\"']?(?P<link>(?:https?://(?:www\.)?reddit\.com|)/r/[^\s\"']+/comments/[^\s\"']+)",
                line,
            )
            if not url_match:
                continue
            link = url_match.group("link").rstrip(".,)")
            if link.startswith("/r/"):
                link = f"https://www.reddit.com{link}"
            if f"/r/{subreddit.lower()}/comments/" not in link.lower():
                continue
            if link in seen:
                continue
            seen.add(link)
            title = ""
            for previous in reversed(snapshot_lines[max(0, index - 6) : index]):
                title_match = re.search(
                    r"(?:heading|link) [\"'](.+?)[\"'](?: \[level=\d+\])?:$", previous
                )
                if title_match:
                    title = title_match.group(1)
                    break
            entry = FeedEntry(
                id=hashlib.sha1(link.encode()).hexdigest(),
                title=re.sub(r"\s+", " ", title).strip(),
                link=link,
            )
            if matches_query(entry):
                candidates.append(entry)
        if not candidates:
            for match in re.finditer(
                r"(?P<title>.{5,200}?)\s+(?P<link>https?://(?:www\.)?reddit\.com/r/[^\s]+/comments/[^\s]+)",
                content,
            ):
                link = match.group("link").rstrip(".,)")
                if f"/r/{subreddit.lower()}/comments/" not in link.lower() or link in seen:
                    continue
                seen.add(link)
                entry = FeedEntry(
                    id=hashlib.sha1(link.encode()).hexdigest(),
                    title=re.sub(r"\s+", " ", match.group("title")).strip(),
                    link=link,
                )
                if matches_query(entry):
                    candidates.append(entry)
        entries.extend(candidates[:limit])
    return entries
