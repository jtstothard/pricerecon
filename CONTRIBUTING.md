# Contributing to PriceRecon

Thank you for your interest in contributing to PriceRecon! This guide covers how to add new connectors, run tests, and submit pull requests.

For the repo-native engineering standard, start with [docs/engineering-standard.md](docs/engineering-standard.md). It explains the PriceRecon-specific bar: explicit validation boundaries, zero unchecked escape hatches, deterministic plus live proof, shrinking baseline, and no untestable feature work.

## Quick Start

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-connector`)
3. Make your changes
4. Add tests
5. Ensure the quality gate passes: `python -m pricerecon.quality_gate`
6. Submit a pull request

## Security and Licensing

- **Security vulnerabilities**: Do **not** open public issues. Report security issues privately to jtstothard@gmail.com. See [SECURITY.md](SECURITY.md) for details.
- **License**: By contributing, you agree that your contributions will be licensed under the MIT License, matching the project's existing license.
- **Sensitive data**: Never commit API keys, credentials, or secrets. Use environment variables for all sensitive configuration.

## Engineering standard

PriceRecon changes should be built to prove correctness, not just to satisfy a compiler or linter.

- validate raw source data at the boundary
- avoid new unchecked casts or `type: ignore` shortcuts
- back behavior changes with deterministic tests and, where the source is real, live proof
- preserve the baseline-first diff contract
- do not ship features that cannot be verified

Canonical quality entrypoints live in [docs/engineering-standard.md](docs/engineering-standard.md):

- `python -m pytest`
- `python -m ruff check .`
- `python -m mypy src/pricerecon`

## Adding a Connector

PriceRecon supports two types of connectors: Python code connectors and YAML config connectors.

### Python Connectors

For sources requiring auth flows, multi-step pagination, tier fallbacks, or complex parsing.

#### Step 1: Create the Connector File

Create a new file in `src/pricerecon/connectors/`:

```python
"""My Store connector."""

from decimal import Decimal
from datetime import datetime
from typing import Any, Optional

import httpx

from pricerecon.connectors.base import BaseConnector
from pricerecon.models import Condition, NormalizedListing, SourceType


class MyStoreConnector(BaseConnector):
    """My Store connector."""

    CONNECTOR_ID = "mystore"

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def source_role(self) -> SourceType:
        """Return the source type (retailer, marketplace, signal)."""
        return SourceType.RETAILER

    async def initialize(self) -> None:
        """Initialize the connector (auth setup, etc.). Optional."""
        self._client = httpx.AsyncClient(timeout=30.0)
        # Auth setup if needed

    async def cleanup(self) -> None:
        """Cleanup resources (close browser, etc.). Optional."""
        if self._client:
            await self._client.aclose()

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
        filters = filters or {}

        # Implement your search logic here
        url = "https://mystore.com/api/search"
        params = {"q": query}

        if "price_max" in filters:
            params["max_price"] = filters["price_max"]

        response = await self._client.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        return self._parse_listings(data.get("items", []))

    def _parse_listings(self, items: list[dict]) -> list[NormalizedListing]:
        """Parse raw API response into NormalizedListing objects."""
        listings = []

        for item in items:
            try:
                listing = NormalizedListing(
                    source="mystore",
                    source_type=self.source_role,
                    source_listing_id=str(item["id"]),
                    title_raw=item["title"],
                    price=Decimal(str(item["price"])),
                    currency=item.get("currency", "GBP"),
                    url=item["url"],
                    timestamp_seen=datetime.utcnow(),
                    # Optional enrichment fields
                    condition=self._parse_condition(item.get("condition")),
                    seller_or_store=item.get("seller"),
                    in_stock=item.get("in_stock", True),
                    image_url=item.get("image"),
                )
                listings.append(listing)
            except Exception as exc:
                import logging
                logging.warning("Failed to parse MyStore listing: %s", exc)

        return listings

    def _parse_condition(self, condition_raw: str | None) -> Optional[Condition]:
        """Parse raw condition string to enum."""
        if not condition_raw:
            return None

        condition_map = {
            "new": Condition.NEW,
            "refurbished": Condition.REFURBISHED,
            "used": Condition.USED_GOOD,
        }
        return condition_map.get(condition_raw.lower())
```

#### Step 2: Register the Connector

Add your connector to `pyproject.toml` under `[project.entry-points."pricerecon.connectors"]`:

```toml
[project.entry-points."pricerecon.connectors"]
ebay = "pricerecon.connectors.ebay:eBayConnector"
amazon_uk = "pricerecon.connectors.amazon:AmazonConnector"
cex = "pricerecon.connectors.cex:CexConnector"
mystore = "pricerecon.connectors.mystore:MyStoreConnector"  # Add this
```

#### Step 3: Add Tests

Create `tests/test_mystore.py`:

```python
"""Tests for MyStore connector."""

import pytest
from decimal import Decimal

from pricerecon.connectors.mystore import MyStoreConnector
from pricerecon.models import SourceType


@pytest.fixture
def connector():
    """Create connector fixture."""
    return MyStoreConnector()


def test_source_role(connector):
    """Test source role."""
    assert connector.source_role == SourceType.RETAILER


