"""GAME Digital connector using browser-based scraping."""

import logging
from decimal import Decimal
from typing import Any, Optional

from pricerecon.connectors.base import BaseConnector
from pricerecon.connectors.browser_client import (
    browser_context,
)
from pricerecon.models import NormalizedListing, SourceType

logger = logging.getLogger(__name__)


class GameDigitalConnector(BaseConnector):
    """GAME Digital connector using browser-based scraping.

    GAME is a dedicated UK gaming retailer (consoles, games, accessories).
    Their site is an SPA but renders product cards that can be scraped.
    """

    CONNECTOR_ID = "game_digital"
    display_name = "GAME Digital"

    SEARCH_URL = "https://www.game.co.uk"

    def __init__(self, config: Optional[dict[str, Any]] = None):
        """Initialize the GAME Digital connector.

        Args:
            config: Optional config with BrowserSessionConfig fields
                    (e.g., camofox_url, use_flare_solverr)
        """
        self.config = config or {}

    @property
    def source_role(self) -> SourceType:
        """GAME Digital is a retailer."""
        return SourceType.RETAILER

    async def initialize(self) -> None:
        """Initialize connector (no-op for this connector)."""
        pass

    async def cleanup(self) -> None:
        """Cleanup resources (no-op for this connector)."""
        pass

    async def search(
        self, query: str, filters: Optional[dict[str, Any]] = None
    ) -> list[NormalizedListing]:
        """Search GAME Digital for matching listings.

        Args:
            query: Search query string
            filters: Optional filters (price_max, condition, etc.)

        Returns:
            List of normalized listings
        """
        filters = filters or {}

        try:
            # Navigate to search results page
            search_url = f"{self.SEARCH_URL}/search?q={query}"

            # Fetch page with browser
            async with browser_context() as context:
                page = await context.new_page()
                await page.goto(search_url, timeout=30000)
                html = await page.content()

            if not html:
                logger.error("Failed to fetch GAME Digital HTML")
                return []

            listings = self._parse_search_results(html)
            logger.info(f"GAME Digital found {len(listings)} listings for '{query}'")

            return listings

        except Exception as e:
            logger.error(f"GAME Digital search failed: {e}")
            return []

    def _parse_search_results(self, html: str) -> list[NormalizedListing]:
        """Parse GAME Digital search results HTML.

        Args:
            html: HTML response from game.co.uk

        Returns:
            List of normalized listings
        """
        from bs4 import BeautifulSoup
        import re

        listings = []
        soup = BeautifulSoup(html, "html.parser")

        # GAME Digital product cards typically have specific structures
        # Look for product cards with links and prices
        product_cards = soup.find_all("a", href=True)

        for card in product_cards:
            try:
                url = str(card["href"])
                if url.startswith("/"):
                    url = f"{self.SEARCH_URL}{url}"

                # Skip non-product links
                if not re.search(r"/(games|tech|pc-gaming|consoles|accessories)/", url):
                    continue

                # Extract title - usually in heading or product name element
                title = ""
                title_elem = card.find(["h1", "h2", "h3", "h4"])
                if title_elem:
                    title = title_elem.get_text(strip=True)
                else:
                    # Fallback to link text
                    title = card.get_text(strip=True)

                if not title or len(title) < 5:
                    continue

                # Extract price - look for currency patterns
                price = None
                for elem in card.find_all(["span", "div", "strong"]):
                    text = elem.get_text(strip=True)
                    # Look for GBP currency patterns (e.g., £59.99)
                    if re.match(r"^[£]?\s?\d+\.\d{2}$", text):
                        price_text = text.replace("£", "").replace(",", "").strip()
                        try:
                            price = Decimal(price_text)
                            break
                        except ValueError:
                            continue

                # Extract image
                image_url = None
                img_elem = card.find("img")
                if img_elem and img_elem.get("src"):
                    image_url = str(img_elem["src"])

                # Generate stable ID from URL
                source_listing_id = str(hash(url))

                # Create normalized listing
                listing = NormalizedListing(
                    source=self.connector_id,
                    source_type=self.source_role,
                    source_listing_id=source_listing_id,
                    title_raw=title,
                    price=price,
                    currency="GBP",
                    url=url,
                    seller_or_store="GAME Digital",
                    in_stock=True,  # GAME doesn't show out-of-stock on search cards
                    image_url=image_url,
                    # Optional fields with None defaults
                    product_normalized=None,
                    variant_normalized=None,
                    condition=None,
                    condition_raw=None,
                    shipping_cost=None,
                    total_landed_cost=None,
                    seller_feedback_score=None,
                    seller_feedback_pct=None,
                    location=None,
                    stock_state=None,
                    exact_variant_confirmed=None,
                    variant_match_confidence=None,
                    mismatch_flags=None,
                    risk_flags=None,
                    category=None,
                )

                listings.append(listing)

            except Exception as e:
                logger.warning(f"Failed to parse GAME Digital product card: {e}")
                continue

        return listings
