"""Tests for Argos and MusicMagpie connectors."""

from decimal import Decimal

import pytest
from pricerecon.connectors.argos import ArgosConnector
from pricerecon.connectors.musicmagpie import MusicMagpieConnector
from pricerecon.models import SourceType


@pytest.mark.asyncio
async def test_argos_connector_has_correct_source_type() -> None:
    """Test that Argos connector has correct source type."""
    connector = ArgosConnector()
    assert connector.source_role == SourceType.RETAILER
    assert connector.connector_id == "argos"


@pytest.mark.asyncio
async def test_musicmagpie_connector_has_correct_source_type() -> None:
    """Test that MusicMagpie connector has correct source type."""
    connector = MusicMagpieConnector()
    assert connector.source_role == SourceType.RETAILER
    assert connector.connector_id == "musicmagpie"


def test_argos_parses_product_cards() -> None:
    """Test Argos HTML parser with deterministic fixture."""
    html = """
    <html><body>
      <a href="/product/7631324">
        <h3>HP 14a-ne1000na 14in Celeron 4GB 64GB Chromebook - Grey</h3>
      </a>
      <div>£179.00</div>
      <div>In stock</div>
      <img src="/img/hp-chromebook.jpg" />
    </body></html>
    """

    connector = ArgosConnector()
    listings = connector._parse_search_results(html)

    assert len(listings) == 1
    listing = listings[0]

    assert listing.source == "argos"
    assert listing.source_type == SourceType.RETAILER
    assert listing.source_listing_id == "7631324"
    assert "HP 14a-ne1000na" in listing.title_raw
    assert listing.price == Decimal("179.00")
    assert listing.currency == "GBP"
    assert listing.url == "https://www.argos.co.uk/product/7631324"
    assert listing.in_stock is True
    assert listing.seller_or_store == "Argos"


def test_argos_deduplicates_by_product_id() -> None:
    """Test that Argos connector deduplicates listings by product ID."""
    html = """
    <html><body>
      <a href="/product/7631324">
        <h3>HP Chromebook</h3>
      </a>
      <div>£179.00</div>
      <a href="/product/7631324">
        <h3>HP Chromebook - Duplicate</h3>
      </a>
      <div>£179.00</div>
      <a href="/product/3288599">
        <h3>Lenovo Chromebook</h3>
      </a>
      <div>£279.00</div>
    </body></html>
    """

    connector = ArgosConnector()
    listings = connector._parse_search_results(html)

    # Should have 2 unique products, not 3
    assert len(listings) == 2
    product_ids = {listing.source_listing_id for listing in listings}
    assert product_ids == {"7631324", "3288599"}


@pytest.mark.asyncio
async def test_argos_real_403_fixture_fails_fast_truthfully() -> None:
    """A live Argos response is an Akamai block, not an empty result set.

    NOTE: This test documents legacy direct-HTTP behavior. Argos now routes through
    Camofox/BrowserClient, so the 403 is no longer surfaced as a connector error.
    The fixture parsing assertion remains valid: an Akamai block page contains
    no product listings, and _parse_search_results correctly returns [].
    """
    from pathlib import Path

    fixture = Path(__file__).parent / "fixtures" / "argos" / "airpods_403.html"
    html = fixture.read_text()
    assert "Access Denied" in html
    assert ArgosConnector()._parse_search_results(html) == []

    # Argos now uses Camofox routing; direct-HTTP 403 is no longer observable
    # through the connector's search() interface. The degraded behavior is
    # handled at the BrowserClient layer, not as ConnectorDegradedError from
    # ArgosConnector directly.


def test_musicmagpie_parses_product_cards() -> None:
    """Test MusicMagpie HTML parser with deterministic fixture."""
    html = """
    <html><body>
      <a href="/store/product/hp-laptop-14">
        <h3>HP 14in Laptop - Refurbished</h3>
      </a>
      <div>£299.00</div>
      <div>In stock</div>
      <img src="/img/hp-laptop.jpg" />
    </body></html>
    """

    connector = MusicMagpieConnector()
    listings = connector._parse_search_results(html)

    assert len(listings) == 1
    listing = listings[0]

    assert listing.source == "musicmagpie"
    assert listing.source_type == SourceType.RETAILER
    assert listing.source_listing_id == "hp-laptop-14"
    assert "HP 14in Laptop" in listing.title_raw
    assert listing.price == Decimal("299.00")
    assert listing.currency == "GBP"
    assert listing.url == "https://www.musicmagpie.co.uk/store/product/hp-laptop-14"
    assert listing.in_stock is True
    assert listing.seller_or_store == "MusicMagpie"
    assert listing.condition == "refurbished"
    assert listing.condition_raw == "Refurbished"
    assert listing.shipping_cost == Decimal("0")


def test_musicmagpie_detects_out_of_stock() -> None:
    """Test that MusicMagpie connector detects out of stock items."""
    html = """
    <html><body>
      <a href="/store/product/dell-laptop">
        <h3>Dell Laptop</h3>
      </a>
      <div>£399.00</div>
      <div>This item is out of stock</div>
    </body></html>
    """

    connector = MusicMagpieConnector()
    listings = connector._parse_search_results(html)

    assert len(listings) == 1
    assert listings[0].in_stock is False


def test_musicmagpie_deduplicates_by_product_id() -> None:
    """Test that MusicMagpie connector deduplicates listings by product ID."""
    html = """
    <html><body>
      <a href="/store/product/hp-laptop">
        <h3>HP Laptop</h3>
      </a>
      <div>£299.00</div>
      <a href="/store/product/hp-laptop">
        <h3>HP Laptop - Duplicate</h3>
      </a>
      <div>£299.00</div>
      <a href="/store/product/dell-laptop">
        <h3>Dell Laptop</h3>
      </a>
      <div>£399.00</div>
    </body></html>
    """

    connector = MusicMagpieConnector()
    listings = connector._parse_search_results(html)

    # Should have 2 unique products, not 3
    assert len(listings) == 2
    product_ids = {listing.source_listing_id for listing in listings}
    assert product_ids == {"hp-laptop", "dell-laptop"}