@pytest.mark.asyncio
async def test_search_empty(connector, respx_mock):
    """Test search with no results."""
    connector._client = httpx.AsyncClient()

    respx_mock.get("https://mystore.com/api/search").mock(
        return_value=httpx.Response(200, json={"items": []})
    )

    results = await connector.search("test query")
    assert results == []


@pytest.mark.asyncio
async def test_search_with_results(connector, respx_mock):
    """Test search with results."""
    connector._client = httpx.AsyncClient()

    mock_response = {
        "items": [
            {
                "id": "123",
                "title": "Test Product",
                "price": "99.99",
                "currency": "GBP",
                "url": "https://mystore.com/product/123",
                "in_stock": True,
            }
        ]
    }

    respx_mock.get("https://mystore.com/api/search").mock(
        return_value=httpx.Response(200, json=mock_response)
    )

    results = await connector.search("test query")
    assert len(results) == 1
    assert results[0].title_raw == "Test Product"
    assert results[0].price == Decimal("99.99")
    assert results[0].currency == "GBP"
```

### YAML Config Connectors

For simple sources without auth, configure via YAML in `connectors/` directory:

```yaml
# connectors/mystore.yml
name: mystore
source_type: retailer
base_url: https://mystore.com
search_endpoint: /search
method: GET
params:
  q: "{{query}}"
listings_selector: .product-card
fields:
  title:
    selector: .title
  price:
    selector: .price
    type: numeric
  url:
    selector: a
    attribute: href
  image:
    selector: img
    attribute: src
  in_stock:
    selector: .stock-status
    map:
      "In Stock": true
      "Out of Stock": false
```

## BaseConnector Interface

All connectors must inherit from `BaseConnector` and implement:

```python
from abc import ABC, abstractmethod

class BaseConnector(ABC):
    @property
    @abstractmethod
    def source_role(self) -> SourceType:
        """Return the source type (retailer, marketplace, signal)."""
        pass

    @abstractmethod
    async def search(
        self, query: str, filters: Optional[dict[str, Any]] = None
    ) -> list[NormalizedListing]:
        """Search the source for matching listings."""
        pass

    async def initialize(self) -> None:
        """Initialize the connector (auth setup, etc.). Optional."""
        pass

    async def cleanup(self) -> None:
        """Cleanup resources (close browser, etc.). Optional."""
        pass
```

## NormalizedListing Schema

All connectors must return `list[NormalizedListing]`. Required fields:

| Field | Type | Description |
|-------|------|-------------|
| `source` | str | Connector identifier (e.g., 'ebay', 'cex') |
| `source_type` | SourceType | Source role (RETAILER, MARKETPLACE, SIGNAL) |
| `source_listing_id` | str | Stable ID from source |
| `title_raw` | str | Original listing title |
| `price` | Decimal | Current price in source currency |
| `currency` | str | ISO 4217 currency code |
| `url` | str | Direct link to listing |

Optional enrichment fields:

| Field | Type | Description |
|-------|------|-------------|
| `condition` | Condition | Normalized condition (NEW, USED_GOOD, etc.) |
| `condition_raw` | str | Original condition text |
| `shipping_cost` | Decimal | Shipping cost |
| `total_landed_cost` | Decimal | price + shipping |
| `seller_or_store` | str | Seller name |
| `seller_feedback_score` | int | Feedback count |
| `seller_feedback_pct` | Decimal | Feedback % (0-100) |
| `in_stock` | bool | Item is buyable |
| `stock_state` | StockState | Stock state (IN_STOCK, OUT_OF_STOCK, etc.) |
| `image_url` | str | Primary product image |
| `location` | str | Geographic location |
| `category` | str | Product category |

## Source Roles

- **RETAILER** — Official retailer sites, single seller per listing
- **MARKETPLACE** — Multi-seller platforms with user listings
- **SIGNAL** — Community forums, deal aggregators, RSS feeds

## Running Tests

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run all tests
pytest

# Run specific test file
pytest tests/test_mystore.py

# Run with coverage
pytest --cov=pricerecon --cov-report=html
```

## PR Checklist

Before submitting a PR, ensure:

- [ ] Code follows the existing style (use `black` and `ruff`)
- [ ] Tests added for new functionality
- [ ] All relevant checks passed from the canonical entrypoints
- [ ] Connector handles errors gracefully
- [ ] NormalizedListing includes all required fields
- [ ] Source type is correctly declared
- [ ] Documentation updated (README.md, docs/)
- [ ] Validation boundaries are explicit and unchecked escape hatches are avoided
- [ ] Live proof was captured when the change touches a real source or browser flow
- [ ] No API keys or secrets committed

## Optional Dependencies

Some connectors require optional dependencies:

- `playwright` — For FB Marketplace connector (browser automation)
- `curl_cffi` — For Amazon connector (TLS fingerprinting)

Tests should not fail if these are missing. Use skip decorators:

```python
import pytest

@pytest.mark.skipif(
    not pytest.importorskip("playwright"),
    reason="playwright not installed"
)
@pytest.mark.asyncio
async def test_fb_marketplace():
    pass
```

## Questions?

- Read [docs/engineering-standard.md](docs/engineering-standard.md) first for the repo-wide standard
- See [Connector Development Guide](docs/connector-development.md) for detailed implementation guidance
- Open an issue for bugs or questions
- Check existing connectors for patterns (e.g., `ebay.py`, `cex.py`)

---

Thank you for contributing! 🚀