"""Laptops Direct connector using HTML parsing.

Searches category pages and extracts product data from static HTML.
Products are identified by data-cnstrc-item-* attributes (Constructor.io integration).
"""

from decimal import Decimal
from typing import Any, Optional

import httpx
from selectolax.parser import HTMLParser

from pricerecon.connectors.base import BaseConnector
from pricerecon.models import NormalizedListing, SourceType


class LaptopsDirectConnector(BaseConnector):
    """Laptops Direct UK connector via static HTML scraping."""

    @property
    def source_role(self) -> SourceType:
        """Laptops Direct is a retailer."""
        return SourceType.RETAILER

    @property
    def connector_id(self) -> str:
        """Connector identifier."""
        return "laptopsdirect"

    async def search(
        self,
        query: str,
        filters: Optional[dict[str, Any]] = None,
    ) -> list[NormalizedListing]:
        """Search Laptops Direct for matching listings.

        Args:
            query: Search query string (e.g., "RTX 5070")
            filters: Optional filters (price_max, condition, etc.)

        Returns:
            List of normalized listings
        """
        if filters is None:
            filters = {}

        # For category-based search, map query to category URL
        # This is a simple mapping - in production you'd use their search API
        search_urls = {
            "rtx 5070": "https://www.laptopsdirect.co.uk/ct/pcs/geforce-rtx-5070",
            "rtx 5060": "https://www.laptopsdirect.co.uk/ct/pcs/geforce-rtx-5060",
            "rtx 4090": "https://www.laptopsdirect.co.uk/ct/graphics-cards/nvidia-geforce",
            "rtx 4080": "https://www.laptopsdirect.co.uk/ct/graphics-cards/nvidia-geforce",
            "rtx 4070": "https://www.laptopsdirect.co.uk/ct/graphics-cards/nvidia-geforce",
        }

        query_lower = query.lower()
        url = search_urls.get(
            query_lower, "https://www.laptopsdirect.co.uk/ct/graphics-cards/nvidia-geforce"
        )

        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(
                url,
                headers={"User-Agent": "Mozilla/5.0 (compatible; PriceRecon/1.0)"},
            )
            response.raise_for_status()
            html = response.text

        return self._parse_html(html)

    def _parse_html(self, html: str) -> list[NormalizedListing]:
        """Parse Laptops Direct HTML into NormalizedListing objects.

        Extracts products from div[aria-label="found product"] elements.
        Uses data-cnstrc-item-* attributes for structured data.

        Args:
            html: Raw HTML from category page

        Returns:
            List of normalized listings
        """
        parser = HTMLParser(html)
        listings = []

        for card in parser.css('div[aria-label="found product"]'):
            # Extract from data-cnstrc-item-* attributes
            item_id = card.attributes.get("data-cnstrc-item-id")
            item_name = card.attributes.get("data-cnstrc-item-name")
            item_price = card.attributes.get("data-cnstrc-item-price")

            if not item_id or not item_name or not item_price:
                continue

            # Parse price (comes as string like "1949.00")
            try:
                price = Decimal(str(item_price))
            except Exception:
                continue

            # Extract URL and image
            link = card.css_first("a[href]")
            img = card.css_first("img.offerImage")

            if not link:
                continue

            href = link.attributes.get("href", "")
            if not href:
                continue

            # Build full URL
            if href.startswith("/"):
                full_url = f"https://www.laptopsdirect.co.uk{href}"
            else:
                full_url = href

            # Extract image URL
            image_url = None
            if img:
                img_src = img.attributes.get("src") or img.attributes.get("data-src")
                if img_src:
                    if img_src.startswith("/"):
                        image_url = f"https://www.laptopsdirect.co.uk{img_src}"
                    else:
                        image_url = img_src

            listings.append(
                NormalizedListing(
                    source="laptopsdirect",
                    source_type=self.source_role,
                    source_listing_id=item_id,
                    title_raw=item_name,
                    price=price,
                    currency="GBP",
                    url=full_url,
                    image_url=image_url,
                    in_stock=True,  # Assume in stock for products shown
                    product_normalized=None,
                    variant_normalized=None,
                    condition=None,
                    condition_raw=None,
                    shipping_cost=None,
                    total_landed_cost=None,
                    seller_or_store="Laptops Direct",
                    seller_feedback_score=None,
                    seller_feedback_pct=None,
                    location=None,
                    stock_state=None,
                    exact_variant_confirmed=None,
                    variant_match_confidence=None,
                    mismatch_flags=None,
                    risk_flags=None,
                    category="gpu",
                )
            )

        return listings
