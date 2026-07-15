"""Tests for Back Market connector."""

import httpx
import pytest
from pricerecon.connectors.backmarket import BackMarketConnector
from pricerecon.models import SourceType


@pytest.fixture
def connector():
    """Create connector instance."""
    return BackMarketConnector()


def test_source_role(connector):
    """Test connector is a marketplace."""
    assert connector.source_role == SourceType.MARKETPLACE


def test_connector_id(connector):
    """Test connector ID."""
    assert connector.connector_id == "backmarket"


@pytest.mark.asyncio
async def test_search_parsing(connector, respx_mock):
    """Test HTML parsing with mock response."""
    html_response = """
    <article class="product-card">
        <a href="/en-gb/p/rtx-4090-test-123">
            <img src="https://example.com/image.jpg" alt="RTX 4090" />
            <h3>RTX 4090 24GB GDDR6X Graphics Card</h3>
            <div class="price">£899.00</div>
            <div class="stock">In stock</div>
        </a>
    </article>
    <article class="product-card">
        <a href="/en-gb/p/rtx-4080-test-456">
            <img src="https://example.com/image2.jpg" alt="RTX 4080" />
            <h3>RTX 4080 16GB GDDR6X Graphics Card</h3>
            <div class="price">£649.00</div>
            <div class="stock">In stock</div>
        </a>
    </article>
    """

    respx_mock.get("https://www.backmarket.com/en-gb/search?q=RTX%204090").mock(
        return_value=httpx.Response(200, text=html_response)
    )

    listings = await connector.search("RTX 4090")

    assert len(listings) == 2

    # Check first listing
    listing1 = listings[0]
    assert listing1.source == "backmarket"
    assert listing1.source_type == SourceType.MARKETPLACE
    assert "RTX 4090" in listing1.title_raw
    assert float(listing1.price) == 899.00
    assert listing1.currency == "GBP"
    assert listing1.url.startswith("https://www.backmarket.com/")
    assert listing1.image_url is not None
    assert listing1.in_stock is True


@pytest.mark.asyncio
async def test_search_empty_results(connector, respx_mock):
    """Test search with no results."""
    html_response = '<div class="no-results">No products found</div>'

    respx_mock.get("https://www.backmarket.com/en-gb/search?q=unknown").mock(
        return_value=httpx.Response(200, text=html_response)
    )

    listings = await connector.search("unknown")

    assert len(listings) == 0
