"""Tests for Costco UK connector."""

import pytest
from pricerecon.connectors.costco_uk import CostcoUKConnector
from pricerecon.models import SourceType
from pricerecon.connectors.status import ConnectorDegradedError, ConnectorStatus


def test_connector_id():
    """Test connector ID is set correctly."""
    connector = CostcoUKConnector()
    assert connector.connector_id == "costco_uk"


def test_source_role():
    """Test source role is retailer."""
    connector = CostcoUKConnector()
    assert connector.source_role == SourceType.RETAILER


def test_display_name():
    """Test display name."""
    connector = CostcoUKConnector()
    assert connector.display_name == "Costco UK"


def test_auth_not_configured():
    """Test connector degrades gracefully without auth."""
    connector = CostcoUKConnector()
    assert not connector.auth_configured


def test_parse_product_links():
    """Test parsing product links from HTML."""
    connector = CostcoUKConnector()

    html = """
    <html>
    <body>
        <div class="product-card">
            <a href="/p/123456">Test Laptop</a>
            <span class="price">£899.99</span>
            <img src="//cdn.costco.co.uk/product.jpg" />
        </div>
        <div class="product-card">
            <a href="/p/789012">Test MacBook</a>
            <span class="price">£1299.00</span>
            <img src="//cdn.costco.co.uk/macbook.jpg" />
        </div>
    </body>
    </html>
    """

    listings = connector._parse_search_results(html)

    assert len(listings) == 2

    # First listing
    assert listings[0].source_listing_id == "123456"
    assert listings[0].title_raw == "Test Laptop"
    assert listings[0].price is not None
    assert float(listings[0].price) == 899.99
    assert listings[0].currency == "GBP"
    assert listings[0].url == "https://www.costco.co.uk/p/123456"
    assert listings[0].image_url == "https://cdn.costco.co.uk/product.jpg"
    assert listings[0].seller_or_store == "Costco UK"
    assert listings[0].in_stock is True

    # Second listing
    assert listings[1].source_listing_id == "789012"
    assert listings[1].title_raw == "Test MacBook"
    assert listings[1].price is not None
    assert float(listings[1].price) == 1299.00
    assert listings[1].currency == "GBP"
    assert listings[1].url == "https://www.costco.co.uk/p/789012"


def test_parse_with_stock_status():
    """Test parsing with out-of-stock items."""
    connector = CostcoUKConnector()

    html = """
    <html>
    <body>
        <div class="product-card">
            <a href="/p/123456">Test Laptop</a>
            <span class="price">£899.99</span>
            <span class="stock">Out of stock</span>
        </div>
        <div class="product-card">
            <a href="/p/789012">Test MacBook</a>
            <span class="price">£1299.00</span>
        </div>
    </body>
    </html>
    """

    listings = connector._parse_search_results(html)

    assert len(listings) == 2
    assert listings[0].in_stock is False
    assert listings[1].in_stock is True


def test_deduplicates_by_id():
    """Test that duplicate product IDs are removed."""
    connector = CostcoUKConnector()

    html = """
    <html>
    <body>
        <div class="product-card">
            <a href="/p/123456">Test Laptop</a>
            <span class="price">£899.99</span>
        </div>
        <div class="product-card">
            <a href="/p/123456">Test Laptop Duplicate</a>
            <span class="price">£899.99</span>
        </div>
        <div class="product-card">
            <a href="/p/789012">Test MacBook</a>
            <span class="price">£1299.00</span>
        </div>
    </body>
    </html>
    """

    listings = connector._parse_search_results(html)

    # Should deduplicate the duplicate 123456 entry
    assert len(listings) == 2
    assert listings[0].source_listing_id == "123456"
    assert listings[1].source_listing_id == "789012"


@pytest.mark.asyncio
async def test_search_without_auth_raises_degraded():
    """Test that search without auth raises ConnectorDegradedError."""
    connector = CostcoUKConnector()

    with pytest.raises(ConnectorDegradedError) as exc_info:
        await connector.search("laptop")

    assert exc_info.value.status == ConnectorStatus.auth_failed
    assert "COSTCO_SESSION_COOKIE" in str(exc_info.value.message)


def test_price_extraction_patterns():
    """Test various price extraction patterns."""
    connector = CostcoUKConnector()

    test_cases = [
        ("£899.99", 899.99),
        ("£1299", 1299.00),
        ("£1,299.00", 1299.00),
    ]

    for price_text, expected_value in test_cases:
        html = f"""
        <html>
        <body>
            <div class="product-card">
                <a href="/p/123456">Test Product</a>
                <span class="price">{price_text}</span>
            </div>
        </body>
        </html>
        """

        listings = connector._parse_search_results(html)
        assert len(listings) == 1
        assert listings[0].price is not None
        assert float(listings[0].price) == expected_value


def test_handles_malformed_html():
    """Test that malformed HTML doesn't crash the parser."""
    connector = CostcoUKConnector()

    html = """
    <html>
    <body>
        <div class="product-card">
            <a href="/p/123456">Test Laptop</a>
        </div>
        <div class="product-card">
            <!-- Missing title and price -->
            <a href="/p/789012"></a>
        </div>
        <div class="product-card">
            <a href="/p/111111">Valid Product</a>
            <span class="price">£599.99</span>
        </div>
    </body>
    </html>
    """

    listings = connector._parse_search_results(html)

    # Should skip malformed entries but keep valid ones
    assert len(listings) >= 1
    # Check that at least the valid product is included
    valid_listing = next((item for item in listings if item.source_listing_id == "111111"), None)
    assert valid_listing is not None
    assert valid_listing.price is not None
    assert float(valid_listing.price) == 599.99


@pytest.mark.asyncio
async def test_initialization_without_auth():
    """Test initialization works without auth (degraded mode)."""
    connector = CostcoUKConnector()
    await connector.initialize()

    # Should not raise an error
    assert connector.auth_configured is False

    await connector.cleanup()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
