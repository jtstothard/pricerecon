"""eBay Browse API connector with OAuth token management - Enhanced with startup burst protection."""

import logging
import asyncio
import re
from decimal import Decimal
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from urllib.parse import quote_plus

import httpx

from pricerecon.core.collection_transport import collection_http_client
from pydantic import BaseModel, Field, field_validator

from pricerecon.connectors.base import BaseConnector
from pricerecon.connectors.external_browser import as_connector_degraded_error
from pricerecon.models import NormalizedListing, SourceType

logger = logging.getLogger(__name__)


class eBayOAuthToken(BaseModel):
    """OAuth token model for eBay."""

    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    refresh_token: Optional[str] = None
    expires_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("expires_at")
    @classmethod
    def ensure_utc_expiry(cls, value: datetime) -> datetime:
        """Keep persisted expiry values comparable with the UTC clock.

        Older rows may contain an ISO timestamp without an offset. Treat those
        values as UTC rather than allowing a naive/aware comparison to fail and
        silently discard an otherwise usable token.
        """
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)


class eBayTokenStore:
    """Persistent storage for eBay OAuth tokens."""

    def __init__(self, db_path: str):
        self.db_path = db_path

    def get_token(self) -> Optional[eBayOAuthToken]:
        """Get stored token if not expired."""
        import sqlite3
        from pathlib import Path

        db = Path(self.db_path)
        if not db.exists():
            return None

        conn = sqlite3.connect(db)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT config_json FROM connector_configs
            WHERE connector_id = 'ebay'
        """)
        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        try:
            import json

            config = json.loads(row[0])
            token_data = config.get("oauth_token")
            if not token_data:
                return None

            token = eBayOAuthToken(**token_data)
            if token.expires_at > datetime.now(timezone.utc) + timedelta(minutes=5):
                return token
        except Exception as e:
            logger.warning("Failed to parse stored token (%s)", type(e).__name__)

        return None

    def save_token(self, token: eBayOAuthToken) -> None:
        """Save token to database, preserving existing config keys."""
        import sqlite3
        import json
        from pathlib import Path

        db = Path(self.db_path)

        if not db.exists():
            db.parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(db)
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS connector_configs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    connector_id TEXT NOT NULL UNIQUE,
                    config_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
            """)
            conn.commit()
            conn.close()
            logger.info(f"Created database at {self.db_path}")

        conn = sqlite3.connect(db)
        cursor = conn.cursor()

        # Read existing config to preserve other keys
        cursor.execute("SELECT config_json FROM connector_configs WHERE connector_id = 'ebay'")
        row = cursor.fetchone()

        existing_config = {}
        if row:
            try:
                existing_config = json.loads(row[0])
            except Exception as e:
                logger.warning("Failed to parse existing config (%s)", type(e).__name__)

        # Merge the new token data
        existing_config["oauth_token"] = token.model_dump(mode="json")
        config_json = json.dumps(existing_config)

        cursor.execute(
            """
            INSERT INTO connector_configs (connector_id, config_json)
            VALUES ('ebay', ?)
            ON CONFLICT(connector_id) DO UPDATE SET config_json = ?, updated_at = CURRENT_TIMESTAMP
        """,
            (config_json, config_json),
        )

        conn.commit()
        conn.close()
        logger.info("eBay OAuth token saved to database")


