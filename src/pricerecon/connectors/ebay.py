"""eBay Browse API connector with OAuth token management."""

import logging
from decimal import Decimal
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import httpx
from pydantic import BaseModel, Field

from pricerecon.connectors.base import BaseConnector
from pricerecon.models import NormalizedListing, SourceType

logger = logging.getLogger(__name__)


class eBayOAuthToken(BaseModel):
    """OAuth token model for eBay."""

    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    refresh_token: Optional[str] = None
    expires_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


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
            logger.warning(f"Failed to parse stored token: {e}")

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
                logger.warning(f"Failed to parse existing config: {e}")

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


class eBayConnector(BaseConnector):
    """eBay Browse API connector."""

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
        self._client = httpx.AsyncClient(timeout=30.0)
        await self.ensure_token()

    async def cleanup(self) -> None:
        if self._client:
            await self._client.aclose()

    async def ensure_token(self) -> str:
        token = self.token_store.get_token()
        if token:
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
                logger.warning(f"Failed to delete cached token: {e}")

        conn.close()

    async def _fetch_token(self) -> eBayOAuthToken:
        url = "https://api.ebay.com/identity/v1/oauth2/token"

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Basic {self._get_basic_auth()}",
        }

        data = {
            "grant_type": "client_credentials",
            "scope": "https://api.ebay.com/oauth/api_scope",
        }

        if not self._client:
            raise RuntimeError("HTTP client not initialized")

        response = await self._client.post(url, headers=headers, data=data)
        response.raise_for_status()

        token_data = response.json()
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=token_data["expires_in"])

        return eBayOAuthToken(
            access_token=token_data["access_token"],
            token_type=token_data.get("token_type", "Bearer"),
            expires_in=token_data["expires_in"],
            refresh_token=token_data.get("refresh_token"),
            expires_at=expires_at,
        )

    def _get_basic_auth(self) -> str:
        import base64

        secret = self.cert_id or self.app_id
        credentials = f"{self.app_id}:{secret}"
        return base64.b64encode(credentials.encode()).decode()

    def _clear_health_error(self) -> None:
        """Clear stale error state after a successful token refresh."""
        from pricerecon.core.connector_health import upsert_connector_health

        upsert_connector_health(
            self.CONNECTOR_ID,
            status="ok",
            last_error=None,
            details={"token_refreshed": True},
        )

    def _mark_health_error(self, error: str) -> None:
        """Record a token refresh failure in connector health."""
        from pricerecon.core.connector_health import upsert_connector_health

        upsert_connector_health(
            self.CONNECTOR_ID,
            status="auth_failed",
            last_error=error,
            details={"error": error, "error_type": "TokenRefreshError"},
        )

    async def search(
        self, query: str, filters: Optional[dict[str, Any]] = None
    ) -> list[NormalizedListing]:
        filters = filters or {}
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