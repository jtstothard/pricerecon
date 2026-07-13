# Connector Development Guide

This guide covers how to build connectors for PriceRecon, including the BaseConnector interface, NormalizedListing schema, source roles, and how the diff engine processes your listings.

## Overview

A connector is a Python class that:

1. Inherits from `BaseConnector`
2. Declares its `source_role` (retailer, marketplace, or signal)
3. Implements the `search()` method to return `list[NormalizedListing]`
4. Optionally implements `initialize()` and `cleanup()` for resource management

## BaseConnector Interface

```python
from abc import ABC, abstractmethod
from typing import Any, Optional

class BaseConnector(ABC):
    """Abstract base class for all connectors.

    Connectors implement search(query, filters) to return normalized listings.
    They also declare their source role (retailer, marketplace, signal).
    """

    @property
    @abstractmethod
    def source_role(self) -> SourceType:
        """Return the source type (retailer, marketplace, signal)."""
        pass

    @property
    def connector_id(self) -> str:
        """Return the connector identifier (e.g., 'ebay', 'cex')."""
        explicit = getattr(self, "CONNECTOR_ID", None)
        if explicit:
            return str(explicit)
        return self.__class__.__name__.lower().replace("connector", "")

    @abstractmethod
    async def search(
        self, query: str, filters: Optional[dict[str, Any]] = None
    ) -> list[NormalizedListing]:
        """Search the source for matching listings.

        Args:
            query: Search query string
            filters: Optional filters (price_max, condition, etc.)

        Returns:
            List of normalized listings
        """
        pass

    async def initialize(self) -> None:
        """Initialize the connector (auth setup, etc.). Optional."""

    async def cleanup(self) -> None:
        """Cleanup resources (close browser, etc.). Optional."""
```

## NormalizedListing Schema

All connectors must return `list[NormalizedListing]`. The schema is tiered:

### Required Fields

These fields **must** be populated for every listing:

| Field | Type | Description |
|-------|------|-------------|
| `source` | str | Connector identifier (e.g., 'ebay', 'cex') |
| `source_type` | SourceType | Source role (RETAILER, MARKETPLACE, SIGNAL) |
| `source_listing_id` | str | Stable ID from source (used for deduplication) |
| `title_raw` | str | Original listing title (unmodified) |
| `price` | Decimal | Current price in source currency |
| `currency` | str | ISO 4217 currency code (e.g., 'GBP', 'USD', 'EUR') |
| `url` | str | Direct link to listing |
| `timestamp_seen` | datetime | When the listing was seen (defaults to now) |

### Optional Enrichment Fields

These fields **should** be populated when available:

| Field | Type | Description |
|-------|------|-------------|
| `product_normalized` | str | Normalized product name (e.g., "NVIDIA RTX 3090") |
| `variant_normalized` | dict[str, Any] | Parsed specs (GPU, RAM, storage, CPU, etc.) |
| `condition` | Condition | Normalized condition enum (NEW, USED_GOOD, etc.) |
| `condition_raw` | str | Original condition text from source |
| `shipping_cost` | Decimal | Shipping cost |
| `total_landed_cost` | Decimal | price + shipping |
| `seller_or_store` | str | Seller name or store name |
| `seller_feedback_score` | int | Feedback count |
| `seller_feedback_pct` | Decimal | Feedback percentage (0-100) |
| `location` | str | Geographic location (e.g., "London, UK") |
| `in_stock` | bool | Item is currently buyable |
| `stock_state` | StockState | Stock state (IN_STOCK, OUT_OF_STOCK, etc.) |
| `image_url` | str | Primary product image URL |
| `exact_variant_confirmed` | bool | Spec verified (not inferred) |
| `variant_match_confidence` | VariantMatchConfidence | Match confidence (HIGH, MEDIUM, LOW) |
| `mismatch_flags` | list[str] | Flags like ['WRONG_VARIANT', 'ACCESSORIES_ONLY'] |
| `risk_flags` | list[str] | Flags like ['LOW_SELLER_FEEDBACK'] |
| `category` | str | Product category |

