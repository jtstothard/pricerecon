"""Tests for Gumtree connector."""

from decimal import Decimal
import pytest

from pricerecon.connectors.gumtree import GumtreeConnector
from pricerecon.models import SourceType, Condition


@pytest.fixture
def sample_gumtree_html():
    """Sample HTML from Gumtree search results."""
    return """
    <html>
        <body>
            <div class="ad-listing">
                <a href="/details/12345">
                    <h2 class="title">Dell XPS 15 Laptop</h2>
                    <div class="ad-price">£1,200.00</div>
                </a>
            </div>
            <div class="ad-listing">
                <a href="/details/67890">
                    <h2 class="title">HP Spectre x360</h2>
                    <div class="ad-price">£850.00</div>
                </a>
            </div>
        </body>
    </html>
    """


def test_gumtree_connector_has_correct_role():
    """Gumtree should be a marketplace connector."""
    connector = GumtreeConnector()
    assert connector.source_role == SourceType.MARKETPLACE
    assert connector.connector_id == "gumtree"


def test_gumtree_html_parsing(sample_gumtree_html):
    """Gumtree HTML parsing should extract listings correctly."""
    connector = GumtreeConnector()
    listings = connector._parse_search_results(sample_gumtree_html)

    assert len(listings) == 2
    assert listings[0].title_raw == "Dell XPS 15 Laptop"
    assert listings[0].source_listing_id == "12345"
    assert listings[0].currency == "GBP"
    assert listings[1].title_raw == "HP Spectre x360"
    assert listings[1].source_listing_id == "67890"


def test_gumtree_condition_parsing_new():
    """New condition should be detected."""
    connector = GumtreeConnector()
    mock_html = """
    <html>
        <body>
            <div class="ad-listing">
                <a href="/details/1">
                    <h2 class="title">Test Item brand new</h2>
                    <div class="ad-price">£100.00</div>
                </a>
            </div>
        </body>
    </html>
    """
    listings = connector._parse_search_results(mock_html)
    assert len(listings) == 1
    assert listings[0].condition == Condition.NEW


def test_gumtree_condition_parsing_like_new():
    """Like new condition should be detected."""
    connector = GumtreeConnector()
    mock_html = """
    <html>
        <body>
            <div class="ad-listing">
                <a href="/details/1">
                    <h2 class="title">Test Item excellent condition</h2>
                    <div class="ad-price">£100.00</div>
                </a>
            </div>
        </body>
    </html>
    """
    listings = connector._parse_search_results(mock_html)
    assert len(listings) == 1
    assert listings[0].condition == Condition.USED_LIKE_NEW


def test_gumtree_condition_parsing_good():
    """Good condition should be detected."""
    connector = GumtreeConnector()
    mock_html = """
    <html>
        <body>
            <div class="ad-listing">
                <a href="/details/1">
                    <h2 class="title">Test Item good condition</h2>
                    <div class="ad-price">£100.00</div>
                </a>
            </div>
        </body>
    </html>
    """
    listings = connector._parse_search_results(mock_html)
    assert len(listings) == 1
    assert listings[0].condition == Condition.USED_GOOD


def test_gumtree_deduplication():
    """Duplicate listings should be removed."""
    connector = GumtreeConnector()
    mock_html = """
    <html>
        <body>
            <div class="ad-listing">
                <a href="/details/12345">
                    <h2 class="title">Dell XPS 15</h2>
                    <div class="ad-price">£1,200.00</div>
                </a>
            </div>
            <div class="ad-listing">
                <a href="/details/12345">
                    <h2 class="title">Dell XPS 15</h2>
                    <div class="ad-price">£1,200.00</div>
                </a>
            </div>
        </body>
    </html>
    """
    listings = connector._parse_search_results(mock_html)
    assert len(listings) == 1, f"Expected 1 deduplicated listing, got {len(listings)}"