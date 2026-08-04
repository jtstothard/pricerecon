from __future__ import annotations

from decimal import Decimal
from typing import Any

import pytest

from pricerecon.connectors.amazon import AmazonConnector
from pricerecon.connectors.cex import CexConnector
from pricerecon.connectors.ebay import eBayConnector
from pricerecon.connectors.external_browser import (
    BrowserAttempt,
    BrowserDegradation,
    ExternalBrowserResult,
    NetworkResponse,
    RenderedContent,
)
from pricerecon.connectors.shopify import ShopifyConnector
from pricerecon.connectors.status import ConnectorDegradedError
from pricerecon.models import Condition, NormalizedListing, SourceType

CONFIG: dict[str, Any] = {
    "browser_backends": {
        "primary": {"type": "cloakbrowser", "endpoint": "http://primary.example:9378"},
        "backup": {"type": "camofox", "endpoint": "http://backup.example:9377"},
    },
    "browser_default": ["primary", "backup"],
}


def browser_result(
    *,
    html: str = "",
    responses: tuple[NetworkResponse, ...] = (),
    degradation: BrowserDegradation = BrowserDegradation.NONE,
    selected_backend: str = "primary",
) -> ExternalBrowserResult:
    return ExternalBrowserResult(
        selected_backend=selected_backend,
        attempts=(BrowserAttempt(selected_backend, degradation),),
        rendered=RenderedContent(html=html),
        responses=responses,
        degradation=degradation,
    )


@pytest.fixture
def amazon(monkeypatch: pytest.MonkeyPatch) -> AmazonConnector:
    mock_requests = pytest.importorskip("unittest.mock").MagicMock()
    monkeypatch.setattr("pricerecon.connectors.amazon.requests", mock_requests)
    return AmazonConnector()


def test_remaining_connector_configuration_is_generic_and_absent_by_default(
    amazon: AmazonConnector,
) -> None:
    cex = CexConnector()
    shopify = ShopifyConnector(base_url="https://store.example")
    try:
        for connector in (amazon, cex, shopify):
            assert connector.has_external_browser() is False
            connector.configure_external_browser(CONFIG, {"browser_backend": "primary"})
            assert connector.has_external_browser() is True
    finally:
        # The test does not use Shopify's HTTP client, but cleanup preserves its contract.
        import asyncio

        asyncio.run(shopify.cleanup())


@pytest.mark.asyncio
async def test_amazon_browser_override_is_used_and_selected_backend_is_recorded(
    amazon: AmazonConnector, monkeypatch: pytest.MonkeyPatch
) -> None:
    amazon.configure_external_browser(CONFIG, {"browser_backend": "primary"})
    html = """<div data-component-type="s-search-result"><div data-asin="B0C123ABC1">
    <span class="a-size-base-plus a-color-base a-text-normal">Widget</span>
    <span class="a-offscreen">£19.99</span></div></div>"""

    async def navigate(_url: str) -> ExternalBrowserResult:
        return browser_result(html=html)

    monkeypatch.setattr(amazon, "navigate_external_browser", navigate)
    listings = await amazon.search("widget")

    assert listings[0].price == Decimal("19.99")
    assert (listings[0].variant_normalized or {})["selected_backend"] == "primary"


@pytest.mark.asyncio
async def test_amazon_browser_failure_is_truthful_not_direct_transport_fallback(
    amazon: AmazonConnector, monkeypatch: pytest.MonkeyPatch
) -> None:
    amazon.configure_external_browser(CONFIG, {"browser_backend": "primary"})

    async def navigate(_url: str) -> ExternalBrowserResult:
        return browser_result(degradation=BrowserDegradation.TIMEOUT)

    monkeypatch.setattr(amazon, "navigate_external_browser", navigate)
    with pytest.raises(ConnectorDegradedError) as error:
        await amazon.search("widget")
    assert error.value.detail == {
        "selected_backend": "primary",
        "browser_degradation": "timeout",
        "browser_attempts": [{"backend": "primary", "degradation": "timeout"}],
    }


