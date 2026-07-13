"""Tests for Amazon UK connector."""

import pytest
from decimal import Decimal
from unittest.mock import Mock, MagicMock

from pricerecon.connectors.amazon import AmazonConnector
from pricerecon.models import Condition, SourceType


@pytest.fixture
def mock_session():
    """Mock curl_cffi session."""
    session = MagicMock()
    return session


@pytest.fixture
def connector(monkeypatch, mock_session):
    """Create Amazon connector with mocked session."""
    # Mock curl_cffi.requests.Session
    mock_requests = MagicMock()
    mock_requests.Session.return_value = mock_session

    monkeypatch.setattr("pricerecon.connectors.amazon.requests", mock_requests)

    return AmazonConnector()


def test_connector_id(connector):
    """Test connector ID."""
    assert connector.CONNECTOR_ID == "amazon_uk"
    assert connector.connector_id == "amazon_uk"


def test_source_role(connector):
    """Test source role."""
    assert connector.source_role == SourceType.RETAILER


def test_initialize(connector):
    """Test initialization."""
    import asyncio

    asyncio.run(connector.initialize())
    # Should not raise


def test_cleanup(connector):
    """Test cleanup."""
    import asyncio

    asyncio.run(connector.cleanup())
    # Should not raise


@pytest.mark.asyncio
async def test_search_basic(connector, mock_session):
    """Test basic search."""
    # Mock response with HTML containing ASINs and prices
    mock_response = Mock()
    mock_response.text = """
        <div data-asin="B0C123ABC1">
            <span class="a-offscreen">£599.99</span>
            <h2>RTX 4090</h2>
        </div>
        <div data-asin="B0C456DEF2">
            <span class="a-offscreen">£649.99</span>
            <h2>RTX 4090 OC</h2>
        </div>
        <a href="/dp/B0C789GHI3">Another product</a>
    """
    mock_response.raise_for_status = Mock()
    mock_session.get.return_value = mock_response

    # Perform search
    listings = await connector.search("RTX 4090")

    # Verify
    assert len(listings) >= 2  # At least 2 ASINs found

    # Check first listing
    first = listings[0]
    assert first.source == "amazon_uk"
    assert first.source_type == SourceType.RETAILER
    assert first.currency == "GBP"
    assert first.condition == Condition.NEW
    assert "/dp/" in first.url

    # Verify session was called with correct params
    mock_session.get.assert_called_once()
    call_args = mock_session.get.call_args
    assert "RTX 4090" in str(call_args)


@pytest.mark.asyncio
async def test_search_with_refurbished_filter(connector, mock_session):
    """Test search with refurbished condition filter."""
    # Mock response
    mock_response = Mock()
    mock_response.text = """
        <div data-asin="B0C123ABC1">
            <span class="a-offscreen">£499.99</span>
        </div>
    """
    mock_response.raise_for_status = Mock()
    mock_session.get.return_value = mock_response

    # Search with refurbished filter
    listings = await connector.search("RTX 4090", {"condition": "refurbished"})

    # Verify condition filter was applied
    assert len(listings) >= 1
    assert listings[0].condition == Condition.REFURBISHED

    # Verify URL includes refurbished filter
    mock_session.get.assert_called_once()
    call_args = mock_session.get.call_args
    assert "p_n_condition-type:1486414031" in str(call_args)


@pytest.mark.asyncio
async def test_search_error_handling(connector, mock_session):
    """Test search error handling."""
    # Mock request failure
    mock_session.get.side_effect = Exception("Network error")

    # Search should return empty list on error
    listings = await connector.search("RTX 4090")
    assert listings == []


@pytest.mark.asyncio
async def test_get_product_page(connector, mock_session):
    """Test product page fetching."""
    # Mock product page response
    mock_response = Mock()
    mock_response.text = """
        <span id="productTitle">NVIDIA GeForce RTX 4090 24GB</span>
        <span class="a-offscreen">£599.99</span>
        <span id="availability">
            <span>In Stock.</span>
        </span>
        <img id="landingImage" src="https://example.com/image.jpg" />
    """
    mock_response.raise_for_status = Mock()
    mock_session.get.return_value = mock_response

    # Fetch product page
    details = await connector.get_product_page("B0C123ABC1")

    # Verify parsed details
    assert "title" in details
    assert "RTX 4090" in details["title"]
    assert details["price"] == Decimal("599.99")
    assert details["in_stock"]
    assert details["image_url"] == "https://example.com/image.jpg"


def test_parse_search_results_no_prices(connector):
    """Test parsing when no prices found."""
    html = """
        <div>
            <a href="/dp/B0C123ABC1">Product without price</a>
            <h2>Product without price</h2>
        </div>
    """

    listings = connector._parse_search_results(html, "test query", {})

    # Should still create listing with zero price
    assert len(listings) >= 1
    assert listings[0].price == Decimal("0.00")
    assert not listings[0].in_stock


def test_parse_search_results_duplicate_asins(connector):
    """Test deduplication of duplicate ASINs."""
    html = """
        <a href="/dp/B0C123ABC1">Product 1</a>
        <a href="/dp/B0C123ABC1">Product 1 duplicate</a>
        <a href="/dp/B0C456DEF2">Product 2</a>
    """

    listings = connector._parse_search_results(html, "test query", {})

    # Should deduplicate by ASIN
    source_ids = [listing.source_listing_id for listing in listings]
    assert len(source_ids) == len(set(source_ids))
