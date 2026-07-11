"""eBay Browse API connector with OAuth token management."""

import logging
from datetime import datetime, timedelta
from typing import Any, Optional

import httpx
from pydantic import BaseModel, Field

from pricerecon.connectors.base import BaseConnector
from pricerecon.models import Condition, NormalizedListing, SourceType

logger = logging.getLogger(__name__)


class eBayOAuthToken(BaseModel):
    """OAuth token model for eBay."""

    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    refresh_token: Optional[str] = None
    expires_at: datetime = Field(default_factory=datetime.utcnow)


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

        cursor.execute(
            """
            SELECT config_json FROM connector_configs
            WHERE connector_id = 'ebay'
        """
        )
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
            # Add 5 minute buffer for expiry
            if token.expires_at > datetime.utcnow() + timedelta(minutes=5):
                return token
        except Exception as e:
            logger.warning(f"Failed to parse stored token: {e}")

        return None

    def save_token(self, token: eBayOAuthToken) -> None:
        """Save token to database."""
        import sqlite3
        import json
        from pathlib import Path

        db = Path(self.db_path)
        if not db.exists():
            logger.error(f"Database not found at {self.db_path}")
            return

        conn = sqlite3.connect(db)
        cursor = conn.cursor()

        config_json = json.dumps({"oauth_token": token.model_dump()})

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
    """eBay Browse API connector.

    Uses OAuth client credentials grant for application access token.
    Tokens last ~2 hours and are auto-refreshed on expiry.
    """

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
        """Initialize HTTP client and OAuth token."""
        self._client = httpx.AsyncClient(timeout=30.0)
        await self.ensure_token()

    async def cleanup(self) -> None:
        """Cleanup HTTP client."""
        if self._client:
            await self._client.aclose()

    async def ensure_token(self) -> str:
        """Ensure we have a valid OAuth token, refreshing if needed."""
        token = self.token_store.get_token()
        if token:
            return token.access_token

        # Fetch new token via client credentials grant
        logger.info("Fetching new eBay OAuth token")
        token = await self._fetch_token()
        self.token_store.save_token(token)
        return token.access_token

    async def _fetch_token(self) -> eBayOAuthToken:
        """Fetch OAuth token using client credentials grant."""
        # eBay OAuth endpoint
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
        expires_at = datetime.utcnow() + timedelta(seconds=token_data["expires_in"])

        return eBayOAuthToken(
            access_token=token_data["access_token"],
            token_type=token_data["token_type"],
            expires_in=token_data["expires_in"],
            refresh_token=token_data.get("refresh_token"),
            expires_at=expires_at,
        )

    def _get_basic_auth(self) -> str:
        """Generate Basic auth header from app_id:cert_id."""
        import base64
        import os

        # If cert_id not provided, use app_id for both
        secret = self.cert_id or self.app_id
        credentials = f"{self.app_id}:{secret}"
        return base64.b64encode(credentials.encode()).decode()

    async def search(self, query: str, filters: Optional[dict[str, Any]] = None) -> list[NormalizedListing]:
        """Search eBay Browse API for listings.

        Args:
            query: Search query (e.g., "RTX 3090")
            filters: Optional filters (price_max, condition, category, etc.)

        Returns:
            List of normalized listings
        """
        filters = filters or {}
        await self.ensure_token()

        token = self.token_store.get_token()
        if not token:
            raise RuntimeError("Failed to obtain OAuth token")

        # Build Browse API request
        url = "https://api.ebay.com/buy/browse/v1/item_summary/search"

        headers = {
            "Authorization": f"Bearer {token.access_token}",
            "Content-Type": "application/json",
            "X-EBAY-C-MARKETPLACE-ID": "EBAY_GB",  # UK marketplace
        }

        params = {"q": query, "limit": 50}

        # Apply filters
        if "price_max" in filters:
            params["filter"] = f"price:[0..{filters['price_max']}]"

        if "condition" in filters:
            # Map condition enum to eBay filter values
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

        response = await self._client.get(url, headers=headers, params=params)
        response.raise_for_status()

        data = response.json()
        return self._parse_listings(data.get("itemSummaries", []))

    def _parse_listings(self, items: list[dict]) -> list[NormalizedListing]:
        """Parse eBay itemSummaries into NormalizedListing objects."""
        listings = []

        for item in items:
            try:
                # Extract price
                price_value = item.get("price", {}).get("value", "0")
                currency = item.get("price", {}).get("currency", "GBP")

                # Map condition
                condition = self._map_condition(item.get("condition"))

                # Extract seller info
                seller = item.get("seller", {})
                seller_name = seller.get("username")
                seller_feedback = seller.get("feedbackScore")
                seller_feedback_pct = seller.get("feedbackPercentage")

                listing = NormalizedListing(
                    source="ebay",
                    source_type=SourceType.MARKETPLACE,
                    source_listing_id=item["itemId"],
                    title_raw=item["title"],
                    price=float(price_value),
                    currency=currency,
                    url=item.get("itemWebUrl", ""),
                    condition=condition,
                    condition_raw=item.get("condition"),
                    seller_or_store=seller_name,
                    seller_feedback_score=seller_feedback,
                    seller_feedback_pct=float(seller_feedback_pct) if seller_feedback_pct else None,
                    image_url=item.get("image", {}).get("imageUrl"),
                    category="unknown",  # Could be derived from category hints
                )
                listings.append(listing)
            except Exception as e:
                logger.warning(f"Failed to parse eBay item {item.get('itemId')}: {e}")
                continue

        return listings

    def _map_condition(self, ebay_condition: Optional[str]) -> Optional[Condition]:
        """Map eBay condition strings to NormalizedListing Condition enum."""
        if not ebay_condition:
            return None

        condition_map = {
            "New": Condition.NEW,
            "New with tags": Condition.NEW,
            "New without tags": Condition.NEW_OPEN_BOX,
            "New with defects": Condition.NEW_OPEN_BOX,
            "Open box": Condition.NEW_OPEN_BOX,
            "Certified refurbished": Condition.REFURBISHED,
            "Excellent - Refurbished": Condition.REFURBISHED,
            "Very Good - Refurbished": Condition.REFURBISHED,
            "Good - Refurbished": Condition.REFURBISHED,
            "Refurbished": Condition.REFURBISHED,
            "Like New": Condition.USED_LIKE_NEW,
            "Very Good": Condition.USED_GOOD,
            "Good": Condition.USED_GOOD,
            "Acceptable": Condition.USED_FAIR,
            "For parts or not working": Condition.FOR_PARTS,
        }

        return condition_map.get(ebay_condition)