### Enums

```python
class Condition(str, Enum):
    NEW = "new"
    NEW_OPEN_BOX = "new_open_box"
    REFURBISHED = "refurbished"
    USED_LIKE_NEW = "used_like_new"
    USED_GOOD = "used_good"
    USED_FAIR = "used_fair"
    FOR_PARTS = "for_parts"

class StockState(str, Enum):
    IN_STOCK = "in_stock"
    OUT_OF_STOCK = "out_of_stock"
    BACK_ORDER = "back_order"
    PRE_ORDER = "pre_order"
    DISCONTINUED = "discontinued"

class SourceType(str, Enum):
    RETAILER = "retailer"
    MARKETPLACE = "marketplace"
    SIGNAL = "signal"

class VariantMatchConfidence(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNKNOWN = "unknown"
```

## Source Roles

Each connector must declare its `source_role`:

### RETAILER
- **Definition**: Official retailer sites with single seller per listing
- **Examples**: Amazon, Currys, Scan, Box, Overclockers
- **Characteristics**:
  - Fixed product catalog
  - Prices change over time, but listings are stable
  - No seller marketplace model
- **Diff behavior**: Price drops/increases are significant; new listings are rare

### MARKETPLACE
- **Definition**: Multi-seller platforms with user-generated listings
- **Examples**: eBay, CeX, Facebook Marketplace, Shopify stores
- **Characteristics**:
  - Many sellers offering the same product
  - Listings appear and disappear frequently
  - Seller feedback matters
- **Diff behavior**:
  - New listings appear often (signal of supply)
  - Listings gone (signal of sold out/delisted)
  - Price changes within listings
  - Seller quality signals (feedback, flags)

### SIGNAL
- **Definition**: Community forums, deal aggregators, RSS feeds
- **Examples**: Reddit, HotUKDeals, deal blogs
- **Characteristics**:
  - Not direct listings, but pointers to deals
  - Community-curated content
  - Often time-sensitive
- **Operational notes**:
  - Prefer canonical feed URLs over redirecting aliases. HotUKDeals currently resolves directly at `/rss/new`; if a feed starts redirecting, update the template to the canonical path instead of relying on the redirect chain.
  - Reddit community feeds are frequently rate limited or bot-blocked. Treat HTTP 429 as `rate_limited` with retry on the next sweep, and HTTP 403 as `bot_blocked`/anti-bot rather than a generic failure.
  - For Reddit, prefer queryless `/new/.rss` fetching plus local query filtering. That keeps the connector resilient when Reddit blocks search RSS endpoints.

## Connector Config Patterns


### API Key Configuration

Many connectors require API keys or credentials. Store these in the environment:

```python
import os
from pricerecon.connectors.base import BaseConnector

class MyConnector(BaseConnector):
    def __init__(self):
        self.api_key = os.getenv("MYSTORE_API_KEY")
        if not self.api_key:
            raise ValueError("MYSTORE_API_KEY environment variable required")

    async def search(self, query: str, filters: dict | None = None) -> list[NormalizedListing]:
        headers = {"Authorization": f"Bearer {self.api_key}"}
        # ... rest of implementation
```

### HTTP Client Management

Use `httpx.AsyncClient` for async HTTP requests:

```python
import httpx
from typing import Optional

class MyConnector(BaseConnector):
    def __init__(self):
        self._client: Optional[httpx.AsyncClient] = None

    async def initialize(self) -> None:
        self._client = httpx.AsyncClient(timeout=30.0)

    async def cleanup(self) -> None:
        if self._client:
            await self._client.aclose()

    async def search(self, query: str, filters: dict | None = None) -> list[NormalizedListing]:
        response = await self._client.get(
            "https://api.mystore.com/search",
            params={"q": query}
        )
        response.raise_for_status()
        return self._parse_listings(response.json()["items"])
```

