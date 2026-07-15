"""Tests for Vinted connector."""

import pytest

from pricerecon.connectors.vinted import VintedConnector
from pricerecon.models import SourceType, Condition


@pytest.fixture
def sample_vinted_html():
    """Sample HTML from Vinted search results."""
    return """
    <html>
        <body>
            <div class="item-card">
                <a href="/item/12345">
                    <span class="title">MacBook Pro 13-inch</span>
                    <span class="price">£899.99</span>
                </a>
            </div>
            <div class="item-card">
                <a href="/item/67890">
                    <span class="title">iPhone 12 64GB</span>
                    <span class="price">£449.00</span>
                </a>
            </div>
        </body>
    </html>
    """


def test_vinted_connector_has_correct_role():
    """Vinted should be a marketplace connector."""
    connector = VintedConnector()
    assert connector.source_role == SourceType.MARKETPLACE
    assert connector.connector_id == "vinted"


def test_vinted_html_parsing(sample_vinted_html):
    """Vinted HTML parsing should extract listings correctly."""
    connector = VintedConnector()
    listings = connector._parse_search_results(sample_vinted_html)

    assert len(listings) == 2
    assert listings[0].title_raw == "MacBook Pro 13-inch"
    assert listings[0].source_listing_id == "12345"
    assert listings[0].currency == "GBP"
    assert listings[1].title_raw == "iPhone 12 64GB"
    assert listings[1].source_listing_id == "67890"


def test_vinted_condition_parsing_new():
    """New condition should be detected."""
    connector = VintedConnector()
    mock_html = """
    <html>
        <body>
            <div class="item-card">
                <a href="/item/1">
                    <span class="title">Test Item brand new</span>
                    <span class="price">£100.00</span>
                </a>
            </div>
        </body>
    </html>
    """
    listings = connector._parse_search_results(mock_html)
    assert len(listings) == 1
    assert listings[0].condition == Condition.NEW


def test_vinted_condition_parsing_like_new():
    """Like new condition should be detected."""
    connector = VintedConnector()
    mock_html = """
    <html>
        <body>
            <div class="item-card">
                <a href="/item/1">
                    <span class="title">Test Item like new</span>
                    <span class="price">£100.00</span>
                </a>
            </div>
        </body>
    </html>
    """
    listings = connector._parse_search_results(mock_html)
    assert len(listings) == 1
    assert listings[0].condition == Condition.USED_LIKE_NEW


def test_vinted_condition_parsing_good():
    """Good condition should be detected."""
    connector = VintedConnector()
    mock_html = """
    <html>
        <body>
            <div class="item-card">
                <a href="/item/1">
                    <span class="title">Test Item good</span>
                    <span class="price">£100.00</span>
                </a>
            </div>
        </body>
    </html>
    """
    listings = connector._parse_search_results(mock_html)
    assert len(listings) == 1
    assert listings[0].condition == Condition.USED_GOOD


def test_vinted_deduplication():
    """Duplicate listings should be removed."""
    connector = VintedConnector()
    mock_html = """
    <html>
        <body>
            <div class="item-card">
                <a href="/item/12345">
                    <span class="title">MacBook Pro</span>
                    <span class="price">£899.99</span>
                </a>
            </div>
            <div class="item-card">
                <a href="/item/12345">
                    <span class="title">MacBook Pro</span>
                    <span class="price">£899.99</span>
                </a>
            </div>
        </body>
    </html>
    """
    listings = connector._parse_search_results(mock_html)
    assert len(listings) == 1, f"Expected 1 deduplicated listing, got {len(listings)}"
