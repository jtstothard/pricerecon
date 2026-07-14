"""Tests for GAME Digital connector."""

from decimal import Decimal
import pytest

from pricerecon.connectors.game_digital import GameDigitalConnector
from pricerecon.models import SourceType


@pytest.fixture
def sample_game_digital_html():
    """Sample HTML from GAME Digital search results."""
    return """
    <html>
    <body>
        <a href="/games/ps5-console">
            <h3>PlayStation 5 Console</h3>
            <img src="https://images.game.co.uk/products/ps5.jpg" />
            <div class="price">£479.99</div>
        </a>
        <a href="/tech/xbox-series-x">
            <h4>Xbox Series X</h4>
            <span>£449.99</span>
            <img src="https://images.game.co.uk/products/xbox.jpg" />
        </a>
        <a href="/accessories/controller">
            <h2>DualSense Wireless Controller</h2>
            <div>£59.99</div>
            <img src="https://images.game.co.uk/products/controller.jpg" />
        </a>
        <a href="/games/mario-kart">
            <h3>Mario Kart 8 Deluxe</h3>
            <img src="https://images.game.co.uk/products/mario.jpg" />
            <strong>£49.99</strong>
        </a>
        <a href="/other/page">
            <h3>Non-gaming product</h3>
            <span>£19.99</span>
        </a>
    </body>
    </html>
    """


def test_game_digital_connector_has_correct_role():
    """GAME Digital should be a retailer connector."""
    connector = GameDigitalConnector()
    assert connector.source_role == SourceType.RETAILER
    assert connector.connector_id == "game_digital"


def test_game_digital_connector_has_display_name():
    """Connector should have a display name."""
    connector = GameDigitalConnector()
    assert connector.display_name == "GAME Digital"


def test_parse_game_digital_html(sample_game_digital_html):
    """Parsing GAME Digital HTML should extract listings correctly."""
    connector = GameDigitalConnector()
    listings = connector._parse_search_results(sample_game_digital_html)

    # Should find gaming products (not non-gaming pages)
    assert len(listings) == 4

    # First listing
    listing1 = listings[0]
    assert listing1.title_raw == "PlayStation 5 Console"
    assert listing1.price == Decimal("479.99")
    assert listing1.currency == "GBP"
    assert listing1.seller_or_store == "GAME Digital"
    assert listing1.in_stock is True
    assert listing1.image_url == "https://images.game.co.uk/products/ps5.jpg"
    assert listing1.source == "game_digital"
    assert listing1.source_type == SourceType.RETAILER
    assert "games" in listing1.url

    # Second listing
    listing2 = listings[1]
    assert listing2.title_raw == "Xbox Series X"
    assert listing2.price == Decimal("449.99")
    assert "tech" in listing2.url

    # Third listing
    listing3 = listings[2]
    assert listing3.title_raw == "DualSense Wireless Controller"
    assert listing3.price == Decimal("59.99")

    # Fourth listing
    listing4 = listings[3]
    assert listing4.title_raw == "Mario Kart 8 Deluxe"
    assert listing4.price == Decimal("49.99")


def test_parse_handles_missing_price():
    """Parsing should handle cards without price gracefully."""
    html = """
    <html>
    <body>
        <a href="/games/some-game">
            <h3>Game without price</h3>
            <img src="https://images.game.co.uk/products/game.jpg" />
        </a>
    </body>
    </html>
    """
    connector = GameDigitalConnector()
    listings = connector._parse_search_results(html)

    assert len(listings) == 1
    assert listings[0].price is None


def test_parse_filters_non_gaming_pages():
    """Parsing should filter out non-gaming product links."""
    html = """
    <html>
    <body>
        <a href="/login">Login page</a>
        <a href="/help">Help page</a>
        <a href="/games/ps5-game">
            <h3>PS5 Game</h3>
            <span>£59.99</span>
        </a>
    </body>
    </html>
    """
    connector = GameDigitalConnector()
    listings = connector._parse_search_results(html)

    assert len(listings) == 1
    assert listings[0].title_raw == "PS5 Game"


def test_parse_handles_currency_symbols():
    """Parsing should handle various GBP currency formats."""
    html = """
    <html>
    <body>
        <a href="/games/game1">
            <h3>Game 1</h3>
            <span>£49.99</span>
        </a>
        <a href="/games/game2">
            <h3>Game 2</h3>
            <div>£ 59.99</div>
        </a>
        <a href="/games/game3">
            <h3>Game 3</h3>
            <strong>£69.99</strong>
        </a>
    </body>
    </html>
    """
    connector = GameDigitalConnector()
    listings = connector._parse_search_results(html)

    assert len(listings) == 3
    assert listings[0].price == Decimal("49.99")
    assert listings[1].price == Decimal("59.99")
    assert listings[2].price == Decimal("69.99")