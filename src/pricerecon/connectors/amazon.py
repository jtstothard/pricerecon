"""Amazon UK connector using curl_cffi for TLS fingerprint impersonation."""

import logging
import re
from decimal import Decimal, InvalidOperation
from typing import Any, Optional

from pricerecon.connectors.base import BaseConnector
from pricerecon.connectors.status import ConnectorDegradedError, ConnectorStatus
from pricerecon.models import Condition, NormalizedListing, SourceType

logger = logging.getLogger(__name__)

try:
    from curl_cffi import requests
except ImportError:
    requests = None  # type: ignore[assignment]
    logger.warning("curl_cffi not installed. Amazon connector will not function.")


class AmazonConnector(BaseConnector):
    """Amazon UK connector using curl_cffi with browser impersonation."""

    CONNECTOR_ID = "amazon_uk"
    BASE_URL = "https://www.amazon.co.uk"

    def __init__(self, config: Optional[dict[str, Any]] = None):
        """Initialize the Amazon connector.

        Args:
            config: Optional config with 'impersonate' (default: 'chrome124')
        """
        if requests is None:
            raise ImportError("curl_cffi is required. Install with: pip install curl_cffi")

        self.config = config or {}
        self.impersonate = self.config.get("impersonate", "chrome124")
        self.session: requests.Session = requests.Session(impersonate=self.impersonate)  # type: ignore[union-attr]

    @property
    def source_role(self) -> SourceType:
        """Amazon is a retailer."""
        return SourceType.RETAILER

    async def initialize(self) -> None:
        """Initialize the connector (optional)."""
        # curl_cffi sessions are ready to use after init
        pass

    async def cleanup(self) -> None:
        """Close the session."""
        if self.session:
            self.session.close()

    async def search(
        self, query: str, filters: Optional[dict[str, Any]] = None
    ) -> list[NormalizedListing]:
        """Search Amazon UK for matching listings.

        Args:
            query: Search query string
            filters: Optional filters (price_max, condition, etc.)

        Returns:
            List of normalized listings
        """
        filters = filters or {}

        # Build search URL
        url = f"{self.BASE_URL}/s"
        params = {"k": query}

        # Add condition filter for refurbished
        condition = filters.get("condition")
        if condition == "refurbished":
            params["rh"] = "p_n_condition-type:1486414031"

        # Make request with curl_cffi
        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
        except Exception as e:
            logger.error(f"Amazon search failed: {e}")
            raise ConnectorDegradedError(
                ConnectorStatus.unknown_error,
                f"Amazon search request failed: {e}",
                self.CONNECTOR_ID,
                {"error": str(e), "error_type": type(e).__name__},
            ) from e

        # Check if we got a captcha/blocked page
        if self._is_blocked_page(response.text):
            logger.warning("Amazon returned a captcha or blocked page")
            raise ConnectorDegradedError(
                ConnectorStatus.bot_blocked,
                "Amazon returned a captcha or blocked page",
                self.CONNECTOR_ID,
                {"status_code": getattr(response, "status_code", None)},
            )

        # Parse search results
        listings = self._parse_search_results(response.text, query, filters)
        logger.info(f"Amazon search found {len(listings)} listings")

        return listings

    def _is_blocked_page(self, html: str) -> bool:
        """Check if the response is a captcha or blocked page.

        Args:
            html: HTML response

        Returns:
            True if blocked, False otherwise
        """
        captcha_indicators = [
            "captcha",
            "Type the characters you see below",
            "security measure",
            "enter the characters you see",
            "Amazon is blocking your request",
            "robot check",
            "Sorry, something went wrong",
            "access denied",
            "temporarily blocked",
            "Please verify you are human",
        ]
        html_lower = html.lower()
        return any(indicator.lower() in html_lower for indicator in captcha_indicators)

    def _parse_search_results(
        self, html: str, query: str, filters: dict[str, Any]
    ) -> list[NormalizedListing]:
        """Parse Amazon search results HTML by extracting product blocks.

        Args:
            html: HTML response
            query: Original query
            filters: Search filters

        Returns:
            List of normalized listings
        """
        listings = []
        seen_asins: set[str] = set()

        # Find all product result blocks using data-component-type="s-search-result"
        # These are top-level result divs; extract the full div block.
        product_block_pattern = r'<div[^>]*data-component-type="s-search-result"[^>]*>(.*?)</div>\s*</div>\s*</div>\s*</div>'
        blocks = re.finditer(product_block_pattern, html, re.DOTALL)

        for block_match in blocks:
            block_html = block_match.group(0)

            listing = self._parse_product_block(block_html, query, filters)
            if listing and listing.source_listing_id not in seen_asins:
                seen_asins.add(listing.source_listing_id)
                listings.append(listing)

        # Fallback: if the structured pattern matched nothing, try the simpler
        # data-asin div pattern that older Amazon markup uses.
        if not listings:
            simple_pattern = r'<div[^>]*data-asin="([A-Z0-9]{10})"[^>]*>(.*?)</div>'
            for m in re.finditer(simple_pattern, html, re.DOTALL):
                asin = m.group(1)
                if asin in seen_asins:
                    continue
                listing = self._parse_product_block(m.group(0), query, filters)
                if listing:
                    seen_asins.add(asin)
                    listings.append(listing)

        return listings

    def _parse_product_block(
        self, block_html: str, query: str, filters: dict[str, Any]
    ) -> Optional[NormalizedListing]:
        """Parse a single product result block.

        Args:
            block_html: HTML for a single product block
            query: Original search query
            filters: Search filters

        Returns:
            NormalizedListing or None if block is invalid
        """
        # Extract ASIN from data-asin attribute
        asin_match = re.search(r'data-asin="([A-Z0-9]{10})"', block_html)
        if not asin_match:
            return None

        asin = asin_match.group(1)

        # Extract title - look for the product link/span
        title_patterns = [
            r'<h2[^>]*class="[^"]*a-size-base-plus[^"]*"[^>]*>\s*<span[^>]*>([^<]+)</span>',
            r'<span class="a-size-base-plus a-color-base a-text-normal">\s*([^<]+)\s*</span>',
            r"<h2[^>]*>\s*<span[^>]*>([^<]+)</span>",
        ]

        title = None
        for pattern in title_patterns:
            match = re.search(pattern, block_html)
            if match:
                title = match.group(1).strip()
                break

        if not title:
            # No valid title found - this is not a real product
            return None

        # Check if this might be a sponsored/ad item
        # Sponsored items have different structure and often lack reliable pricing
        is_sponsored = "Sponsored" in block_html or "sponsored" in block_html.lower()
        if is_sponsored:
            logger.debug(f"Skipping sponsored item: {asin}")
            return None

        # Extract price from a-offscreen span
        price_match = re.search(r'<span class="a-offscreen">([^<]+)</span>', block_html)
        if not price_match:
            # No price found — this is not a real purchasable product
            return None

        try:
            price_str = price_match.group(1).replace("£", "").replace(",", "").strip()
            # Handle cases like "Was: £100 £79.99" - take the last price
            price_parts = price_str.split()
            if price_parts:
                price_str = price_parts[-1]
            price = Decimal(price_str)
        except (ValueError, IndexError, InvalidOperation):
            return None

        # Reject zero-priced listings — they are not real purchasable products
        if price <= Decimal("0.00"):
            return None

        # Determine condition from filters or default to new
        condition = Condition.NEW
        if filters.get("condition") == "refurbished":
            condition = Condition.REFURBISHED

        # Determine stock status
        in_stock = True

        # Create normalized listing
        try:
            listing = NormalizedListing.model_validate(
                {
                    "source": self.CONNECTOR_ID,
                    "source_type": self.source_role,
                    "source_listing_id": asin,
                    "title_raw": title,
                    "price": price,
                    "currency": "GBP",
                    "url": f"{self.BASE_URL}/dp/{asin}",
                    "condition": condition,
                    "in_stock": in_stock,
                }
            )
            return listing
        except Exception as e:
            logger.warning(f"Failed to create listing for ASIN {asin}: {e}")
            return None

    async def get_product_page(self, asin: str) -> dict[str, Any]:
        """Fetch and parse Amazon product page.

        Args:
            asin: Amazon ASIN

        Returns:
            Dict with product details (title, price, stock, variants)
        """
        url = f"{self.BASE_URL}/dp/{asin}"

        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
        except Exception as e:
            logger.error(f"Failed to fetch product page for {asin}: {e}")
            raise ConnectorDegradedError(
                ConnectorStatus.unknown_error,
                f"Amazon product page request failed: {e}",
                self.CONNECTOR_ID,
                {"asin": asin, "error": str(e)},
            ) from e

        # Check if blocked
        if self._is_blocked_page(response.text):
            logger.warning(f"Blocked when fetching product page for {asin}")
            raise ConnectorDegradedError(
                ConnectorStatus.bot_blocked,
                f"Amazon blocked product page for {asin}",
                self.CONNECTOR_ID,
                {"asin": asin},
            )

        return self._parse_product_page(response.text)

    def _parse_product_page(self, html: str) -> dict[str, Any]:
        """Parse Amazon product page HTML.

        Args:
            html: HTML response

        Returns:
            Dict with product details
        """
        details = {}

        # Extract title
        title_match = re.search(r'<span id="productTitle"[^>]*>([^<]+)</span>', html)
        if title_match:
            details["title"] = title_match.group(1).strip()

        # Extract price from a-offscreen span
        price_match = re.search(r'<span class="a-offscreen">([^<]+)</span>', html)
        if price_match:
            price_str = price_match.group(1).replace("£", "").replace(",", "").strip()
            try:
                details["price"] = Decimal(price_str)
            except ValueError:
                pass

        # Extract stock status
        availability_pattern = r'<span id="availability"[^>]*>.*?<span>([^<]+)</span>'
        availability_match = re.search(availability_pattern, html, re.DOTALL)
        if availability_match:
            availability = availability_match.group(1).strip().lower()
            details["in_stock"] = "in stock" in availability

        # Extract image URL
        image_match = re.search(r'<img[^>]*id="landingImage"[^>]*src="([^"]+)"', html)
        if image_match:
            details["image_url"] = image_match.group(1)

        # Extract variant info (size, color, etc.)
        # This is more complex and may require parsing dropdowns
        details["variants"] = []

        return details
