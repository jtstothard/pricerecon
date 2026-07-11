from __future__ import annotations

from decimal import Decimal

import httpx
import pytest
from httpx import ASGITransport, AsyncClient, Request, Response

from pricerecon.connectors.flaresolverr import FlareSolverrClient
from pricerecon.connectors.html import SelectorConfig, parse_listings_from_html
from pricerecon.connectors.reddit import RedditBapcSalesUKConnector, RedditHardwareSwapUKConnector
from pricerecon.connectors.shopify import ShopifyConnector
from pricerecon.connectors.specs import extract_specs
from pricerecon.models import SourceType


@pytest.mark.asyncio
async def test_flaresolverr_client_posts_expected_payload(monkeypatch):
    seen: dict[str, object] = {}

    async def handler(request: Request) -> Response:
        seen["method"] = request.method
        seen["url"] = str(request.url)
        seen["json"] = request.read().decode()
        return Response(200, json={"solution": {"response": "<html><body>ok</body></html>"}})

    transport = httpx.MockTransport(handler)

    class DummyClient(httpx.AsyncClient):
        def __init__(self, *args, **kwargs):
            super().__init__(transport=transport, timeout=kwargs.get("timeout", 90.0))

    monkeypatch.setattr(httpx, "AsyncClient", DummyClient)
    html = await FlareSolverrClient("http://example.test/v1").request_html("https://example.com/search?q=rtx")
    assert html == "<html><body>ok</body></html>"
    assert seen["method"] == "POST"
    assert seen["url"] == "http://example.test/v1"


def test_spec_extraction_covers_common_parts():
    gpu = extract_specs("MSI NVIDIA GeForce RTX 4090 24GB Gaming X", "gpu")
    assert gpu["gpu_model"] == "RTX 4090"
    assert gpu["ram_gb"] == 24
    cpu = extract_specs("AMD Ryzen 7 7800X3D", "cpu")
    assert cpu["cpu_vendor"] == "AMD"
    assert "7800X3D" in cpu["cpu_model"]


def test_html_parser_normalizes_cards():
    html = """
    <html><body>
      <article class='product-card'>
        <a href='/p/1'><h3>RTX 4070 Ti 12GB</h3></a>
        <span class='price'>£599.99</span>
        <div class='availability'>In stock</div>
        <img src='/img/1.jpg' />
      </article>
    </body></html>
    """
    listings = parse_listings_from_html(
        html,
        base_url='https://example.com',
        source='scan',
        source_type=SourceType.RETAILER,
        selector=SelectorConfig(card='article.product-card', title='h3', price='.price', url='a', stock='.availability', image='img'),
        category='gpu',
    )
    assert len(listings) == 1
    listing = listings[0]
    assert listing.url == 'https://example.com/p/1'
    assert listing.price == Decimal('599.99')
    assert listing.in_stock is True
    assert listing.variant_normalized is not None
    assert listing.variant_normalized['gpu_model'] == 'RTX 4070'


@pytest.mark.asyncio
async def test_reddit_oauth_search_maps_json_payload_to_listings():
    calls: list[str] = []

    async def handler(request: Request) -> Response:
        calls.append(str(request.url))
        assert request.headers["Authorization"] == "Bearer test-token"
        assert request.headers["User-Agent"] == "PriceRecon/0.1"
        if str(request.url).endswith('/r/hardwareswapuk/search?q=RTX+4070&sort=new&limit=2&restrict_sr=1'):
            return Response(
                200,
                json={
                    'data': {
                        'children': [
                            {
                                'data': {
                                    'id': 'abc123',
                                    'title': '[H] RTX 4070 [W] £450',
                                    'selftext': 'Condition: used good | Location: London',
                                    'author': 'seller1',
                                    'permalink': '/r/hardwareswapuk/comments/abc123/rtx_4070/',
                                    'created_utc': 1710000000,
                                }
                            }
                        ]
                    }
                },
            )
        raise AssertionError(f'unexpected url {request.url}')

    transport = httpx.MockTransport(handler)
    connector = RedditHardwareSwapUKConnector(access_token='test-token')
    connector._client = httpx.AsyncClient(transport=transport, timeout=30.0)
    listings = await connector.search('RTX 4070', {'limit': 2})
    await connector.cleanup()
    assert len(calls) == 1
    assert len(listings) == 1
    listing = listings[0]
    assert listing.source == 'reddit_hardwareswapuk'
    assert listing.source_type == SourceType.MARKETPLACE
    assert listing.price == Decimal('450')
    assert listing.currency == 'GBP'
    assert listing.url.endswith('/comments/abc123/rtx_4070/')
    assert listing.seller_or_store == 'seller1'
    assert listing.location == 'London'
    assert listing.source_listing_id == 'abc123'


@pytest.mark.asyncio
async def test_reddit_rss_fallback_search_uses_feed_entries():
    calls: list[str] = []

    async def handler(request: Request) -> Response:
        calls.append(str(request.url))
        if str(request.url).endswith('/r/bapcsalesuk/search.rss?q=RTX+4070&sort=new&limit=2&restrict_sr=1'):
            return Response(
                200,
                text='''
                <rss><channel>
                  <item>
                    <title>RTX 4070 at £399</title>
                    <link>https://www.reddit.com/r/bapcsalesuk/comments/xyz789/</link>
                    <author>dealsbot</author>
                    <description>Deal alert</description>
                    <guid>xyz789</guid>
                  </item>
                </channel></rss>
                ''',
            )
        raise AssertionError(f'unexpected url {request.url}')

    transport = httpx.MockTransport(handler)
    connector = RedditBapcSalesUKConnector()
    connector._client = httpx.AsyncClient(transport=transport, timeout=30.0)
    listings = await connector.search('RTX 4070', {'limit': 2})
    await connector.cleanup()
    assert len(calls) == 1
    assert len(listings) == 1
    assert listings[0].source == 'reddit_bapcsalesuk'
    assert listings[0].source_type == SourceType.SIGNAL
    assert listings[0].in_stock is None
    assert listings[0].price == Decimal('399')


@pytest.mark.asyncio
async def test_shopify_connector_fetches_products_and_variants():
    calls: list[str] = []

    async def handler(request: Request) -> Response:
        calls.append(str(request.url))
        if str(request.url).endswith('/search?q=RTX+4070&type=product'):
            return Response(200, text='<html><body>Shopify</body></html>', headers={'X-ShopId': '123'})
        if str(request.url).endswith('/products.json?limit=250'):
            return Response(
                200,
                json={
                    'products': [
                        {
                            'handle': 'rtx-4070',
                            'title': 'RTX 4070 Ti',
                            'product_type': 'gpu',
                            'image': {'src': '/img.jpg'},
                            'variants': [{'id': 1, 'title': 'Base', 'price': '599.99', 'available': True}],
                        }
                    ]
                },
            )
        raise AssertionError(f'unexpected url {request.url}')

    transport = httpx.MockTransport(handler)
    connector = ShopifyConnector(base_url='https://shop.example')
    connector._client = httpx.AsyncClient(transport=transport, timeout=30.0)
    listings = await connector.search('RTX 4070')
    await connector.cleanup()
    assert calls[0].endswith('/search?q=RTX+4070&type=product')
    assert calls[1].endswith('/products.json?limit=250')
    assert len(listings) == 1
    assert listings[0].price == Decimal('599.99')
    assert listings[0].source == 'shopify'
