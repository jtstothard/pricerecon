"""Argos connector using browser-assisted HTML parsing."""

import logging
import re
from decimal import Decimal
from typing import Any, Optional

from pricerecon.connectors.base import BaseConnector
from pricerecon.connectors.browser_client import (
    BrowserClient,
    BrowserSessionConfig,
)
from pricerecon.models import NormalizedListing, SourceType

logger = logging.getLogger(__name__)


class ArgosConnector(BaseConnector):
    """Argos connector for UK tech retailer search results.

    Argos is a major UK retailer with public search pages.
    This connector uses browser-assisted HTML parsing to extract product data.
    """

    CONNECTOR_ID = "argos"
    display_name = "Argos"

    SEARCH_URL = "https://www.argos.co.uk/search"

    def __init__(self, config: Optional[dict[str, Any]] = None):
        """Initialize the Argos connector.

        Args:
            config: Optional config with BrowserSessionConfig fields
                    (e.g., camofox_url, use_flare_solverr)
        """
        self.config = config or {}
        self.browser_client: Optional[BrowserClient] = None

    @property
    def source_role(self) -> SourceType:
        """Argos is a retailer."""
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
        """Search Argos for matching listings.

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
            url_with_params = f"{self.SEARCH_URL}/{query}"

            # Fetch page with the configured browser backend. Camofox returns
            # an accessibility snapshot from page.content().
            context = await self.browser_client.new_context()
            try:
                page = await context.new_page()
                await page.goto(url_with_params)
                html = await page.content()
            finally:
                await context.close()

            if not html:
                logger.error("Failed to fetch Argos HTML")
                return []

            listings = self._parse_search_results(html)
            logger.info(f"Argos found {len(listings)} listings for '{query}'")

            return listings

        except Exception as e:
            logger.error(f"Argos search failed: {e}")
            return []

    def _parse_search_results(self, html: str) -> list[NormalizedListing]:
        """Parse Argos search results HTML.

        Args:
            html: HTML response from argos.co.uk

        Returns:
            List of normalized listings
        """
        from bs4 import BeautifulSoup

        # Camofox exposes an accessibility snapshot rather than DOM HTML.
        if "- main:" in html and "/url:" in html:
            snapshot_listings: list[dict[str, str | None]] = []
            current: dict[str, str | None] | None = None
            for line in html.splitlines():
                link_match = re.search(r'link \\\"(.+?)\\\"', line)
                if link_match:
                    if current:
                        snapshot_listings.append(current)
                    current = {"url": None, "title": link_match.group(1), "price": None}
                elif current and "/url:" in line:
                    url_match = re.search(r"/url:\s*(.+)$", line)
                    if url_match:
                        current["url"] = url_match.group(1).strip().strip('\\"')
                elif current:
                    price_match = re.search(r"£(\d+[,.]\d{2})", line)
                    if price_match:
                        current["price"] = price_match.group(1).replace(",", "")
            if current:
                snapshot_listings.append(current)
            return [
                NormalizedListing(
                    source=self.connector_id,
                    source_type=self.source_role,
                    source_listing_id=str(re.search(r"/product/(\d+)", str(item["url"])).group(1)),
                    title_raw=str(item["title"]),
                    price=Decimal(str(item["price"])) if item["price"] else None,
                    currency="GBP",
                    url=f"https://www.argos.co.uk{item['url']}",
                    in_stock=True,
                    image_url=None,
                    product_normalized=None,
                    variant_normalized=None,
                    condition=None,
                    condition_raw=None,
                    shipping_cost=None,
                    total_landed_cost=None,
                    seller_or_store="Argos",
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
                for item in snapshot_listings
                if item["title"] and item["url"] and re.search(r"/product/(\d+)", str(item["url"]))
            ]

        listings = []
        soup = BeautifulSoup(html, "html.parser")

        # Argos product cards - look for product links in search results
        # The structure includes product links with specific data attributes
        product_links = soup.find_all("a", href=re.compile(r"/product/\d+"))

        for link in product_links:
            try:
                # Extract product URL
                href = str(link.get("href", ""))
                if not href or "/product/" not in href:
                    continue

                url = href if href.startswith("http") else f"https://www.argos.co.uk{href}"

                # Extract product ID from URL
                match = re.search(r"/product/(\d+)", str(url))
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
                title_elem = link.find(["h3", "h4", "strong"])
                if title_elem:
                    title = title_elem.get_text(strip=True)
                else:
                    # Fallback to link text
                    title = link.get_text(strip=True)

                # If still no title, look for heading in the card
                if not title:
                    title_elem = card.find(["h3", "h4", "h2"])
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
                if not price_text:
                    for elem in card.find_all(["span", "div", "p"]):
                        elem_text = elem.get_text(strip=True)
                        if re.match(r"^£\d+\.\d{2}$", elem_text):
                            price_text = elem_text.replace("£", "")
                            break

                if price_text:
                    try:
                        price = Decimal(price_text)
                    except (ValueError, TypeError):
                        pass

                # Extract stock availability
                in_stock = True
                card_text_lower = card.get_text().lower()
                if "out of stock" in card_text_lower or "unavailable" in card_text_lower:
                    in_stock = False

                # Extract image
                image_url = None
                img_elem = card.find("img")
                if img_elem and img_elem.get("src"):
                    image_url = str(img_elem["src"])
                    if image_url.startswith("//"):
                        image_url = f"https:{image_url}"

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
                    # Optional fields with None defaults
                    product_normalized=None,
                    variant_normalized=None,
                    condition=None,
                    condition_raw=None,
                    shipping_cost=None,
                    total_landed_cost=None,
                    seller_or_store="Argos",
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
                logger.warning(f"Failed to parse Argos product card: {e}")
                continue

        # Deduplicate by source_listing_id
        seen_ids = set()
        unique_listings = []
        for listing in listings:
            if listing.source_listing_id not in seen_ids:
                seen_ids.add(listing.source_listing_id)
                unique_listings.append(listing)

        return unique_listings