### Browser Automation (Playwright)

For sources requiring JavaScript execution:

```python
from playwright.async_api import async_playwright

class MyConnector(BaseConnector):
    async def initialize(self) -> None:
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch()
        self.context = await self.browser.new_context()

    async def cleanup(self) -> None:
        await self.context.close()
        await self.browser.close()
        await self.playwright.stop()

    async def search(self, query: str, filters: dict | None = None) -> list[NormalizedListing]:
        page = await self.context.new_page()
        await page.goto(f"https://mystore.com/search?q={query}")
        await page.wait_for_selector(".product-card")

        listings = await page.eval_on_selector_all(
            ".product-card",
            """elements => elements.map(el => ({
                title: el.querySelector('.title').textContent,
                price: el.querySelector('.price').textContent,
                url: el.querySelector('a').href
            }))"""
        )

        await page.close()
        return self._parse_listings(listings)
```

### Session Cookie Authentication

For sources requiring logged-in sessions:

```python
import os
from playwright.async_api import async_playwright

class MyConnector(BaseConnector):
    async def initialize(self) -> None:
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=True)
        self.context = await self.browser.new_context()

        # Load session cookies from environment
        cookies = [
            {"name": "session", "value": os.getenv("SESSION_COOKIE")},
            {"name": "auth", "value": os.getenv("AUTH_COOKIE")},
        ]
        await self.context.add_cookies(cookies)

    async def search(self, query: str, filters: dict | None = None) -> list[NormalizedListing]:
        page = await self.context.new_page()
        await page.goto("https://mystore.com")
        # ... rest of implementation
```

## How the Diff Engine Uses Listings

The diff engine (`pricerecon/core/diff_engine.py`) processes your listings as follows:

### 1. First Run (Baseline)

On the first run for a watch, no events are generated. This establishes a baseline for future comparisons.

### 2. Subsequent Runs (Diff)

The engine compares current listings with previous listings using the composite key `(source, source_listing_id)`:

#### New Listings
- Listings that didn't exist in the previous run
- Event type: `NEW_LISTING`
- Most significant for MARKETPLACE sources (new supply)

#### Price Changes
- Existing listings with different prices
- Event type: `PRICE_DROP` or `PRICE_INCREASE`
- Significant for RETAILER and MARKETPLACE sources

#### Stock Changes
- Existing listings where `in_stock` changed from True ↔ False
- Event type: `STOCK_CHANGE`
- Important for all sources

#### Listings Gone
- Listings that existed but are no longer present
- Event type: `LISTING_GONE`
- Most significant for MARKETPLACE sources (sold/delisted)

### 3. Event Storage

All events are stored in the `events` table with:

- `watch_id`: The watch being monitored
- `event_type`: One of the four types above
- `listing_key`: Composite key `(source, source_listing_id)`
- `severity`: Currently always "info"
- `event_json`: Full event data including before/after values

### 4. Notification Triggers

The notification system reads from the `events` table and sends alerts based on configuration.

## Example Connector Walkthrough

Let's walk through a complete connector implementation for a hypothetical retailer "TechStore":

