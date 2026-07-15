"""Google Shopping connector using browser-based scraping of search results."""

import logging
from decimal import Decimal
from typing import Any, Optional

from pricerecon.connectors.base import BaseConnector
from pricerecon.connectors.browser_client import (
    BrowserClient,
    BrowserSessionConfig,
    browser_context,
)
from pricerecon.models import NormalizedListing, SourceType

logger = logging.getLogger(__name__)


class GoogleShoppingConnector(BaseConnector):
    """Google Shopping connector using browser-based scraping.

    Google Shopping aggregates listings from multiple retailers in one query.
    This connector scrapes the public shopping.google.com search results page.
    """

    CONNECTOR_ID = "google_shopping"
    display_name = "Google Shopping"

    SEARCH_URL = "https://shopping.google.com"

    def __init__(self, config: Optional[dict[str, Any]] = None):
        """Initialize the Google Shopping connector.

        Args:
            config: Optional config with BrowserSessionConfig fields
                    (e.g., camofox_url, use_flare_solverr)
        """
        self.config = config or {}
        self.browser_client: Optional[BrowserClient] = None

    @property
    def source_role(self) -> SourceType:
        """Google Shopping is a marketplace aggregator."""
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
        """Search Google Shopping for matching listings.

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
            url_with_params = f"{self.SEARCH_URL}/search?q={query}&tbm=shop"

            # Fetch page with browser
            async with browser_context() as context:
                page = await context.new_page()
                await page.goto(url_with_params)
                html = await page.content()

            if not html:
                logger.error("Failed to fetch Google Shopping HTML")
                return []

            listings = self._parse_search_results(html)
            logger.info(f"Google Shopping found {len(listings)} listings for '{query}'")

            return listings

        except Exception as e:
            logger.error(f"Google Shopping search failed: {e}")
            return []

    def _parse_search_results(self, html: str) -> list[NormalizedListing]:
        """Parse Google Shopping search results HTML.

        Args:
            html: HTML response from shopping.google.com

        Returns:
            List of normalized listings
        """
        from bs4 import BeautifulSoup

        listings = []
        soup = BeautifulSoup(html, "html.parser")

        # Google Shopping product cards have specific structure
        # Look for divs with product content from both card types
        product_cards = soup.find_all("div", class_="sh-dgr__content")
        grid_cards = soup.find_all("div", class_="sh-dgr__grid-result")

        # Combine both card types, removing duplicates
        seen_cards = set()
        all_cards = []
        for card in product_cards + grid_cards:
            card_id = id(card)
            if card_id not in seen_cards:
                seen_cards.add(card_id)
                all_cards.append(card)

        for card in all_cards:
            try:
                # Extract product title - try h3 first
                title = ""
                title_elem = card.find("h3")
                if title_elem:
                    title = title_elem.get_text(strip=True)

                # If no h3, skip this card (require explicit title)
                if not title:
                    continue

                # Extract product URL
                url = ""
                link_elem = card.find("a", href=True)
                if link_elem:
                    url = str(link_elem["href"])
                    if url.startswith("/"):
                        url = f"{self.SEARCH_URL}{url}"

                # Extract price - look for price patterns
                price = None
                for elem in card.find_all(["span", "div"]):
                    text = elem.get_text(strip=True)
                    # Look for currency patterns (e.g., £599.99, $999.99)
                    import re

                    if re.match(r"^[£$€]?\s?\d+[.,]\d{2}$", text):
                        price_text = (
                            text.replace("£", "").replace("$", "").replace("€", "").replace(",", "")
                        )
                        try:
                            price = Decimal(price_text)
                            break
                        except ValueError:
                            continue

                # Extract seller/retailer info - check class attributes first
                retailer = "Google Shopping"
                for elem in card.find_all(["div", "span"]):
                    elem_class = elem.get("class", [])
                    elem_class_str = " ".join(elem_class).lower()
                    if "seller" in elem_class_str or "store" in elem_class_str:
                        retailer = elem.get_text(strip=True)
                        break

                # Fallback: look for text markers
                if retailer == "Google Shopping":
                    for elem in card.find_all(["div", "span"]):
                        text = elem.get_text(strip=True).lower()
                        if "sold by" in text:
                            retailer = elem.get_text(strip=True)
                            # Clean up seller name: remove "Sold by:", "sold by", etc.
                            retailer = (
                                retailer.replace("Sold by:", "").replace("sold by", "").strip()
                            )
                            break

                # Extract availability
                in_stock = True
                for elem in card.find_all(["div", "span"]):
                    text = elem.get_text(strip=True).lower()
                    if "out of stock" in text or "unavailable" in text:
                        in_stock = False
                        break

                # Extract image
                image_url = None
                img_elem = card.find("img")
                if img_elem and img_elem.get("src"):
                    image_url = str(img_elem["src"])

                # Generate stable ID from URL
                source_listing_id = str(hash(url)) if url else ""

                # Create normalized listing
                listing = NormalizedListing(
                    source=self.connector_id,
                    source_type=self.source_role,
                    source_listing_id=source_listing_id,
                    title_raw=title,
                    price=price,
                    currency="GBP",
                    url=url,
                    seller_or_store=retailer,
                    in_stock=in_stock,
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
                logger.warning(f"Failed to parse Google Shopping product card: {e}")
                continue

        return listings
