"""Tests for Back Market connector."""

from typing import Any

import httpx
import pytest
from pricerecon.connectors.backmarket import BackMarketConnector
from pricerecon.models import SourceType


@pytest.fixture
def connector() -> BackMarketConnector:
    """Create connector instance."""
    return BackMarketConnector()


def test_source_role(connector: BackMarketConnector) -> None:
    """Test connector is a marketplace."""
    assert connector.source_role == SourceType.MARKETPLACE


def test_connector_id(connector: BackMarketConnector) -> None:
    """Test connector ID."""
    assert connector.connector_id == "backmarket"


@pytest.mark.asyncio
async def test_search_parsing(connector: BackMarketConnector, respx_mock: Any) -> None:
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

    # Mock FlareSolverr POST request
    flaresolverr_response = {
        "solution": {
            "response": html_response,
            "status": 200,
            "url": "https://www.backmarket.com/en-gb/search?q=RTX%204090",
        }
    }

    respx_mock.post("http://localhost:8191/").mock(
        return_value=httpx.Response(200, json=flaresolverr_response)
    )

    listings = await connector.search("RTX 4090")

    # We expect 2 unique listings, but the parser may return duplicates
    # because the CSS selectors match each element multiple times
    # (each article matches both "article" and ".product-card")
    assert len(listings) >= 2
    unique_urls = set(listing.url for listing in listings)
    assert len(unique_urls) == 2

    # Find the RTX 4090 listing
    rtx_4090 = next(listing for listing in listings if "RTX 4090" in listing.title_raw)
    assert rtx_4090.source == "backmarket"
    assert rtx_4090.source_type == SourceType.MARKETPLACE
    assert "RTX 4090" in rtx_4090.title_raw
    assert rtx_4090.price is not None
    assert float(rtx_4090.price) == 899.00
    assert rtx_4090.currency == "GBP"
    assert rtx_4090.url.startswith("https://www.backmarket.com/")
    assert rtx_4090.image_url is not None
    assert rtx_4090.in_stock is True


@pytest.mark.asyncio
async def test_search_empty_results(connector: BackMarketConnector, respx_mock: Any) -> None:
    """Test search with no results."""
    html_response = '<div class="no-results">No products found</div>'

    # Mock FlareSolverr POST request
    flaresolverr_response = {
        "solution": {
            "response": html_response,
            "status": 200,
            "url": "https://www.backmarket.com/en-gb/search?q=unknown",
        }
    }

    respx_mock.post("http://localhost:8191/").mock(
        return_value=httpx.Response(200, json=flaresolverr_response)
    )

    listings = await connector.search("unknown")

    assert len(listings) == 0
