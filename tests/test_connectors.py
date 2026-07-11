from __future__ import annotations

from decimal import Decimal

import httpx
import pytest
from httpx import ASGITransport, AsyncClient, Request, Response

from pricerecon.connectors.flaresolverr import FlareSolverrClient
from pricerecon.connectors.html import SelectorConfig, parse_listings_from_html
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
async def test_ebuyer_connector_parses_live_search_markup():
    html = """
    <div class='card text-center rounded-0 h-100 bg-vdarkgrey'>
      <div class='card-body d-flex flex-column'>
        <a href='/asus-dual-geforce-rtx-5070-12gb-gddr7-oc-edition-705967#colcode=70596799' class='stretched-link'></a>
        <img src='https://example.test/img.jpg' alt='ASUS - Dual GeForce RTX 5070 12GB GDDR7 OC Edition'>
        <p class='card-link fw-bold mb-2'>ASUS - Dual GeForce RTX 5070 12GB GDDR7 OC Edition</p>
        <p class='fw-bold mb-0 mt-auto'>£560.00</p>
      </div>
    </div>
    """
    listings = parse_listings_from_html(
        html,
        base_url='https://www.ebuyer.com',
        source='ebuyer',
        source_type=SourceType.RETAILER,
        selector=SelectorConfig(
            card='div.card.text-center',
            title='p.card-link',
            price='p.fw-bold.mt-auto',
            url='a.stretched-link',
            image='img',
            id='a.stretched-link',
        ),
        category='gpu',
    )
    assert len(listings) == 1
    assert listings[0].url.endswith('/asus-dual-geforce-rtx-5070-12gb-gddr7-oc-edition-705967#colcode=70596799')
    assert listings[0].price == Decimal('560.00')
    assert listings[0].title_raw == 'ASUS - Dual GeForce RTX 5070 12GB GDDR7 OC Edition'


@pytest.mark.asyncio
async def test_ccl_connector_parses_live_autocomplete_markup():
    html = """
    <div class='card text-center rounded-0 h-100 bg-vdarkgrey'>
      <div class='card-body d-flex flex-column'>
        <a href='/rtx-4070-ventus-2x-12g-oc-msi-geforce-rtx-4070-ventus-2x-oc-12gb-graphics-card-486350/' class='stretched-link'></a>
        <img src='https://static.cclonline.com/images/avante/4070Ventus2Xgpu1.JPG?width=300&height=300&scale=canvas' alt='MSI GeForce RTX 4070 Ventus 2X 12G OC Graphics Card'>
        <p class='card-link fw-bold mb-2'>MSI GeForce RTX 4070 Ventus 2X 12G OC Graphics Card</p>
        <p class='fw-bold mb-0 mt-auto'>£599.99</p>
      </div>
    </div>
    """
    listings = parse_listings_from_html(
        html,
        base_url='https://www.cclonline.com',
        source='ccl',
        source_type=SourceType.RETAILER,
        selector=SelectorConfig(
            card='div.card.text-center',
            title='p.card-link',
            price='p.fw-bold.mt-auto',
            url='a.stretched-link',
            image='img',
            id='a.stretched-link',
        ),
        category='gpu',
    )
    assert len(listings) == 1
    assert listings[0].url.endswith('/rtx-4070-ventus-2x-12g-oc-msi-geforce-rtx-4070-ventus-2x-oc-12gb-graphics-card-486350/')
    assert listings[0].price == Decimal('599.99')
    assert listings[0].source == 'ccl'


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