class _EBayTokenFetchCoordinator:
    """Singleton coordinator for OAuth token fetches to prevent startup burst.

    Ensures that only one token fetch happens at a time across all connector
    instances, even during container restart when multiple watches fire simultaneously.
    """

    _instance: Optional["_EBayTokenFetchCoordinator"] = None
    _active_fetches: dict[str, asyncio.Task[eBayOAuthToken]] = {}
    _active_fetches_lock: asyncio.Lock = asyncio.Lock()

    def __new__(cls) -> "_EBayTokenFetchCoordinator":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    async def fetch_token(
        cls,
        app_id: str,
        cert_id: Optional[str],
        client: httpx.AsyncClient,
        max_retries: int = 3,
        initial_backoff: float = 1.0,
    ) -> eBayOAuthToken:
        """Fetch a new OAuth token with retry logic and deduplication.

        Args:
            app_id: eBay application ID
            cert_id: eBay certificate ID (or None to use app_id as secret)
            client: HTTP client for making requests
            max_retries: Maximum number of retry attempts
            initial_backoff: Initial backoff time in seconds (exponential backoff)

        Returns:
            OAuth token

        Raises:
            RuntimeError: If token fetch fails after all retries
        """
        cache_key = f"{app_id}:{cert_id or app_id}"

        # First, check if there's already an active fetch (lock-protected read)
        async with cls._active_fetches_lock:
            if cache_key in cls._active_fetches:
                logger.info("Waiting for in-progress eBay token fetch")
                existing_task = cls._active_fetches[cache_key]
                # Don't release lock until we've added a waiter
                # The existing task will clean up the entry
                try:
                    result: eBayOAuthToken = await existing_task
                    return result
                finally:
                    # The existing task will clean up the active fetches dict
                    pass
            else:
                # No active fetch, create new one
                fetch_task = asyncio.create_task(
                    cls._fetch_token_with_retry(
                        app_id, cert_id, client, max_retries, initial_backoff
                    )
                )
                cls._active_fetches[cache_key] = fetch_task

        try:
            result = await fetch_task
            return result
        finally:
            # Clean up completed task
            async with cls._active_fetches_lock:
                if cache_key in cls._active_fetches and cls._active_fetches[cache_key].done():
                    cls._active_fetches.pop(cache_key, None)

    @staticmethod
    async def _fetch_token_with_retry(
        app_id: str,
        cert_id: Optional[str],
        client: httpx.AsyncClient,
        max_retries: int,
        initial_backoff: float,
    ) -> eBayOAuthToken:
        """Fetch token with exponential backoff retry logic."""

        url = "https://api.ebay.com/identity/v1/oauth2/token"
        backoff = initial_backoff

        for attempt in range(max_retries):
            try:

                headers = {
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Authorization": f"Basic {_get_basic_auth(app_id, cert_id)}",
                }

                data = {
                    "grant_type": "client_credentials",
                    "scope": "https://api.ebay.com/oauth/api_scope",
                }

                response = await client.post(url, headers=headers, data=data)
                response.raise_for_status()

                token_data = response.json()
                expires_at = datetime.now(timezone.utc) + timedelta(
                    seconds=token_data["expires_in"]
                )

                logger.info(
                    f"Successfully fetched eBay OAuth token on attempt {attempt + 1}/{max_retries}"
                )

                return eBayOAuthToken(
                    access_token=token_data["access_token"],
                    token_type=token_data.get("token_type", "Bearer"),
                    expires_in=token_data["expires_in"],
                    refresh_token=token_data.get("refresh_token"),
                    expires_at=expires_at,
                )

            except httpx.HTTPStatusError as exc:
                status_code = exc.response.status_code

                # Retry on rate limiting (429) or server errors (5xx)
                if attempt < max_retries - 1 and (status_code == 429 or status_code >= 500):
                    logger.warning(
                        f"Token fetch failed with status {status_code}, "
                        f"retrying in {backoff}s (attempt {attempt + 1}/{max_retries})"
                    )
                    await asyncio.sleep(backoff)
                    backoff *= 2  # Exponential backoff
                elif status_code == 401:
                    # 401 on token endpoint suggests invalid credentials, don't retry
                    logger.error("Token fetch failed with 401: invalid credentials")
                    raise RuntimeError(
                        "eBay OAuth token fetch failed with 401: invalid credentials. "
                        "Check EBAY_APP_ID and EBAY_CERT_ID environment variables."
                    ) from None
                else:
                    # Other errors, raise immediately
                    logger.error(f"Token fetch failed with status {status_code}")
                    raise RuntimeError(
                        f"eBay OAuth token fetch failed: HTTP {exc.response.status_code}"
                    ) from None

            except (httpx.HTTPError, ValueError, TypeError, KeyError, OverflowError) as exc:
                if attempt < max_retries - 1:
                    logger.warning(
                        f"Token fetch failed with exception, retrying in {backoff}s "
                        f"(attempt {attempt + 1}/{max_retries}; {type(exc).__name__})"
                    )
                    await asyncio.sleep(backoff)
                    backoff *= 2
                else:
                    logger.error(
                        "Token fetch failed after %s attempts (%s)", max_retries, type(exc).__name__
                    )
                    raise RuntimeError(
                        f"eBay OAuth token fetch failed ({type(exc).__name__})"
                    ) from None

        # Should never reach here, but just in case
        raise RuntimeError(f"eBay OAuth token fetch failed after {max_retries} attempts")


def _get_basic_auth(app_id: str, cert_id: Optional[str]) -> str:
    """Generate Basic auth header for eBay OAuth."""
    import base64

    secret = cert_id or app_id
    credentials = f"{app_id}:{secret}"
    return base64.b64encode(credentials.encode()).decode()


