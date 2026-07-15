"""Tests for CamelCamelCamel connector."""

import pytest
from decimal import Decimal
from unittest.mock import Mock, AsyncMock

from pricerecon.connectors.camelcamelcamel import CamelCamelCamelConnector
from pricerecon.models import Condition, SourceType


@pytest.fixture
def connector() -> CamelCamelCamelConnector:
    """Create CamelCamelCamel connector."""
    return CamelCamelCamelConnector()


def test_connector_id(connector: CamelCamelCamelConnector) -> None:
    """Test connector ID."""
    assert connector.CONNECTOR_ID == "camelcamelcamel"
    assert connector.connector_id == "camelcamelcamel"


def test_source_role(connector: CamelCamelCamelConnector) -> None:
    """Test source role."""
    assert connector.source_role == SourceType.SIGNAL


@pytest.mark.asyncio
async def test_initialize(connector: CamelCamelCamelConnector) -> None:
    """Test initialization."""
    await connector.initialize()
    assert connector.session is not None
    await connector.cleanup()


@pytest.mark.asyncio
async def test_cleanup(connector: CamelCamelCamelConnector) -> None:
    """Test cleanup."""
    await connector.initialize()
    await connector.cleanup()
    assert connector.session is None


def test_extract_asin(connector: CamelCamelCamelConnector) -> None:
    """Test ASIN extraction."""
    # Direct ASIN
    assert connector._extract_asin("B0C123ABC1") == "B0C123ABC1"
    assert connector._extract_asin("b0c123abc1") == "B0C123ABC1"

    # ASIN in URL
    assert connector._extract_asin("https://amazon.co.uk/dp/B0C123ABC1") == "B0C123ABC1"
    assert connector._extract_asin("https://amazon.com/product/B0C123ABC1") == "B0C123ABC1"

    # No ASIN
    assert connector._extract_asin("just a query") is None
    assert connector._extract_asin("") is None


@pytest.mark.asyncio
async def test_search_no_asin(connector: CamelCamelCamelConnector) -> None:
    """Test search with no valid ASIN."""
    listings = await connector.search("just a random query")
    assert len(listings) == 0


@pytest.mark.asyncio
async def test_fetch_product_data_error_handling(connector: CamelCamelCamelConnector) -> None:
    """Test product data fetch error handling."""
    import httpx

    # Mock session that raises error
    mock_session = AsyncMock()
    mock_session.get.side_effect = httpx.HTTPStatusError(
        "Not Found", request=Mock(), response=Mock(status_code=404)
    )

    connector.session = mock_session

    result = await connector._fetch_product_data("B0C123ABC1", "co.uk")
    assert result is None


@pytest.mark.asyncio
async def test_extract_price_history(connector: CamelCamelCamelConnector) -> None:
    """Test price history extraction."""
    data = {
        "prices": {
            "amazon": [[1700000000, 599.99], [1700086400, 579.99], [1700172800, 649.99]],
            "new": [[1700000000, 599.99], [1700086400, 589.99]],
            "used": [[1700000000, 550.00], [1700086400, 520.00]],
        }
    }

    history = connector._extract_price_history(data)

    # Verify Amazon prices
    assert history["amazon_count"] == 3
    assert history["amazon_min"] == 579.99
    assert history["amazon_max"] == 649.99
    assert history["amazon_current"] == 649.99

    # Verify new prices
    assert history["new_count"] == 2
    assert history["new_min"] == 589.99
    assert history["new_max"] == 599.99
    assert history["new_current"] == 589.99

    # Verify used prices
    assert history["used_count"] == 2
    assert history["used_min"] == 520.00
    assert history["used_max"] == 550.00
    assert history["used_current"] == 520.00


@pytest.mark.asyncio
async def test_extract_price_history_empty(connector: CamelCamelCamelConnector) -> None:
    """Test price history extraction with empty data."""
    data = {"prices": {}}
    history = connector._extract_price_history(data)
    assert history == {}

    data = {}
    history = connector._extract_price_history(data)
    assert history == {}


@pytest.mark.asyncio
async def test_create_listing_minimal_data(connector: CamelCamelCamelConnector) -> None:
    """Test creating listing with minimal data."""
    data = {
        "title": "",
        "url": "",
        "prices": {},
    }

    listing = connector._create_listing(data, "B0C123ABC1", "co.uk")

    # Verify fallback values
    assert listing is not None
    assert listing.source_listing_id == "B0C123ABC1"
    assert listing.title_raw == "Amazon Product B0C123ABC1"
    assert listing.url == "https://www.amazon.co.uk/dp/B0C123ABC1"
    assert listing.price is None  # No price in data
    assert listing.currency == "GBP"


@pytest.mark.asyncio
async def test_create_listing_with_full_data(connector: CamelCamelCamelConnector) -> None:
    """Test creating listing with full data."""
    data = {
        "title": "Test Product",
        "url": "https://www.amazon.co.uk/dp/B0C123ABC1",
        "prices": {
            "amazon": [[1700000000, 599.99], [1700086400, 579.99]],
            "new": [[1700000000, 599.99]],
            "used": [[1700000000, 550.00]],
        },
        "category": "Electronics",
        "image_url": "https://example.com/image.jpg",
    }

    listing = connector._create_listing(data, "B0C123ABC1", "co.uk")

    assert listing is not None
    assert listing.source == "camelcamelcamel"
    assert listing.source_type == SourceType.SIGNAL
    assert listing.source_listing_id == "B0C123ABC1"
    assert listing.title_raw == "Test Product"
    assert listing.price == Decimal("579.99")  # Latest Amazon price
    assert listing.currency == "GBP"
    assert listing.condition == Condition.NEW
    assert listing.in_stock is True
    assert listing.category == "Electronics"
    assert listing.image_url == "https://example.com/image.jpg"

    # Verify price history was extracted
    assert listing.variant_normalized is not None
    price_history = listing.variant_normalized.get("price_history")
    assert price_history is not None
    assert price_history["amazon_count"] == 2
    assert price_history["amazon_min"] == 579.99
    assert price_history["amazon_max"] == 599.99
    assert price_history["amazon_current"] == 579.99
    assert price_history["new_min"] == 599.99
    assert price_history["used_min"] == 550.00


def test_currency_mapping(connector: CamelCamelCamelConnector) -> None:
    """Test currency mapping from domains."""
    # Test via _create_listing with different domains
    data = {"title": "Test", "url": "", "prices": {"amazon": [[1700000000, 100.00]]}}

    uk_listing = connector._create_listing(data, "ASIN", "co.uk")
    assert uk_listing is not None
    assert uk_listing.currency == "GBP"

    us_listing = connector._create_listing(data, "ASIN", "com")
    assert us_listing is not None
    assert us_listing.currency == "USD"

    de_listing = connector._create_listing(data, "ASIN", "de")
    assert de_listing is not None
    assert de_listing.currency == "EUR"

    ca_listing = connector._create_listing(data, "ASIN", "ca")
    assert ca_listing is not None
    assert ca_listing.currency == "CAD"

    au_listing = connector._create_listing(data, "ASIN", "com.au")
    assert au_listing is not None
    assert au_listing.currency == "AUD"
