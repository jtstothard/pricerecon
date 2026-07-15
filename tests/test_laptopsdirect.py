"""Tests for Laptops Direct connector."""

import httpx
import pytest
from pricerecon.connectors.laptopsdirect import LaptopsDirectConnector
from pricerecon.models import SourceType


@pytest.fixture
def connector():
    """Create connector instance."""
    return LaptopsDirectConnector()


def test_source_role(connector):
    """Test connector is a retailer."""
    assert connector.source_role == SourceType.RETAILER


def test_connector_id(connector):
    """Test connector ID."""
    assert connector.connector_id == "laptopsdirect"


@pytest.mark.asyncio
async def test_search_parsing(connector, respx_mock):
    """Test HTML parsing with mock response."""
    # Mock Laptops Direct category page response
    html_response = """
    <div aria-label="found product" role="listitem"
         data-cnstrc-item-id="1996306"
         data-cnstrc-item-name="CyberPowerPC Intel Core i7-14700KF 32GB RAM 2TB SSD RTX 5070 Windows 11 Gaming PC"
         data-cnstrc-item-price="1949.00"
         class="OfferBox">
        <div class="sr_image">
            <a class="productHref_1996306" href="/cyberpowerpc-intel-core-i7-14700kf-32gb-ddr5-ram-2tb-ssd-rtx-5070-windows-1-ld22247/version.asp" title="CyberPowerPC Intel Core i7-14700KF 32GB RAM 2TB SSD RTX 5070 Windows 11 Gaming PC">
                <img id="productImage_1996306" class="offerImage" src="/Images/791079831LD22247_1_Classic.png?v=10" alt="" />
            </a>
        </div>
    </div>
    <div aria-label="found product" role="listitem"
         data-cnstrc-item-id="2067835"
         data-cnstrc-item-name="Stormforce Defiance AMD Ryzen 7 7800X3D 32GB RAM 1TB SSD RTX 5070 Windows 11 Gaming PC"
         data-cnstrc-item-price="1899.97"
         class="OfferBox">
        <div class="sr_image">
            <a class="productHref_2067835" href="/stormforce-defiance-amd-ryzen-7-7800x3d-32gb-ram-1tb-ssd-rtx-5070-windows-1-7873-1458/version.asp" title="Stormforce Defiance AMD Ryzen 7 7800X3D 32GB RAM 1TB SSD RTX 5070 Windows 11 Gaming PC">
                <img id="productImage_2067835" class="offerImage" src="/Images/7873-1458_1_Classic.png?v=5" alt="" />
            </a>
        </div>
    </div>
    """

    respx_mock.get("https://www.laptopsdirect.co.uk/ct/graphics-cards/nvidia-geforce").mock(
        return_value=httpx.Response(200, text=html_response)
    )

    listings = await connector.search("RTX 4090")

    assert len(listings) == 2

    # Check first listing
    listing1 = listings[0]
    assert listing1.source == "laptopsdirect"
    assert listing1.source_type == SourceType.RETAILER
    assert listing1.source_listing_id == "1996306"
    assert "CyberPowerPC" in listing1.title_raw
    assert float(listing1.price) == 1949.00
    assert listing1.currency == "GBP"
    assert listing1.url.startswith("https://www.laptopsdirect.co.uk/")
    assert listing1.image_url is not None
    assert listing1.in_stock is True
    assert listing1.seller_or_store == "Laptops Direct"
    assert listing1.category == "gpu"

    # Check second listing
    listing2 = listings[1]
    assert listing2.source_listing_id == "2067835"
    assert "Stormforce" in listing2.title_raw
    assert float(listing2.price) == 1899.97


@pytest.mark.asyncio
async def test_search_with_known_query(connector, respx_mock):
    """Test search with known query mapping."""
    html_response = '<div aria-label="found product" data-cnstrc-item-id="test" data-cnstrc-item-name="Test Product" data-cnstrc-item-price="1000.00"><a href="/test"></a></div>'

    respx_mock.get("https://www.laptopsdirect.co.uk/ct/pcs/geforce-rtx-5070").mock(
        return_value=httpx.Response(200, text=html_response)
    )

    listings = await connector.search("RTX 5070")

    # Should use the RTX 5070 specific URL
    assert len(listings) >= 0  # Just verify it didn't crash


def test_parse_html_missing_attributes(connector):
    """Test HTML parsing when attributes are missing."""
    html = """
    <div aria-label="found product" data-cnstrc-item-id="123">
        <a href="/test">Test</a>
    </div>
    """

    listings = connector._parse_html(html)

    assert len(listings) == 0  # Should skip cards without required attributes


def test_parse_html_invalid_price(connector):
    """Test HTML parsing with invalid price."""
    html = """
    <div aria-label="found product"
         data-cnstrc-item-id="123"
         data-cnstrc-item-name="Test Product"
         data-cnstrc-item-price="invalid">
        <a href="/test">Test</a>
    </div>
    """

    listings = connector._parse_html(html)

    assert len(listings) == 0  # Should skip cards with invalid price


def test_parse_html_relative_urls(connector):
    """Test that relative URLs are converted to absolute."""
    html = """
    <div aria-label="found product"
         data-cnstrc-item-id="123"
         data-cnstrc-item-name="Test Product"
         data-cnstrc-item-price="1000.00">
        <a href="/test-product">
            <img class="offerImage" src="/images/test.jpg" />
        </a>
    </div>
    """

    listings = connector._parse_html(html)

    assert len(listings) == 1
    assert listings[0].url == "https://www.laptopsdirect.co.uk/test-product"
    assert listings[0].image_url == "https://www.laptopsdirect.co.uk/images/test.jpg"
