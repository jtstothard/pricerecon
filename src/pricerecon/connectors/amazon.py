"""Amazon UK connector using curl_cffi for TLS fingerprint impersonation."""

import logging
import re
from decimal import Decimal
from typing import Any, Optional

from pricerecon.connectors.base import BaseConnector
from pricerecon.models import Condition, NormalizedListing, SourceType

logger = logging.getLogger(__name__)

try:
    from curl_cffi import requests
except ImportError:
    requests = None
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
            raise ImportError(
                "curl_cffi is required. Install with: pip install curl_cffi"
            )
        
        self.config = config or {}
        self.impersonate = self.config.get("impersonate", "chrome124")
        self.session = requests.Session(impersonate=self.impersonate)
    
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
            return []
        
        # Parse search results
        listings = self._parse_search_results(response.text, query, filters)
        logger.info(f"Amazon search found {len(listings)} listings")
        
        return listings
    
    def _parse_search_results(
        self, html: str, query: str, filters: dict[str, Any]
    ) -> list[NormalizedListing]:
        """Parse Amazon search results HTML.
        
        Args:
            html: HTML response
            query: Original query
            filters: Search filters
        
        Returns:
            List of normalized listings
        """
        listings = []
        
        # Extract search result blocks
        # Each block has ASIN and price information
        # ASINs can be in URL pattern or data-asin attribute
        asin_pattern = r'/dp/([A-Z0-9]{10})'
        data_asin_pattern = r'data-asin="([A-Z0-9]{10})"'
        price_pattern = r'<span class="a-offscreen">([^<]+)</span>'
        
        # Find all product blocks - check both patterns
        url_asins = re.findall(asin_pattern, html)
        data_asins = re.findall(data_asin_pattern, html)
        asins = list(set(url_asins + data_asins))  # Deduplicate
        
        price_matches = re.finditer(price_pattern, html)
        prices = [match.group(1) for match in price_matches]
        
        # Match ASINs with prices
        # This is a simple approach; in reality, prices are nested within product blocks
        # For now, we'll create basic listings from what we can extract
        
        seen_asins = set()
        for i, asin in enumerate(asins):
            if asin in seen_asins:
                continue
            seen_asins.add(asin)
            
            # Get price if available
            price = Decimal("0.00")
            if i < len(prices):
                try:
                    price_str = prices[i].replace("£", "").replace(",", "").strip()
                    price = Decimal(price_str)
                except (ValueError, IndexError):
                    pass
            
            # Determine condition from filters or default to new
            condition = Condition.NEW
            if filters.get("condition") == "refurbished":
                condition = Condition.REFURBISHED
            
            # Create normalized listing with keyword-only args
            listing = NormalizedListing.model_validate({
                "source": self.CONNECTOR_ID,
                "source_type": self.source_role,
                "source_listing_id": asin,
                "title_raw": query,  # Full title requires fetching product page
                "price": price,
                "currency": "GBP",
                "url": f"{self.BASE_URL}/dp/{asin}",
                "condition": condition,
                "in_stock": price > Decimal("0.00"),
            })
            
            listings.append(listing)
        return listings
    
    async def get_product_page(
        self, asin: str
    ) -> dict[str, Any]:
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
            return {}
        
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