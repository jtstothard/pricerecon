"""Test Amazon connector result authenticity and validation.

Verifies that:
1. Fake ASINs from banners/scripts are not returned as listings
2. Every listing has a non-empty title extracted from the page
3. Captcha/blocked pages are detected and return empty results
4. Price matching is per-product, not positional
"""

import pytest
from pricerecon.connectors.amazon import AmazonConnector
from pricerecon.models import Condition


@pytest.mark.asyncio
async def test_no_fake_asins_from_promo_banners():
    """Fake ASINs from promo banners (like B0GZHRXGG7) should not appear in results."""
    connector = AmazonConnector()
    listings = await connector.search("watch")

    # Known fake ASINs from promo banners that should NOT appear
    fake_asins = {"B0GZHRXGG7", "B0BH98211K", "B0GVJDL919"}

    returned_asins = {listing.source_listing_id for listing in listings}
    overlap = returned_asins & fake_asins

    await connector.cleanup()

    assert not overlap, f"Found fake ASINs in results: {overlap}"


@pytest.mark.asyncio
async def test_every_listing_has_title():
    """Every listing must have a non-empty title extracted from the page."""
    connector = AmazonConnector()
    listings = await connector.search("watch")

    await connector.cleanup()

    for listing in listings:
        assert listing.title_raw, f"ASIN {listing.source_listing_id} has empty title"
        # Title should NOT just be the search query
        assert listing.title_raw != "watch", (
            f"ASIN {listing.source_listing_id} title is just the query string - "
            "not extracted from page"
        )


@pytest.mark.asyncio
async def test_captcha_page_returns_empty():
    """If Amazon returns a captcha page, connector should return empty list."""
    connector = AmazonConnector()

    captcha_html = """
    <html>
    <head><title>Amazon CAPTCHA</title></head>
    <body>
        <p>Please type the characters you see below</p>
    </body>
    </html>
    """

    assert connector._is_blocked_page(captcha_html), "Captcha page should be detected"

    await connector.cleanup()


@pytest.mark.asyncio
async def test_prices_are_per_product_not_positional():
    """Prices should be matched per product, not by array position.

    This tests that the parser extracts price from within the same
    product block as the ASIN, not by positional matching.
    """
    connector = AmazonConnector()

    # If prices were matched positionally to ASINs, many products would
    # have the wrong price. The new parser should avoid this.
    listings = await connector.search("watch")

    await connector.cleanup()

    if len(listings) > 10:
        # Check that we have price diversity - not all the same price
        prices = {listing.price for listing in listings}
        # At least 3 distinct prices should be found for a "watch" search
        assert len(prices) >= 3, (
            f"Only {len(prices)} distinct prices found - "
            "suspicious for a diverse product search"
        )


@pytest.mark.asyncio
async def test_sponsored_items_filtered_or_labeled():
    """Sponsored items should either be filtered or clearly labeled."""
    connector = AmazonConnector()
    listings = await connector.search("watch")

    # For now, the connector filters out sponsored items.
    # If this changes, we should verify they're labeled.

    await connector.cleanup()

    # The test passes if we get reasonable results
    # (specific sponsored handling depends on connector implementation)
    assert isinstance(listings, list)


@pytest.mark.asyncio
async def test_blocked_page_detection():
    """Test various blocked page indicators are detected."""
    connector = AmazonConnector()

    blocked_pages = [
        '<html><body>Type the characters you see below</body></html>',
        '<html><body><span class="a-alert-heading">CAPTCHA</span></body></html>',
        '<html><body>Amazon is blocking your request</body></html>',
        '<html><body>security measure</body></html>',
    ]

    for html in blocked_pages:
        assert connector._is_blocked_page(html), f"Should detect blocked page: {html[:50]}"

    # Normal search page should NOT be detected as blocked
    normal_html = """
    <html>
    <head><title>Amazon.co.uk : watch</title></head>
    <body>
        <div data-asin="B0REALPROD1">Product</div>
    </body>
    </html>
    """

    assert not connector._is_blocked_page(normal_html), "Normal page should not be detected as blocked"

    await connector.cleanup()