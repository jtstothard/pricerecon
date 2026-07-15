"""Tests for Google Shopping connector."""

from decimal import Decimal
import pytest

from pricerecon.connectors.google_shopping import GoogleShoppingConnector
from pricerecon.models import SourceType


@pytest.fixture
def sample_google_shopping_html():
    """Sample HTML from Google Shopping search results."""
    return """
    <html>
    <body>
        <div class="sh-dgr__content">
            <h3>AMD Ryzen 9 5950X Processor</h3>
            <a href="/product?id=abc123&hl=en-GB">View Product</a>
            <span class="price">£549.99</span>
            <div class="seller">Amazon UK</div>
            <div class="availability">In Stock</div>
            <img src="https://example.com/image1.jpg" />
        </div>
        <div class="sh-dgr__content">
            <h3>AMD Ryzen 9 5950X 16-Core CPU</h3>
            <a href="/product?id=def456&hl=en-GB">View Product</a>
            <span>£599.99</span>
            <div>Sold by: Ebuyer</div>
            <div>Out of Stock</div>
            <img src="https://example.com/image2.jpg" />
        </div>
        <div class="sh-dgr__grid-result">
            <h3>Ryzen 9 5950X Desktop Processor</h3>
            <a href="/product?id=ghi789&hl=en-GB">View Product</a>
            <div>£579.00</div>
            <span class="store">Overclockers UK</span>
            <img src="https://example.com/image3.jpg" />
        </div>
    </body>
    </html>
    """


def test_google_shopping_connector_has_correct_role():
    """Google Shopping should be a marketplace connector."""
    connector = GoogleShoppingConnector()
    assert connector.source_role == SourceType.MARKETPLACE
    assert connector.connector_id == "google_shopping"


def test_google_shopping_connector_has_display_name():
    """Connector should have a display name."""
    connector = GoogleShoppingConnector()
    assert connector.display_name == "Google Shopping"


def test_parse_google_shopping_html(sample_google_shopping_html):
    """Parsing Google Shopping HTML should extract listings correctly."""
    connector = GoogleShoppingConnector()
    listings = connector._parse_search_results(sample_google_shopping_html)

    assert len(listings) == 3

    # First listing
    listing1 = listings[0]
    assert listing1.title_raw == "AMD Ryzen 9 5950X Processor"
    assert listing1.price == Decimal("549.99")
    assert listing1.currency == "GBP"
    assert listing1.seller_or_store == "Amazon UK"
    assert listing1.in_stock is True
    assert listing1.image_url == "https://example.com/image1.jpg"
    assert listing1.source == "google_shopping"
    assert listing1.source_type == SourceType.MARKETPLACE

    # Second listing
    listing2 = listings[1]
    assert listing2.title_raw == "AMD Ryzen 9 5950X 16-Core CPU"
    assert listing2.price == Decimal("599.99")
    assert listing2.seller_or_store == "Ebuyer"
    assert listing2.in_stock is False

    # Third listing
    listing3 = listings[2]
    assert listing3.title_raw == "Ryzen 9 5950X Desktop Processor"
    assert listing3.price == Decimal("579.00")
    assert listing3.seller_or_store == "Overclockers UK"
    assert listing3.in_stock is True  # Default when no stock info


def test_parse_handles_missing_price():
    """Parsing should handle cards without price gracefully."""
    html = """
    <html>
    <body>
        <div class="sh-dgr__content">
            <h3>Product without price</h3>
            <a href="/product?id=no-price">View Product</a>
            <div class="seller">Some Store</div>
        </div>
    </body>
    </html>
    """
    connector = GoogleShoppingConnector()
    listings = connector._parse_search_results(html)

    assert len(listings) == 1
    assert listings[0].price is None


def test_parse_handles_missing_title():
    """Parsing should skip cards without title."""
    html = """
    <html>
    <body>
        <div class="sh-dgr__content">
            <a href="/product?id=no-title">View Product</a>
            <span class="price">£100.00</span>
        </div>
    </body>
    </html>
    """
    connector = GoogleShoppingConnector()
    listings = connector._parse_search_results(html)

    assert len(listings) == 0


def test_parse_generates_stable_listing_ids():
    """Listing IDs should be stable across parses of the same HTML."""
    html = """
    <html>
    <body>
        <div class="sh-dgr__content">
            <h3>Test Product</h3>
            <a href="/product?id=test123">View Product</a>
        </div>
    </body>
    </html>
    """
    connector = GoogleShoppingConnector()
    listings1 = connector._parse_search_results(html)
    listings2 = connector._parse_search_results(html)

    assert len(listings1) == len(listings2) == 1
    assert listings1[0].source_listing_id == listings2[0].source_listing_id


def test_parse_normalizes_relative_urls():
    """Relative URLs should be converted to absolute URLs."""
    html = """
    <html>
    <body>
        <div class="sh-dgr__content">
            <h3>Test Product</h3>
            <a href="/product?id=relative">View Product</a>
        </div>
        <div class="sh-dgr__content">
            <h3>Test Product 2</h3>
            <a href="https://example.com/absolute">View Product</a>
        </div>
    </body>
    </html>
    """
    connector = GoogleShoppingConnector()
    listings = connector._parse_search_results(html)

    assert len(listings) == 2
    assert listings[0].url.startswith("https://shopping.google.com")
    assert listings[0].url.endswith("/product?id=relative")
    assert listings[1].url == "https://example.com/absolute"


def test_parse_detects_availability():
    """Parser should detect stock availability from text."""
    html = """
    <html>
    <body>
        <div class="sh-dgr__content">
            <h3>Product 1</h3>
            <a href="/product?id=1">View</a>
            <div>Out of Stock</div>
        </div>
        <div class="sh-dgr__content">
            <h3>Product 2</h3>
            <a href="/product?id=2">View</a>
            <div>Unavailable</div>
        </div>
        <div class="sh-dgr__content">
            <h3>Product 3</h3>
            <a href="/product?id=3">View</a>
            <div>In Stock</div>
        </div>
    </body>
    </html>
    """
    connector = GoogleShoppingConnector()
    listings = connector._parse_search_results(html)

    assert len(listings) == 3
    assert listings[0].in_stock is False
    assert listings[1].in_stock is False
    assert listings[2].in_stock is True


@pytest.mark.asyncio
async def test_initialize_creates_browser_client():
    """Initialize should create a browser client."""
    connector = GoogleShoppingConnector()

    # Note: This test may fail if Playwright is not installed
    # It's mainly to check that the code path is correct
    try:
        await connector.initialize()
        assert connector.browser_client is not None
        await connector.cleanup()
    except Exception as e:
        # Expected if Playwright not installed or no browser available
        pytest.skip(f"Browser not available: {e}")