@pytest.mark.asyncio
async def test_ebay_browser_override_uses_current_rendered_prices_not_browse_api(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ebay = eBayConnector(app_id="test-app")
    ebay.configure_external_browser(CONFIG, {"browser_backend": "primary"})
    html = """<li class="s-item"><a href="https://www.ebay.co.uk/itm/123456789012"><h3 class="s-item__title">Widget</h3><span class="s-item__price">£17.50</span></a></li>"""

    async def navigate(_url: str) -> ExternalBrowserResult:
        return browser_result(html=html)

    async def api_must_not_run() -> str:
        raise AssertionError("browser override must not fall back to eBay Browse API")

    monkeypatch.setattr(ebay, "navigate_external_browser", navigate)
    monkeypatch.setattr(ebay, "ensure_token", api_must_not_run)
    listings = await ebay.search("widget")

    assert listings[0].price == Decimal("17.50")
    assert listings[0].variant_normalized is not None
    assert listings[0].variant_normalized["selected_backend"] == "primary"


@pytest.mark.asyncio
async def test_ebay_browser_failure_is_truthful_not_browse_api_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ebay = eBayConnector(app_id="test-app")
    ebay.configure_external_browser(CONFIG, {"browser_backend": "primary"})

    async def navigate(_url: str) -> ExternalBrowserResult:
        return browser_result(degradation=BrowserDegradation.TIMEOUT)

    async def api_must_not_run() -> str:
        raise AssertionError("browser failure must not fall back to eBay Browse API")

    monkeypatch.setattr(ebay, "navigate_external_browser", navigate)
    monkeypatch.setattr(ebay, "ensure_token", api_must_not_run)
    with pytest.raises(ConnectorDegradedError) as error:
        await ebay.search("widget")
    assert error.value.status.value == "timeout"


@pytest.mark.asyncio
async def test_cex_browser_override_requires_intercepted_authoritative_hits(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cex = CexConnector()
    cex.configure_external_browser(CONFIG, {"browser_backend": "primary"})
    payload = '{"hits":[{"boxId":"123","boxName":"Widget","sellPrice":19.99,"stores":["x"],"inStockOnline":true}]}'

    async def navigate(_url: str) -> ExternalBrowserResult:
        return browser_result(
            responses=(
                NetworkResponse(
                    url="https://search.webuy.io/1/indexes/prod_cex_uk/query",
                    status=200,
                    body=payload,
                    intercepted=True,
                ),
            )
        )

    monkeypatch.setattr(cex, "navigate_external_browser", navigate)
    listings = await cex.search("widget")
    assert listings[0].source == "cex"
    assert (listings[0].variant_normalized or {})["selected_backend"] == "primary"


@pytest.mark.asyncio
async def test_shopify_browser_override_does_not_substitute_rendered_discovery_for_prices(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    shopify = ShopifyConnector(base_url="https://store.example")
    shopify.configure_external_browser(CONFIG, {"browser_backend": "primary"})

    async def navigate(_url: str) -> ExternalBrowserResult:
        return browser_result(html="<html>product discovery only</html>")

    monkeypatch.setattr(shopify, "navigate_external_browser", navigate)
    try:
        with pytest.raises(ConnectorDegradedError, match="no intercepted products JSON"):
            await shopify.search("widget")
    finally:
        await shopify.cleanup()


@pytest.mark.asyncio
async def test_shopify_browser_override_records_backend_for_intercepted_products(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    shopify = ShopifyConnector(base_url="https://store.example")
    shopify.configure_external_browser(CONFIG, {"browser_backend": "primary"})
    payload = '{"products":[{"handle":"widget","title":"Widget","variants":[{"id":"1","price":"12.50","available":true}]}]}'

    async def navigate(_url: str) -> ExternalBrowserResult:
        return browser_result(
            responses=(
                NetworkResponse(
                    url="https://store.example/products.json?limit=250",
                    status=200,
                    body=payload,
                    intercepted=True,
                ),
            )
        )

    monkeypatch.setattr(shopify, "navigate_external_browser", navigate)
    try:
        listings = await shopify.search("widget")
        assert listings[0].price == Decimal("12.50")
        assert (listings[0].variant_normalized or {})["selected_backend"] == "primary"
    finally:
        await shopify.cleanup()


def test_browser_annotation_preserves_existing_variant_data(amazon: AmazonConnector) -> None:
    listing = NormalizedListing(
        source="amazon_uk",
        source_type=SourceType.RETAILER,
        source_listing_id="B0C123ABC1",
        title_raw="Widget",
        price=Decimal("1"),
        currency="GBP",
        url="https://amazon.example/dp/B0C123ABC1",
        condition=Condition.NEW,
        variant_normalized={"existing": True},
        product_normalized=None,
        condition_raw=None,
        shipping_cost=None,
        total_landed_cost=None,
        seller_or_store=None,
        seller_feedback_score=None,
        seller_feedback_pct=None,
        location=None,
        in_stock=None,
        stock_state=None,
        image_url=None,
        exact_variant_confirmed=None,
        variant_match_confidence=None,
        mismatch_flags=None,
        risk_flags=None,
        category=None,
    )
    annotated = amazon.annotate_browser_result([listing], browser_result())
    assert annotated[0].variant_normalized == {
        "existing": True,
        "selected_backend": "primary",
        "browser_degradation": "none",
        "browser_attempts": [{"backend": "primary", "degradation": "none"}],
    }
