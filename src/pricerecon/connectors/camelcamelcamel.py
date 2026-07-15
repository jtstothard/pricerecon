"""CamelCamelCamel connector for Amazon price history tracking."""

import logging
from decimal import Decimal
from typing import Any, Optional

from pricerecon.connectors.base import BaseConnector
from pricerecon.models import Condition, NormalizedListing, SourceType

logger = logging.getLogger(__name__)

try:
    import httpx
except ImportError:
    httpx = None  # type: ignore[assignment]
    logger.warning("httpx not installed. CamelCamelCamel connector will not function.")


class CamelCamelCamelConnector(BaseConnector):
    """CamelCamelCamel connector for Amazon price history.

    CamelCamelCamel provides API access to Amazon product price history.
    API documentation: https://camelcamelcamel.com/api
    """

    CONNECTOR_ID = "camelcamelcamel"
    BASE_URL = "https://camelcamelcamel.com"
    API_KEY_ENV_VAR = "CAMELCAMELCAMEL_API_KEY"

    def __init__(self, config: Optional[dict[str, Any]] = None):
        """Initialize the CamelCamelCamel connector.

        Args:
            config: Optional config with 'api_key' (or set CAMELCAMELCAMEL_API_KEY env var)
        """
        if httpx is None:
            raise ImportError("httpx is required. Install with: pip install httpx")

        self.config = config or {}

        # Get API key from config or environment
        import os

        self.api_key = self.config.get("api_key") or os.getenv(self.API_KEY_ENV_VAR)

        if not self.api_key:
            logger.warning(
                f"{self.API_KEY_ENV_VAR} not set. "
                "Connector will use public access only (rate limited)."
            )

        self.session: Optional[httpx.AsyncClient] = None  # type: ignore[valid-type]

    @property
    def source_role(self) -> SourceType:
        """CamelCamelCamel is a signal source (price history data)."""
        return SourceType.SIGNAL

    async def initialize(self) -> None:
        """Initialize the connector."""
        headers = {"User-Agent": "PriceRecon/1.0"}
        if self.api_key:
            headers["X-API-Key"] = self.api_key

        self.session = httpx.AsyncClient(
            headers=headers,
            timeout=30.0,
        )

    async def cleanup(self) -> None:
        """Close the session."""
        if self.session:
            await self.session.aclose()
            self.session = None

    async def search(
        self, query: str, filters: Optional[dict[str, Any]] = None
    ) -> list[NormalizedListing]:
        """Search CamelCamelCamel for Amazon product price history.

        CamelCamelCamel requires an Amazon ASIN or product URL.
        If query is an ASIN, fetch price history directly.
        Otherwise, return empty list (ASIN required).

        Args:
            query: Search query (ASIN or Amazon product URL)
            filters: Optional filters (domain, marketplace)

        Returns:
            List of normalized listings with price history data
        """
        filters = filters or {}
        domain = filters.get("domain", "co.uk")  # Default to Amazon UK

        # Extract ASIN from query
        asin = self._extract_asin(query)
        if not asin:
            logger.warning(f"Could not extract ASIN from query: {query}")
            return []

        # Fetch product data from CamelCamelCamel
        try:
            product_data = await self._fetch_product_data(asin, domain)
        except Exception as e:
            logger.error(f"Failed to fetch CamelCamelCamel data for {asin}: {e}")
            return []

        if not product_data:
            return []

        # Create normalized listing
        listing = self._create_listing(product_data, asin, domain)
        return [listing] if listing else []

    def _extract_asin(self, query: str) -> Optional[str]:
        """Extract Amazon ASIN from query.

        Args:
            query: Query string (ASIN or Amazon URL)

        Returns:
            ASIN string or None
        """
        import re

        # Try to match ASIN pattern (10 alphanumeric characters)
        asin_match = re.search(r"\b([A-Z0-9]{10})\b", query.upper())
        if asin_match:
            return asin_match.group(1)

        # Try to extract from Amazon URL
        url_match = re.search(r"/(?:dp|product|ASIN)/([A-Z0-9]{10})", query)
        if url_match:
            return url_match.group(1)

        return None

    async def _fetch_product_data(self, asin: str, domain: str) -> Optional[dict[str, Any]]:
        """Fetch product data from CamelCamelCamel API.

        Args:
            asin: Amazon ASIN
            domain: Amazon domain (e.g., 'co.uk', 'com', 'de')

        Returns:
            Product data dict or None
        """
        if not self.session:
            await self.initialize()

        # Construct API URL
        # CamelCamelCamel API endpoints:
        # - /search/products.json?query=ASIN
        # - /product/ASIN?format=json&domain=DOMAIN
        url = f"{self.BASE_URL}/product/{asin}"
        params = {"format": "json", "domain": domain}

        try:
            response = await self.session.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching product {asin}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error fetching product {asin}: {e}")
            return None

    def _create_listing(
        self, data: dict[str, Any], asin: str, domain: str
    ) -> Optional[NormalizedListing]:
        """Create normalized listing from CamelCamelCamel data.

        Args:
            data: Product data from API
            asin: Amazon ASIN
            domain: Amazon domain

        Returns:
            NormalizedListing or None
        """
        try:
            # Extract basic fields
            title = data.get("title") or f"Amazon Product {asin}"
            url = data.get("url") or f"https://www.amazon.{domain}/dp/{asin}"

            # Extract current price from Amazon prices
            price = Decimal("0.00")
            price_data = data.get("prices", {})
            if price_data:
                # Try Amazon prices first, then new prices
                amazon_prices = price_data.get("amazon", [])
                new_prices = price_data.get("new", [])

                # Get latest price from Amazon or new
                prices_to_check = amazon_prices if amazon_prices else new_prices
                if prices_to_check and len(prices_to_check) > 0:
                    # Each price point is [timestamp, price]
                    latest_price = prices_to_check[-1][1] if len(prices_to_check[-1]) > 1 else None
                    if latest_price:
                        try:
                            price = Decimal(str(latest_price))
                        except (ValueError, TypeError):
                            pass

            # Determine currency from domain
            currency_map = {
                "co.uk": "GBP",
                "com": "USD",
                "de": "EUR",
                "fr": "EUR",
                "it": "EUR",
                "es": "EUR",
                "ca": "CAD",
                "com.au": "AUD",
            }
            currency = currency_map.get(domain, "USD")

            # Extract price history data
            price_history = self._extract_price_history(data)

            # Create normalized listing
            listing = NormalizedListing.model_validate(
                {
                    "source": self.CONNECTOR_ID,
                    "source_type": self.source_role,
                    "source_listing_id": asin,
                    "title_raw": title,
                    "price": price if price > 0 else None,
                    "currency": currency,
                    "url": url,
                    "condition": Condition.NEW,  # Amazon default
                    "in_stock": price > 0,
                    "variant_normalized": {"price_history": price_history},
                    "category": data.get("category"),
                    "image_url": data.get("image_url"),
                }
            )

            return listing
        except Exception as e:
            logger.error(f"Error creating listing from data: {e}")
            return None

    def _extract_price_history(self, data: dict[str, Any]) -> dict[str, Any]:
        """Extract price history from CamelCamelCamel data.

        Args:
            data: Product data from API

        Returns:
            Dict with price history data
        """
        history = {}

        # CamelCamelCamel price history structure:
        # prices: {amazon: [price_points], new: [price_points], used: [price_points]}
        # Each price point: [timestamp_epoch, price]
        prices = data.get("prices", {})

        # Extract Amazon price history
        amazon_prices = prices.get("amazon", [])
        if amazon_prices:
            history["amazon_count"] = len(amazon_prices)
            if amazon_prices:
                # Get min/max prices
                price_values = [p[1] for p in amazon_prices if p[1]]
                if price_values:
                    history["amazon_min"] = min(price_values)
                    history["amazon_max"] = max(price_values)
                    history["amazon_current"] = price_values[-1]

        # Extract new price history
        new_prices = prices.get("new", [])
        if new_prices:
            history["new_count"] = len(new_prices)
            if new_prices:
                price_values = [p[1] for p in new_prices if p[1]]
                if price_values:
                    history["new_min"] = min(price_values)
                    history["new_max"] = max(price_values)
                    history["new_current"] = price_values[-1]

        # Extract used price history
        used_prices = prices.get("used", [])
        if used_prices:
            history["used_count"] = len(used_prices)
            if used_prices:
                price_values = [p[1] for p in used_prices if p[1]]
                if price_values:
                    history["used_min"] = min(price_values)
                    history["used_max"] = max(price_values)
                    history["used_current"] = price_values[-1]

        return history
