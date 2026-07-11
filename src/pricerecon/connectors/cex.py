"""CeX connector using Algolia search API.

POSTs to https://search.webuy.io/1/indexes/prod_cex_uk/query.
Parses hits into NormalizedListing format.
Filters out entries with empty stores array (catalog-only).
Maps Grade A/B/C to Excellent/Good/Fair.
"""

from decimal import Decimal
from typing import Any, Optional

import httpx

from pricerecon.connectors.base import BaseConnector
from pricerecon.models import NormalizedListing, SourceType, Condition


# CeX grade mapping
GRADE_MAP = {
    "A": Condition.USED_LIKE_NEW,  # Excellent/Mint
    "B": Condition.USED_GOOD,       # Good
    "C": Condition.USED_FAIR,       # Fair
}


class CexConnector(BaseConnector):
    """CeX UK connector via Algolia search API."""

    @property
    def source_role(self) -> SourceType:
        """CeX is a retailer."""
        return SourceType.RETAILER

    @property
    def connector_id(self) -> str:
        """Connector identifier."""
        return "cex"

    async def search(
        self,
        query: str,
        filters: Optional[dict[str, Any]] = None,
    ) -> list[NormalizedListing]:
        """Search CeX for matching listings.

        Args:
            query: Search query string (e.g., "RTX 3090")
            filters: Optional filters (price_max, condition, etc.)

        Returns:
            List of normalized listings
        """
        if filters is None:
            filters = {}

        # Build Algolia query payload
        payload = {
            "query": query,
            "hitsPerPage": filters.get("limit", 50),
        }

        # Apply price filter if provided
        price_max = filters.get("price_max")
        if price_max:
            payload["filters"] = f"sellPrice <= {int(price_max)}"

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://search.webuy.io/1/indexes/prod_cex_uk/query",
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "Mozilla/5.0 (compatible; PriceRecon/1.0)",
                }
            )
            response.raise_for_status()
            data = response.json()

        hits = data.get("hits", [])
        listings = []

        for hit in hits:
            listing = self._parse_hit(hit)
            if listing:
                listings.append(listing)

        return listings

    def _parse_hit(self, hit: dict[str, Any]) -> Optional[NormalizedListing]:
        """Parse a CeX Algolia hit into NormalizedListing.

        Filters out entries with empty stores array (catalog-only, not buyable).
        Maps Grade A/B/C to Excellent/Good/Fair.

        Args:
            hit: Algolia hit data

        Returns:
            NormalizedListing or None if filtered out
        """
        # Filter out entries with empty stores array
        stores = hit.get("stores", [])
        if not stores:
            # No stores have stock - catalog-only entry, not buyable
            return None

        # Check if in stock online
        in_stock = hit.get("inStockOnline", False)

        # Extract basic fields
        box_id = hit.get("boxId")
        box_name = hit.get("boxName", "")
        sell_price = hit.get("sellPrice")
        image_urls = hit.get("imageUrls", {})

        if not box_id or not box_name or sell_price is None:
            # Missing required fields
            return None

        # Build product URL
        slug = hit.get("slug", box_id.lower())
        url = f"https://uk.webuy.com/product-detail/{slug}/{box_id}.html"

        # Map grade to condition
        grades = hit.get("Grade", [])
        condition = None
        condition_raw = None

        if grades:
            grade = grades[0]
            condition = GRADE_MAP.get(grade)
            condition_raw = f"Grade {grade}"

        # Extract image URL (prefer medium, fall back to large, then small)
        image_url = None
        if image_urls:
            image_url = (
                image_urls.get("medium")
                or image_urls.get("large")
                or image_urls.get("small")
            )

        return NormalizedListing(
            source="cex",
            source_type=self.source_role,
            source_listing_id=box_id,
            title_raw=box_name,
            price=Decimal(str(sell_price)),
            currency="GBP",
            url=url,
            condition=condition,
            condition_raw=condition_raw,
            in_stock=in_stock,
            image_url=image_url,
            seller_or_store="CeX",  # CeX is the retailer
        )