```python
"""TechStore connector."""

import logging
from decimal import Decimal
from datetime import datetime
from typing import Any, Optional

import httpx

from pricerecon.connectors.base import BaseConnector
from pricerecon.models import Condition, NormalizedListing, SourceType, StockState

logger = logging.getLogger(__name__)


class TechStoreConnector(BaseConnector):
    """TechStore retailer connector."""

    CONNECTOR_ID = "techstore"

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def source_role(self) -> SourceType:
        """TechStore is a retailer."""
        return SourceType.RETAILER

    async def initialize(self) -> None:
        """Initialize HTTP client."""
        self._client = httpx.AsyncClient(
            timeout=30.0,
            headers={"User-Agent": "PriceRecon/1.0"}
        )

        # Validate API key if provided
        if self.api_key:
            response = await self._client.get(
                "https://api.techstore.com/validate",
                headers={"X-API-Key": self.api_key}
            )
            response.raise_for_status()
            logger.info("TechStore API key validated")

    async def cleanup(self) -> None:
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()

    async def search(
        self, query: str, filters: Optional[dict[str, Any]] = None
    ) -> list[NormalizedListing]:
        """Search TechStore for matching products."""
        filters = filters or {}

        # Build request parameters
        params = {"q": query, "limit": 50}

        if "price_max" in filters:
            params["max_price"] = filters["price_max"]

        if "condition" in filters:
            params["condition"] = self._map_condition(filters["condition"])

        # Make API request
        headers = {}
        if self.api_key:
            headers["X-API-Key"] = self.api_key

        response = await self._client.get(
            "https://api.techstore.com/products",
            params=params,
            headers=headers
        )
        response.raise_for_status()

        data = response.json()
        return self._parse_listings(data.get("products", []))

    def _parse_listings(self, items: list[dict]) -> list[NormalizedListing]:
        """Parse API response into NormalizedListing objects."""
        listings = []

        for item in items:
            try:
                # Parse price (handle "£99.99" or "99.99 GBP")
                price_str = item.get("price", "0")
                if "£" in price_str:
                    price_str = price_str.replace("£", "").strip()
                elif "GBP" in price_str:
                    price_str = price_str.replace("GBP", "").strip()

                # Parse stock state
                stock_state = self._parse_stock_state(item.get("stock"))
                in_stock = stock_state != StockState.OUT_OF_STOCK

                # Build listing
                listing = NormalizedListing(
                    source=self.connector_id,
                    source_type=self.source_role,
                    source_listing_id=str(item["id"]),
                    title_raw=item["title"],
                    price=Decimal(price_str),
                    currency="GBP",
                    url=item.get("url", f"https://techstore.com/product/{item['id']}"),
                    timestamp_seen=datetime.utcnow(),

                    # Optional enrichment fields
                    condition=self._parse_condition(item.get("condition")),
                    condition_raw=item.get("condition"),
                    shipping_cost=Decimal(str(item.get("shipping", "0"))),
                    total_landed_cost=Decimal(price_str) + Decimal(str(item.get("shipping", "0"))),
                    in_stock=in_stock,
                    stock_state=stock_state,
                    image_url=item.get("image"),
                    category=item.get("category"),
                )
                listings.append(listing)

            except Exception as exc:
                logger.warning("Failed to parse TechStore listing %s: %s", item.get("id", "?"), exc)

        return listings

    def _map_condition(self, condition: str) -> str:
        """Map normalized condition to API value."""
        mapping = {
            "new": "brand_new",
            "refurbished": "refurbished",
            "used_good": "used_good",
            "used_fair": "used_fair",
        }
        return mapping.get(condition, "any")

    def _parse_condition(self, condition_raw: str | None) -> Optional[Condition]:
        """Parse API condition string to enum."""
        if not condition_raw:
            return None

        mapping = {
            "Brand New": Condition.NEW,
            "Refurbished": Condition.REFURBISHED,
            "Used - Good": Condition.USED_GOOD,
            "Used - Fair": Condition.USED_FAIR,
            "For Parts": Condition.FOR_PARTS,
        }
        return mapping.get(condition_raw)

    def _parse_stock_state(self, stock_raw: str | None) -> Optional[StockState]:
        """Parse API stock string to enum."""
        if not stock_raw:
            return None

        mapping = {
            "In Stock": StockState.IN_STOCK,
            "Out of Stock": StockState.OUT_OF_STOCK,
            "Pre-order": StockState.PRE_ORDER,
            "Discontinued": StockState.DISCONTINUED,
        }
        return mapping.get(stock_raw)
```

## Testing Your Connector

Write comprehensive tests:

