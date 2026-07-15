"""Tests for EE Gaming connector."""

from decimal import Decimal
import pytest

from pricerecon.connectors.ee_gaming import EEGamingConnector
from pricerecon.models import SourceType


@pytest.fixture
def sample_ee_gaming_html():
    """Sample HTML from EE Gaming search results."""
    return """
    <html>
    <body>
        <a href="/products/ps5-console-bundle">
            <h3>PlayStation 5 Console Bundle</h3>
            <img src="https://ee.co.uk/images/ps5.jpg" />
            <span>£629.98</span>
        </a>
        <a href="/products/xbox-series-x">
            <h4>Xbox Series X</h4>
            <div>£479.99</div>
            <img src="https://ee.co.uk/images/xbox.jpg" />
        </a>
        <a href="/products/gaming-pc">
            <h2>PCSpecialist Gaming PC</h2>
            <span>£949.00</span>
            <img src="https://ee.co.uk/images/pc.jpg" />
        </a>
        <a href="/products/switch-2-bundle">
            <h3>Nintendo Switch 2 Bundle</h3>
            <div>£34.00</div>
            <img src="https://ee.co.uk/images/switch.jpg" />
        </a>
        <a href="/gaming/categories/consoles">
            <h3>Consoles Category Page</h3>
            <span>No price</span>
        </a>
    </body>
    </html>
    """


def test_ee_gaming_connector_has_correct_role():
    """EE Gaming should be a retailer connector."""
    connector = EEGamingConnector()
    assert connector.source_role == SourceType.RETAILER
    assert connector.connector_id == "ee_gaming"


def test_ee_gaming_connector_has_display_name():
    """Connector should have a display name."""
    connector = EEGamingConnector()
    assert connector.display_name == "EE Gaming"


def test_parse_ee_gaming_html(sample_ee_gaming_html):
    """Parsing EE Gaming HTML should extract listings correctly."""
    connector = EEGamingConnector()
    listings = connector._parse_search_results(sample_ee_gaming_html)

    # Should find gaming products (not category pages)
    assert len(listings) == 4

    # First listing
    listing1 = listings[0]
    assert listing1.title_raw == "PlayStation 5 Console Bundle"
    assert listing1.price == Decimal("629.98")
    assert listing1.currency == "GBP"
    assert listing1.seller_or_store == "EE Gaming"
    assert listing1.in_stock is True
    assert listing1.image_url == "https://ee.co.uk/images/ps5.jpg"
    assert listing1.source == "ee_gaming"
    assert listing1.source_type == SourceType.RETAILER
    assert "products" in listing1.url

    # Second listing
    listing2 = listings[1]
    assert listing2.title_raw == "Xbox Series X"
    assert listing2.price == Decimal("479.99")
    assert "products" in listing2.url

    # Third listing
    listing3 = listings[2]
    assert listing3.title_raw == "PCSpecialist Gaming PC"
    assert listing3.price == Decimal("949.00")

    # Fourth listing
    listing4 = listings[3]
    assert listing4.title_raw == "Nintendo Switch 2 Bundle"
    assert listing4.price == Decimal("34.00")


def test_parse_handles_missing_price():
    """Parsing should handle cards without price gracefully."""
    html = """
    <html>
    <body>
        <a href="/products/some-product">
            <h3>Product without price</h3>
            <img src="https://ee.co.uk/images/product.jpg" />
        </a>
    </body>
    </html>
    """
    connector = EEGamingConnector()
    listings = connector._parse_search_results(html)

    assert len(listings) == 1
    assert listings[0].price is None


def test_parse_filters_non_product_pages():
    """Parsing should filter out non-product links."""
    html = """
    <html>
    <body>
        <a href="/help">Help page</a>
        <a href="/manage">Manage page</a>
        <a href="/products/ps5-game">
            <h3>PS5 Game</h3>
            <span>£59.99</span>
        </a>
    </body>
    </html>
    """
    connector = EEGamingConnector()
    listings = connector._parse_search_results(html)

    assert len(listings) == 1
    assert listings[0].title_raw == "PS5 Game"


def test_parse_handles_currency_symbols():
    """Parsing should handle various GBP currency formats."""
    html = """
    <html>
    <body>
        <a href="/products/game1">
            <h3>Game 1</h3>
            <span>£49.99</span>
        </a>
        <a href="/products/game2">
            <h3>Game 2</h3>
            <div>£ 59.99</div>
        </a>
        <a href="/products/game3">
            <h3>Game 3</h3>
            <strong>£69.99</strong>
        </a>
    </body>
    </html>
    """
    connector = EEGamingConnector()
    listings = connector._parse_search_results(html)

    assert len(listings) == 3
    assert listings[0].price == Decimal("49.99")
    assert listings[1].price == Decimal("59.99")
    assert listings[2].price == Decimal("69.99")
