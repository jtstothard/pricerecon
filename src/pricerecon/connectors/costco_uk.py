"""Costco UK connector using session-based authentication."""

import logging
import os
import re
from decimal import Decimal
from typing import Any, Optional

from pricerecon.connectors.base import BaseConnector
from pricerecon.connectors.browser_client import BrowserClient, BrowserSessionConfig, browser_context
from pricerecon.connectors.status import ConnectorDegradedError, ConnectorStatus
from pricerecon.models import NormalizedListing, SourceType

logger = logging.getLogger(__name__)


class CostcoUKConnector(BaseConnector):
    """Costco UK connector for member-only retailer search results.

    Costco UK requires a valid membership session to access product pages and pricing.
    This connector uses session cookies loaded from environment variables and
    browser-assisted HTML parsing to extract product data.
    """

    CONNECTOR_ID = "costco_uk"
    display_name = "Costco UK"

    SEARCH_URL = "https://www.costco.co.uk/search"
    CATEGORY_URL = "https://www.costco.co.uk/Computers/Laptops-MacBooks/c/cos_16.1"

    def __init__(self, config: Optional[dict[str, Any]] = None):
        """Initialize the Costco UK connector.

        Args:
            config: Optional config with BrowserSessionConfig fields
                    and session cookies
        """
        self.config = config or {}
        self.browser_client: Optional[BrowserClient] = None

        # Load session cookie from environment variable
        self.session_cookie = os.getenv("COSTCO_SESSION_COOKIE")

        # Check if auth is configured
        self.auth_configured = bool(self.session_cookie)

        if not self.auth_configured:
            logger.warning(
                "COSTCO_SESSION_COOKIE not set - Costco UK connector requires authentication. "
                "Set the environment variable with your Costco session cookie to enable this connector."
            )

    @property
    def source_role(self) -> SourceType:
        """Costco UK is a retailer."""
        return SourceType.RETAILER

    async def initialize(self) -> None:
        """Initialize browser client with session cookies if configured."""
        if not self.auth_configured:
            # Don't fail initialization, but mark as degraded
            return

        # Parse cookie string (format: "name1=value1; name2=value2")
        cookies = []
        if self.session_cookie:
            for pair in self.session_cookie.split(";"):
                if "=" in pair:
                    name, value = pair.strip().split("=", 1)
                    cookies.append({"name": name, "value": value})

        browser_config = BrowserSessionConfig(**self.config)
        self.browser_client = BrowserClient(config=browser_config)

        # Create context with cookies if available
        if cookies:
            # Note: browser_context will be used in search method
            pass

        await self.browser_client.start()

    async def cleanup(self) -> None:
        """Cleanup browser resources."""
        if self.browser_client:
            await self.browser_client.close()

    async def search(
        self, query: str, filters: Optional[dict[str, Any]] = None
    ) -> list[NormalizedListing]:
        """Search Costco UK for matching listings.

        Args:
            query: Search query string
            filters: Optional filters (price_max, condition, etc.)

        Returns:
            List of normalized listings

        Raises:
            ConnectorDegradedError: If authentication is not configured
        """
        if not self.auth_configured:
            raise ConnectorDegradedError(
                status=ConnectorStatus.auth_failed,
                message="Costco UK connector requires COSTCO_SESSION_COOKIE environment variable to be set",
                connector_id=self.connector_id,
            )

        filters = filters or {}

        if self.browser_client is None:
            await self.initialize()

        assert self.browser_client is not None

        try:
            # Build search URL
            url_with_params = f"{self.SEARCH_URL}?searchOption=uk-search-all&text={query}"

            # Parse cookies for browser context
            cookies = []
            if self.session_cookie:
                for pair in self.session_cookie.split(";"):
                    if "=" in pair:
                        name, value = pair.strip().split("=", 1)
                        cookies.append({"name": name, "value": value})

            # Fetch page with browser
            async with browser_context() as context:
                # Add cookies to context
                for cookie in cookies:
                    await context.add_cookies(cookie)

                page = await context.new_page()
                await page.goto(url_with_params, timeout=30000)
                html = await page.content()

            if not html:
                logger.error("Failed to fetch Costco UK HTML")
                return []

            listings = self._parse_search_results(html)
            logger.info(f"Costco UK found {len(listings)} listings for '{query}'")

            return listings

        except ConnectorDegradedError:
            raise
        except Exception as e:
            logger.error(f"Costco UK search failed: {e}")
            raise ConnectorDegradedError(
                status=ConnectorStatus.unknown_error,
                message=f"Costco UK search failed: {e}",
                connector_id=self.connector_id,
            )

    def _parse_search_results(self, html: str) -> list[NormalizedListing]:
        """Parse Costco UK search results HTML.

        Args:
            html: HTML response from costco.co.uk

        Returns:
            List of normalized listings
        """
        from bs4 import BeautifulSoup

        listings = []
        soup = BeautifulSoup(html, "html.parser")

        # Costco product cards - look for product links in search results
        # Product URLs typically follow pattern /p/{product_id}
        product_links = soup.find_all("a", href=re.compile(r"/p/\d+"))

        for link in product_links:
            try:
                # Extract product URL
                href = str(link.get("href", ""))
                if not href or "/p/" not in href:
                    continue

                url = href if href.startswith("http") else f"https://www.costco.co.uk{href}"

                # Extract product ID from URL
                match = re.search(r"/p/(\d+)", str(url))
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
                title_elem = link.find(["h3", "h4", "strong", "span"])
                if title_elem:
                    title = title_elem.get_text(strip=True)
                else:
                    # Fallback to link text
                    title = link.get_text(strip=True)

                # If still no title, look for heading in the card
                if not title:
                    title_elem = card.find(["h3", "h4", "h2", "h1"])
                    if title_elem:
                        title = title_elem.get_text(strip=True)

                if not title:
                    continue

                # Extract price - look for price patterns in the card
                price = None
                price_text = None

                # Try to find price in card text
                card_text = card.get_text()
                price_match = re.search(r"£([\d,]+\.?\d*)", card_text)
                if price_match:
                    price_text = price_match.group(1).replace(",", "")

                # Alternatively, look for specific price elements
                if not price_text:
                    for elem in card.find_all(["span", "div", "p"]):
                        elem_text = elem.get_text(strip=True)
                        if re.match(r"^£\d+\.?\d*$", elem_text):
                            price_text = elem_text.replace("£", "")
                            break

                if price_text:
                    try:
                        price = Decimal(price_text)
                    except (ValueError, TypeError):
                        pass

                # Extract stock availability - Costco generally shows in-stock items
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
                    schema_version="1.0",
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
                    seller_or_store="Costco UK",
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
                logger.warning(f"Failed to parse Costco UK product card: {e}")
                continue

        # Deduplicate by source_listing_id
        seen_ids = set()
        unique_listings = []
        for listing in listings:
            if listing.source_listing_id not in seen_ids:
                seen_ids.add(listing.source_listing_id)
                unique_listings.append(listing)

        return unique_listings