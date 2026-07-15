"""Gumtree connector using browser-assisted HTML parsing."""

import hashlib
import logging
import re
from decimal import Decimal
from typing import Any, Optional

from pricerecon.connectors.base import BaseConnector
from pricerecon.connectors.browser_client import (
    BrowserClient,
    BrowserSessionConfig,
    browser_context,
)
from pricerecon.models import NormalizedListing, SourceType, Condition

logger = logging.getLogger(__name__)


class GumtreeConnector(BaseConnector):
    """Gumtree connector for classified ads search results.

    Gumtree is a UK classifieds website for buying and selling items locally.
    This connector uses browser-assisted HTML parsing to extract listing data.
    """

    CONNECTOR_ID = "gumtree"
    display_name = "Gumtree"

    SEARCH_URL = "https://www.gumtree.com/search"

    def __init__(self, config: Optional[dict[str, Any]] = None):
        """Initialize the Gumtree connector.

        Args:
            config: Optional config with BrowserSessionConfig fields
                    (e.g., camofox_url, use_flare_solverr)
        """
        self.config = config or {}
        self.browser_client: Optional[BrowserClient] = None

    @property
    def source_role(self) -> SourceType:
        """Gumtree is a marketplace (classifieds)."""
        return SourceType.MARKETPLACE

    async def initialize(self) -> None:
        """Initialize browser client."""
        browser_config = BrowserSessionConfig(**self.config)
        self.browser_client = BrowserClient(config=browser_config)
        await self.browser_client.start()

    async def cleanup(self) -> None:
        """Cleanup browser resources."""
        if self.browser_client:
            await self.browser_client.close()

    async def search(
        self, query: str, filters: Optional[dict[str, Any]] = None
    ) -> list[NormalizedListing]:
        """Search Gumtree for matching listings.

        Args:
            query: Search query string
            filters: Optional filters (price_max, condition, etc.)

        Returns:
            List of normalized listings
        """
        filters = filters or {}

        if self.browser_client is None:
            await self.initialize()

        assert self.browser_client is not None

        try:
            # Build search URL
            url_with_params = f"{self.SEARCH_URL}?search_category=all&q={query}"

            # Fetch page with browser
            async with browser_context() as context:
                page = await context.new_page()
                await page.goto(url_with_params)
                html = await page.content()

            if not html:
                logger.error("Failed to fetch Gumtree HTML")
                return []

            listings = self._parse_search_results(html)
            logger.info(f"Gumtree found {len(listings)} listings for '{query}'")

            return listings

        except Exception as e:
            logger.error(f"Gumtree search failed: {e}")
            return []

    def _parse_search_results(self, html: str) -> list[NormalizedListing]:
        """Parse Gumtree search results HTML.

        Args:
            html: HTML response from gumtree.com

        Returns:
            List of normalized listings
        """
        from bs4 import BeautifulSoup

        listings = []
        soup = BeautifulSoup(html, "html.parser")

        # Gumtree uses listing links to individual ads
        listing_links = soup.find_all("a", href=re.compile(r"/details/"))

        for link in listing_links:
            try:
                # Extract listing URL
                href = str(link.get("href", ""))
                if not href or "/details/" not in href:
                    continue

                url = href if href.startswith("http") else f"https://www.gumtree.com{href}"

                # Extract listing ID from URL (numeric ID)
                match = re.search(r"/details/(\d+)", str(url))
                if not match:
                    continue

                source_listing_id = match.group(1)

                # Find the parent card element to get title and price
                card = link.find_parent()
                if not card:
                    # Try going up the DOM to find the listing container
                    card = link
                    for _ in range(5):
                        if card.parent:
                            card = card.parent

                # Extract title - often in the link text or nearby heading
                title = ""
                title_elem = link.find(["h2", "h3", "span", "strong"])
                if title_elem:
                    title = title_elem.get_text(strip=True)
                else:
                    # Fallback to link text
                    title = link.get_text(strip=True)

                if not title:
                    continue

                # Extract price - look for price patterns in the card
                price = None
                price_text = None

                # Try to find price in card text
                card_text = card.get_text()
                price_match = re.search(r"£?(\d+\.?\d*)", card_text)
                if price_match:
                    price_text = price_match.group(1)

                # Gumtree often has price in specific elements
                if not price_text:
                    for elem in card.find_all(
                        ["span", "div"], class_=re.compile(r"price|ad-price", re.I)
                    ):
                        elem_text = elem.get_text(strip=True)
                        price_match = re.search(r"£?(\d+\.?\d*)", elem_text)
                        if price_match:
                            price_text = price_match.group(1)
                            break

                if price_text:
                    try:
                        price = Decimal(price_text)
                    except (ValueError, TypeError):
                        pass

                # Extract condition from card text
                condition = Condition.USED_FAIR
                card_text_lower = card.get_text().lower()
                if any(word in card_text_lower for word in ["new", "brand new"]):
                    condition = Condition.NEW
                elif any(word in card_text_lower for word in ["like new", "excellent"]):
                    condition = Condition.USED_LIKE_NEW
                elif any(word in card_text_lower for word in ["good"]):
                    condition = Condition.USED_GOOD

                # Extract seller/location
                seller = None
                location = None

                # Try to find seller info
                seller_elem = card.find(
                    ["span", "div"], class_=re.compile(r"seller|user|advertiser", re.I)
                )
                if seller_elem:
                    seller = seller_elem.get_text(strip=True)

                # Try to find location info
                location_elem = card.find(
                    ["span", "div"], class_=re.compile(r"location|area|city", re.I)
                )
                if location_elem:
                    location = location_elem.get_text(strip=True)

                # Extract image
                image_url = None
                img_elem = card.find("img")
                if img_elem and img_elem.get("src"):
                    image_url = str(img_elem["src"])
                    if image_url.startswith("//"):
                        image_url = f"https:{image_url}"
                    elif image_url.startswith("/"):
                        image_url = f"https://www.gumtree.com{image_url}"

                # Create normalized listing
                listing = NormalizedListing(
                    source=self.connector_id,
                    source_type=self.source_role,
                    source_listing_id=source_listing_id,
                    title_raw=title,
                    price=price,
                    currency="GBP",
                    url=url,
                    in_stock=True,  # Classified listings are generally available
                    image_url=image_url,
                    condition=condition,
                    condition_raw=condition.value.replace("_", " ").title(),
                    seller_or_store=seller,
                    location=location,
                    # Optional fields with None defaults
                    product_normalized=None,
                    variant_normalized=None,
                    shipping_cost=None,
                    total_landed_cost=None,
                    seller_feedback_score=None,
                    seller_feedback_pct=None,
                    stock_state=None,
                    exact_variant_confirmed=None,
                    variant_match_confidence=None,
                    mismatch_flags=None,
                    risk_flags=None,
                    category=None,
                )

                listings.append(listing)

            except Exception as e:
                logger.warning(f"Failed to parse Gumtree listing card: {e}")
                continue

        # Deduplicate by source_listing_id
        seen_ids = set()
        unique_listings = []
        for listing in listings:
            if listing.source_listing_id not in seen_ids:
                seen_ids.add(listing.source_listing_id)
                unique_listings.append(listing)

        return unique_listings