```python
"""Tests for TechStore connector."""

import pytest
from decimal import Decimal

from pricerecon.connectors.techstore import TechStoreConnector
from pricerecon.models import SourceType, Condition, StockState


@pytest.fixture
def connector():
    """Create connector fixture."""
    return TechStoreConnector(api_key="test-key")


def test_source_role(connector):
    """Test source role."""
    assert connector.source_role == SourceType.RETAILER
    assert connector.connector_id == "techstore"


@pytest.mark.asyncio
async def test_search_empty(connector, respx_mock):
    """Test search with no results."""
    await connector.initialize()

    respx_mock.get("https://api.techstore.com/products").mock(
        return_value=httpx.Response(200, json={"products": []})
    )

    results = await connector.search("nonexistent")
    assert results == []

    await connector.cleanup()


@pytest.mark.asyncio
async def test_search_with_results(connector, respx_mock):
    """Test search with results."""
    await connector.initialize()

    mock_response = {
        "products": [
            {
                "id": "12345",
                "title": "NVIDIA RTX 3090",
                "price": "£699.99",
                "shipping": "5.00",
                "condition": "Brand New",
                "stock": "In Stock",
                "url": "https://techstore.com/product/12345",
                "image": "https://techstore.com/images/12345.jpg",
                "category": "Graphics Cards",
            }
        ]
    }

    respx_mock.get("https://api.techstore.com/products").mock(
        return_value=httpx.Response(200, json=mock_response)
    )

    results = await connector.search("RTX 3090")

    assert len(results) == 1
    listing = results[0]

    assert listing.source == "techstore"
    assert listing.source_type == SourceType.RETAILER
    assert listing.source_listing_id == "12345"
    assert listing.title_raw == "NVIDIA RTX 3090"
    assert listing.price == Decimal("699.99")
    assert listing.currency == "GBP"
    assert listing.condition == Condition.NEW
    assert listing.in_stock is True
    assert listing.stock_state == StockState.IN_STOCK
    assert listing.shipping_cost == Decimal("5.00")
    assert listing.total_landed_cost == Decimal("704.99")

    await connector.cleanup()


@pytest.mark.asyncio
async def test_search_with_filters(connector, respx_mock):
    """Test search with price filter."""
    await connector.initialize()

    def validate_request(request):
        assert "max_price=500" in request.url.params
        return True

    respx_mock.get("https://api.techstore.com/products").mock(
        return_value=httpx.Response(200, json={"products": []}),
        side_effect=validate_request
    )

    await connector.search("GPU", filters={"price_max": 500})

    await connector.cleanup()
```

## Best Practices

1. **Error Handling**: Log warnings for individual parse failures, but don't fail the entire search
2. **Rate Limiting**: Respect source rate limits (use `time.sleep` or async delays)
3. **User Agents**: Set descriptive user agents so sources can identify legitimate traffic
4. **Timeouts**: Set reasonable timeouts (30s default)
5. **Pagination**: Handle pagination gracefully (default to 50-100 items)
6. **Caching**: Consider caching expensive auth tokens or sessions
7. **Testing**: Mock HTTP responses in tests using `pytest-respx` or similar

## Troubleshooting

### Common Issues

**Issue**: "source_listing_id must be unique per source"
- **Fix**: Ensure each listing has a stable ID from the source (don't use URLs as IDs)

**Issue**: "price parsing fails"
- **Fix**: Handle various price formats (£99.99, $99.99, 99.99 GBP), strip symbols before converting to Decimal

**Issue**: "tests fail with optional deps missing"
- **Fix**: Use `@pytest.mark.skipif` to skip tests requiring optional dependencies

**Issue**: "connector hangs"
- **Fix**: Check timeout settings, ensure browser cleanup in `cleanup()` method

## Next Steps

- See existing connectors for patterns: `ebay.py`, `cex.py`, `amazon.py`
- Read the [CONTRIBUTING.md](../CONTRIBUTING.md) for PR guidelines
- Check the project structure in the main README

Happy connecting! 🚀