"""MusicMagpie connector using browser-assisted HTML parsing."""

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
from pricerecon.models import NormalizedListing, SourceType

logger = logging.getLogger(__name__)


class MusicMagpieConnector(BaseConnector):
    """MusicMagpie connector for refurbished tech search results.

    MusicMagpie sells refurbished electronics (phones, laptops, tablets, etc.).
    This connector uses browser-assisted HTML parsing to extract product data.
    """

    CONNECTOR_ID = "musicmagpie"
    display_name = "MusicMagpie"

    SEARCH_URL = "https://www.musicmagpie.co.uk/store/search"

    def __init__(self, config: Optional[dict[str, Any]] = None):
        """Initialize the MusicMagpie connector.

        Args:
            config: Optional config with BrowserSessionConfig fields
                    (e.g., camofox_url, use_flare_solverr)
        """
        self.config = config or {}
        self.browser_client: Optional[BrowserClient] = None

    @property
    def source_role(self) -> SourceType:
        """MusicMagpie is a retailer (refurbished goods)."""
        return SourceType.RETAILER

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
        """Search MusicMagpie for matching listings.

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
            url_with_params = f"{self.SEARCH_URL}?q={query}"

            # Fetch page with browser
            async with browser_context() as context:
                page = await context.new_page()
                await page.goto(url_with_params)
                html = await page.content()

            if not html:
                logger.error("Failed to fetch MusicMagpie HTML")
                return []

            listings = self._parse_search_results(html)
            logger.info(f"MusicMagpie found {len(listings)} listings for '{query}'")

            return listings

        except Exception as e:
            logger.error(f"MusicMagpie search failed: {e}")
            return []

    def _parse_search_results(self, html: str) -> list[NormalizedListing]:
        """Parse MusicMagpie search results HTML.

        Args:
            html: HTML response from musicmagpie.co.uk

        Returns:
            List of normalized listings
        """
        from bs4 import BeautifulSoup

        listings = []
        soup = BeautifulSoup(html, "html.parser")

        # MusicMagpie product cards - look for product links
        # The structure includes product cards with links to individual products
        product_links = soup.find_all("a", href=re.compile(r"/store/product/\w+"))

        for link in product_links:
            try:
                # Extract product URL
                href = str(link.get("href", ""))
                if not href or "/store/product/" not in href:
                    continue

                url = href if href.startswith("http") else f"https://www.musicmagpie.co.uk{href}"

                # Extract product ID from URL (alphanumeric slug, may include hyphens)
                match = re.search(r"/store/product/([^/]+)", str(url))
                if not match:
                    continue

                source_listing_id = match.group(1)

                # Find the parent card element to get title and price
                card = link.find_parent()
                if not card:
                    # Try going up the DOM to find the product container
                    card = link
                    for _ in range(5):  # Try up to 5 levels up
                        if card.parent:
                            card = card.parent

                # Extract title - often in the link text or nearby heading
                title = ""
                title_elem = link.find(["h3", "h4", "h2", "strong"])
                if title_elem:
                    title = title_elem.get_text(strip=True)
                else:
                    # Fallback to link text
                    title = link.get_text(strip=True)

                # If still no title, look for heading in the card
                if not title:
                    title_elem = card.find(["h3", "h4", "h2", "h5"])
                    if title_elem:
                        title = title_elem.get_text(strip=True)

                if not title:
                    continue

                # Extract price - look for price patterns in the card
                price = None
                price_text = None

                # Try to find price in card text
                card_text = card.get_text()
                price_match = re.search(r"£(\d+\.\d{2})", card_text)
                if price_match:
                    price_text = price_match.group(1)

                # Alternatively, look for specific price elements
                # MusicMagpie often has price in a class like "price" or "product-price"
                if not price_text:
                    for elem in card.find_all(
                        ["span", "div", "p"], class_=re.compile(r"price", re.I)
                    ):
                        elem_text = elem.get_text(strip=True)
                        price_match = re.search(r"£?(\d+\.\d{2})", elem_text)
                        if price_match:
                            price_text = price_match.group(1)
                            break

                if price_text:
                    try:
                        price = Decimal(price_text)
                    except (ValueError, TypeError):
                        pass

                # Extract stock availability
                in_stock = True
                card_text_lower = card.get_text().lower()
                if (
                    "out of stock" in card_text_lower
                    or "unavailable" in card_text_lower
                    or "sold out" in card_text_lower
                ):
                    in_stock = False

                # Extract image
                image_url = None
                img_elem = card.find("img")
                if img_elem and img_elem.get("src"):
                    image_url = str(img_elem["src"])
                    if image_url.startswith("//"):
                        image_url = f"https:{image_url}"
                    elif image_url.startswith("/"):
                        image_url = f"https://www.musicmagpie.co.uk{image_url}"

                # Create normalized listing
                listing = NormalizedListing(
                    source=self.connector_id,
                    source_type=self.source_role,
                    source_listing_id=source_listing_id,
                    title_raw=title,
                    price=price,
                    currency="GBP",
                    url=url,
                    in_stock=in_stock,
                    image_url=image_url,
                    condition="refurbished",  # MusicMagpie only sells refurbished
                    condition_raw="Refurbished",
                    seller_or_store="MusicMagpie",
                    # Optional fields with None defaults
                    product_normalized=None,
                    variant_normalized=None,
                    shipping_cost=Decimal("0"),  # Free delivery on all orders
                    total_landed_cost=None,
                    seller_feedback_score=None,
                    seller_feedback_pct=None,
                    location="UK",
                    stock_state=None,
                    exact_variant_confirmed=None,
                    variant_match_confidence=None,
                    mismatch_flags=None,
                    risk_flags=None,
                    category=None,
                )

                listings.append(listing)

            except Exception as e:
                logger.warning(f"Failed to parse MusicMagpie product card: {e}")
                continue

        # Deduplicate by source_listing_id
        seen_ids = set()
        unique_listings = []
        for listing in listings:
            if listing.source_listing_id not in seen_ids:
                seen_ids.add(listing.source_listing_id)
                unique_listings.append(listing)

        return unique_listings
