"""Tests for Very.co.uk connector."""

import httpx
import pytest
from pricerecon.connectors.very_uk import VeryUKConnector
from pricerecon.models import SourceType


@pytest.fixture
def connector():
    """Create connector instance."""
    return VeryUKConnector()


def test_source_role(connector):
    """Test connector is a retailer."""
    assert connector.source_role == SourceType.RETAILER


def test_connector_id(connector):
    """Test connector ID."""
    assert connector.connector_id == "very_uk"


@pytest.mark.asyncio
async def test_search_parsing(connector, respx_mock):
    """Test HTML parsing with mock response."""
    html_response = """
    <article class="product-card">
        <a href="/product/rtx-4090-graphics-card">
            <img src="https://example.com/image.jpg" alt="RTX 4090" />
            <h3>RTX 4090 24GB GDDR6X Graphics Card</h3>
            <div class="price">£1699.00</div>
            <div class="stock">In stock</div>
        </a>
    </article>
    <article class="product-card">
        <a href="/product/rtx-4080-graphics-card">
            <img src="https://example.com/image2.jpg" alt="RTX 4080" />
            <h3>RTX 4080 16GB GDDR6X Graphics Card</h3>
            <div class="price">£1299.00</div>
            <div class="stock">In stock</div>
        </a>
    </article>
    """

    respx_mock.get("https://www.very.co.uk/search?q=RTX%204090").mock(
        return_value=httpx.Response(200, text=html_response)
    )

    listings = await connector.search("RTX 4090")

    assert len(listings) == 2

    # Check first listing
    listing1 = listings[0]
    assert listing1.source == "very_uk"
    assert listing1.source_type == SourceType.RETAILER
    assert "RTX 4090" in listing1.title_raw
    assert float(listing1.price) == 1699.00
    assert listing1.currency == "GBP"
    assert listing1.url.startswith("https://www.very.co.uk/")
    assert listing1.image_url is not None
    assert listing1.in_stock is True


@pytest.mark.asyncio
async def test_search_empty_results(connector, respx_mock):
    """Test search with no results."""
    html_response = '<div class="no-results">No results found</div>'

    respx_mock.get("https://www.very.co.uk/search?q=unknown").mock(
        return_value=httpx.Response(200, text=html_response)
    )

    listings = await connector.search("unknown")

    assert len(listings) == 0
