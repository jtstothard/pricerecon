"""EE Gaming connector using browser-based scraping of Next.js SPA."""

import logging
from decimal import Decimal
from typing import Any, Optional

from pricerecon.connectors.base import BaseConnector
from pricerecon.connectors.browser_client import BrowserClient, BrowserSessionConfig, browser_context
from pricerecon.models import NormalizedListing, SourceType

logger = logging.getLogger(__name__)


class EEGamingConnector(BaseConnector):
    """EE Gaming connector using browser-based scraping.

    EE Gaming is a UK mobile network operator's gaming/hardware store.
    Their site is a Next.js SPA selling gaming consoles, PCs, and accessories.
    """

    CONNECTOR_ID = "ee_gaming"
    display_name = "EE Gaming"

    SEARCH_URL = "https://ee.co.uk"
    GAMING_PATH = "/gaming"

    def __init__(self, config: Optional[dict[str, Any]] = None):
        """Initialize the EE Gaming connector.

        Args:
            config: Optional config with BrowserSessionConfig fields
                    (e.g., camofox_url, use_flare_solverr)
        """
        self.config = config or {}

    @property
    def source_role(self) -> SourceType:
        """EE Gaming is a retailer."""
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
        """Search EE Gaming for matching listings.

        Args:
            query: Search query string
            filters: Optional filters (price_max, condition, etc.)

        Returns:
            List of normalized listings
        """
        filters = filters or {}

        try:
            # Navigate to gaming section and perform search
            search_url = f"{self.SEARCH_URL}{self.GAMING_PATH}"

            # Fetch page with browser
            async with browser_context() as context:
                page = await context.new_page()
                await page.goto(search_url, timeout=30000)

                # Wait for page to render (Next.js SPA)
                await page.wait_for_load_state("networkidle", timeout=10000)

                # Try to interact with search functionality
                # First, try to find and click search button
                try:
                    search_button = page.locator("button:has-text('Search')").first
                    await search_button.click(timeout=5000)
                    await page.wait_for_timeout(1000)

                    # Type query into search input
                    search_input = page.locator("input[type='search'], input[placeholder*='search'], input[placeholder*='Search']").first
                    await search_input.fill(query)
                    await page.wait_for_timeout(1000)
                    await search_input.press("Enter")
                    await page.wait_for_load_state("networkidle", timeout=10000)
                except Exception:
                    # Search button interaction failed, proceed with gaming page content
                    pass

                html = await page.content()

            if not html:
                logger.error("Failed to fetch EE Gaming HTML")
                return []

            listings = self._parse_search_results(html)
            logger.info(f"EE Gaming found {len(listings)} listings for '{query}'")

            return listings

        except Exception as e:
            logger.error(f"EE Gaming search failed: {e}")
            return []

    def _parse_search_results(self, html: str) -> list[NormalizedListing]:
        """Parse EE Gaming search results HTML.

        Args:
            html: HTML response from ee.co.uk/gaming

        Returns:
            List of normalized listings
        """
        from bs4 import BeautifulSoup
        import re

        listings = []
        soup = BeautifulSoup(html, "html.parser")

        # EE Gaming product cards have link elements with product info
        # Look for product links with prices
        product_cards = soup.find_all("a", href=True)

        for card in product_cards:
            try:
                url = str(card["href"])
                if not url.startswith("http"):
                    url = f"{self.SEARCH_URL}{url}"

                # Skip non-product links (look for product URLs)
                if not re.search(r"/products/", url):
                    continue

                # Extract title - usually in heading
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
                for elem in card.find_all(["span", "div", "strong", "p"]):
                    text = elem.get_text(strip=True)
                    # Look for GBP currency patterns (e.g., £59.99, £34.00)
                    if re.match(r'^[£]?\s?\d+\.\d{2}$', text):
                        price_text = text.replace("£", "").replace(",", "").strip()
                        try:
                            price = Decimal(price_text)
                            break
                        except:
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
                    seller_or_store="EE Gaming",
                    in_stock=True,  # EE doesn't show out-of-stock on search cards
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
                logger.warning(f"Failed to parse EE Gaming product card: {e}")
                continue

        return listings