class eBayConnector(BaseConnector):
    collection_accounting = "http_v1"

    """eBay Browse API connector with startup burst protection."""

    CONNECTOR_ID = "ebay"

    def __init__(self, app_id: str, cert_id: Optional[str] = None, db_path: str = "pricerecon.db"):
        self.app_id = app_id
        self.cert_id = cert_id
        self.db_path = db_path
        self.token_store = eBayTokenStore(db_path)
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def source_role(self) -> SourceType:
        return SourceType.MARKETPLACE

    async def initialize(self) -> None:
        self._client = collection_http_client(timeout=30.0)
        await self.ensure_token()

    async def cleanup(self) -> None:
        if self._client:
            await self._client.aclose()

    async def ensure_token(self) -> str:

        token = self.token_store.get_token()
        if token:
            # Clear stale auth_failed health when a valid cached token is used
            self._clear_health_error()
            logger.info(
                f"Using cached eBay OAuth token (valid until {token.expires_at.isoformat()})"
            )
            return token.access_token

        logger.info("Fetching new eBay OAuth token")
        try:
            token = await self._fetch_token()
            self.token_store.save_token(token)
            self._clear_health_error()
            return token.access_token
        except Exception as exc:
            self._mark_health_error(str(exc))
            raise

    def _delete_cached_token(self) -> None:
        """Delete the cached token from the database."""
        import sqlite3
        from pathlib import Path

        db = Path(self.db_path)
        if not db.exists():
            return

        conn = sqlite3.connect(db)
        cursor = conn.cursor()

        # Remove oauth_token from config
        cursor.execute("SELECT config_json FROM connector_configs WHERE connector_id = 'ebay'")
        row = cursor.fetchone()

        if row:
            try:
                import json

                config = json.loads(row[0])
                if "oauth_token" in config:
                    del config["oauth_token"]
                    config_json = json.dumps(config)
                    cursor.execute(
                        """
                        UPDATE connector_configs
                        SET config_json = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE connector_id = 'ebay'
                    """,
                        (config_json,),
                    )
                    conn.commit()
                    logger.info("Deleted cached eBay OAuth token")
            except Exception as e:
                logger.warning("Failed to delete cached token (%s)", type(e).__name__)

        conn.close()

    async def _fetch_token(self) -> eBayOAuthToken:
        """Fetch a new OAuth token using the coordinator for burst protection."""
        if not self._client:
            raise RuntimeError("HTTP client not initialized")

        coordinator = _EBayTokenFetchCoordinator()
        return await coordinator.fetch_token(self.app_id, self.cert_id, self._client)

    def _clear_health_error(self) -> None:
        """Clear stale error state after a successful token refresh."""
        from pricerecon.core.connector_health import upsert_connector_health

        upsert_connector_health(
            self.CONNECTOR_ID,
            status="ok",
            last_error=None,
            details={"token_refreshed": True},
            checked_at=None,  # Token refresh is not a verified connector operation
        )

    def _mark_health_error(self, error: str) -> None:
        """Record a token refresh failure in connector health."""
        from pricerecon.core.connector_health import upsert_connector_health

        upsert_connector_health(
            self.CONNECTOR_ID,
            status="auth_failed",
            last_error=error,
            details={"error": error, "error_type": "TokenRefreshError"},
            checked_at=None,  # Token refresh is not a verified connector operation
        )

    async def search(
        self, query: str, filters: Optional[dict[str, Any]] = None
    ) -> list[NormalizedListing]:
        filters = filters or {}
        browser_result = await self.navigate_external_browser(
            f"https://www.ebay.co.uk/sch/i.html?_nkw={quote_plus(query)}"
        )
        if browser_result is not None:
            if browser_result.degraded or not browser_result.rendered.html:
                raise as_connector_degraded_error(browser_result, self.CONNECTOR_ID)
            # A browser selection is authoritative for this execution. Do not
            # mask a bad browser acquisition with a successful Browse API call.
            return self.annotate_browser_result(
                self._parse_browser_listings(browser_result.rendered.html), browser_result
            )

        # The authenticated Browse API remains the default without an explicit
        # external browser selection.
        await self.ensure_token()

        token = self.token_store.get_token()
        if not token:
            raise RuntimeError("Failed to obtain OAuth token")

        url = "https://api.ebay.com/buy/browse/v1/item_summary/search"

        headers = {
            "Authorization": f"Bearer {token.access_token}",
            "Content-Type": "application/json",
            "X-EBAY-C-MARKETPLACE-ID": "EBAY_GB",
        }

        params = {"q": query, "limit": 50}

        if "price_max" in filters:
            params["filter"] = f"price:[0..{filters['price_max']}]"

        if "condition" in filters:
            condition_map = {
                "new": "New",
                "refurbished": "Refurbished",
                "used_like_new": "Used",
                "used_good": "Used",
                "used_fair": "Used",
            }
            condition = filters["condition"]
            if condition in condition_map:
                price_filter = params.get("filter", "")
                if price_filter:
                    params["filter"] = f"{price_filter},condition:{condition_map[condition]}"
                else:
                    params["filter"] = f"condition:{condition_map[condition]}"

        # Try the search, retry once on 401 with token refresh
        try:
            response = await self._client.get(url, headers=headers, params=params)  # type: ignore[union-attr, arg-type]
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 401:
                logger.warning("Got 401 from eBay API, forcing token refresh and retrying")
                # Delete cached token to force refresh
                self._delete_cached_token()
                # Get fresh token
                new_access_token = await self.ensure_token()
                # Update headers with new token
                headers["Authorization"] = f"Bearer {new_access_token}"
                # Retry the request once
                response = await self._client.get(url, headers=headers, params=params)  # type: ignore[union-attr, arg-type]
                response.raise_for_status()
            else:
                raise

        data = response.json()
        return self._parse_listings(data.get("itemSummaries", []))

    def _parse_browser_listings(self, html: str) -> list[NormalizedListing]:
        """Parse only current, priced eBay cards rendered by the selected browser."""
        listings: list[NormalizedListing] = []
        seen_ids: set[str] = set()
        for match in re.finditer(
            r'<li[^>]+class=["\'][^"\']*\bs-item\b[^"\']*["\'][^>]*>(.*?)</li>',
            html,
            re.IGNORECASE | re.DOTALL,
        ):
            card = match.group(1)
            url_match = re.search(
                r'href=["\'](https?://[^"\']*?/itm/(\d+)[^"\']*)["\']', card, re.IGNORECASE
            )
            title_match = re.search(
                r'class=["\'][^"\']*\bs-item__title\b[^"\']*["\'][^>]*>(.*?)</(?:div|h3|span)>',
                card,
                re.IGNORECASE | re.DOTALL,
            )
            price_match = re.search(
                r'class=["\'][^"\']*\bs-item__price\b[^"\']*["\'][^>]*>\s*(?:£|GBP\s*)?([\d,]+(?:\.\d{1,2})?)',
                card,
                re.IGNORECASE | re.DOTALL,
            )
            if not url_match or not title_match or not price_match:
                continue
            item_id = url_match.group(2)
            if item_id in seen_ids:
                continue
            title = re.sub(r"<[^>]+>", " ", title_match.group(1))
            title = re.sub(r"\s+", " ", title).strip()
            try:
                price = Decimal(price_match.group(1).replace(",", ""))
            except Exception:
                continue
            if not title or price <= 0:
                continue
            seen_ids.add(item_id)
            listings.append(
                NormalizedListing(
                    source="ebay",
                    source_type=self.source_role,
                    source_listing_id=item_id,
                    title_raw=title,
                    price=price,
                    currency="GBP",
                    url=url_match.group(1),
                    timestamp_seen=datetime.now(timezone.utc),
                    product_normalized=None,
                    variant_normalized=None,
                    condition=None,
                    condition_raw=None,
                    shipping_cost=None,
                    total_landed_cost=None,
                    seller_or_store=None,
                    seller_feedback_score=None,
                    seller_feedback_pct=None,
                    location=None,
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

    def _parse_listings(self, items: list[dict]) -> list[NormalizedListing]:
        listings = []

        for item in items:
            try:
                price = item.get("price", {})
                seller_data = item.get("seller", {})
                availability_data = item.get("availability", {}).get(
                    "shipToLocationAvailability", {}
                )
                feedback_pct_val = seller_data.get("feedbackPercentage")
                listing = NormalizedListing(
                    source="ebay",
                    source_type=self.source_role,
                    source_listing_id=str(item.get("itemId", "")),
                    title_raw=item.get("title", ""),
                    price=Decimal(str(price.get("value", 0))),
                    currency=price.get("currency", "GBP"),
                    url=item.get("itemWebUrl", ""),
                    timestamp_seen=datetime.now(timezone.utc),
                    product_normalized=None,
                    variant_normalized=None,
                    condition=None,
                    condition_raw=None,
                    shipping_cost=None,
                    total_landed_cost=None,
                    seller_or_store=seller_data.get("username"),
                    seller_feedback_score=seller_data.get("feedbackScore"),
                    seller_feedback_pct=(
                        Decimal(str(feedback_pct_val)) if feedback_pct_val else None
                    ),
                    location=None,
                    in_stock=availability_data.get("quantity", 1) > 0,
                    stock_state=None,
                    image_url=item.get("itemWebUrl"),
                    exact_variant_confirmed=None,
                    variant_match_confidence=None,
                    mismatch_flags=None,
                    risk_flags=None,
                    category=None,
                )
                listings.append(listing)
            except Exception as exc:
                logger.warning("Failed to parse eBay listing: %s", exc)

        return listings
