from __future__ import annotations

from decimal import Decimal
from typing import Any, cast

import httpx
import pytest
from httpx import Request, Response

from pricerecon.connectors.fb_marketplace import FacebookMarketplaceConnector
from pricerecon.connectors.flaresolverr import FlareSolverrClient
from pricerecon.connectors.html import SelectorConfig, parse_listings_from_html
from pricerecon.connectors.overclockers import OverclockersConnector
from returns.result import Failure

from pricerecon.connectors.rss import (
    ConnectorTemplateConfig,
    TemplateConnector,
    load_template_configs,
    load_template_configs_result,
    parse_hardwareswapuk_post,
)
from pricerecon.connectors.reddit import (
    HotUKDealsConnector,
    RedditBapcSalesUKConnector,
    RedditHardwareSwapUKConnector,
)
from pricerecon.connectors.shopify import ShopifyConnector
from pricerecon.connectors.aliexpress import AliExpressConnector
from pricerecon.connectors.dell_uk import DellUKConnector
from pricerecon.connectors.specs import extract_specs
from pricerecon.connectors.status import ConnectorDegradedError, ConnectorStatus
from pricerecon.core import watch_executor
from pricerecon.models import (
    NormalizedListing,
    SourceConfig,
    SourceType,
    SpecMatch,
    Watch,
    WatchFilters,
    WatchGrouping,
    WatchNotification,
    WatchSchedule,
)


@pytest.mark.asyncio
async def test_flaresolverr_client_posts_expected_payload(monkeypatch: Any) -> None:
    seen: dict[str, object] = {}

    async def handler(request: Request) -> Response:
        seen["method"] = request.method
        seen["url"] = str(request.url)
        seen["json"] = request.read().decode()
        return Response(200, json={"solution": {"response": "<html><body>ok</body></html>"}})

    transport = httpx.MockTransport(handler)

    class DummyClient(httpx.AsyncClient):
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__(transport=transport, timeout=kwargs.get("timeout", 90.0))

    monkeypatch.setattr(httpx, "AsyncClient", DummyClient)
    html = await FlareSolverrClient("http://example.test/v1").request_html(
        "https://example.com/search?q=rtx"
    )
    assert html == "<html><body>ok</body></html>"
    assert seen["method"] == "POST"
    assert seen["url"] == "http://example.test/v1"


def test_spec_extraction_covers_common_parts() -> None:
    gpu = extract_specs("MSI NVIDIA GeForce RTX 4090 24GB Gaming X", "gpu")
    assert gpu["gpu_model"] == "RTX 4090"
    assert gpu["ram_gb"] == 24
    cpu = extract_specs("AMD Ryzen 7 7800X3D", "cpu")
    assert cpu["cpu_vendor"] == "AMD"
    assert "7800X3D" in cpu["cpu_model"]


def test_html_parser_normalizes_cards() -> None:
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
        base_url="https://example.com",
        source="scan",
        source_type=SourceType.RETAILER,
        selector=SelectorConfig(
            card="article.product-card",
            title="h3",
            price=".price",
            url="a",
            stock=".availability",
            image="img",
        ),
        category="gpu",
    )
    assert len(listings) == 1
    listing = listings[0]
    assert listing.url == "https://example.com/p/1"
    assert listing.price == Decimal("599.99")
    assert listing.in_stock is True
    assert listing.variant_normalized is not None
    assert listing.variant_normalized["gpu_model"] == "RTX 4070"

    import importlib.metadata

    entry_points = {
        ep.name: ep.value for ep in importlib.metadata.entry_points(group="pricerecon.connectors")
    }
    assert entry_points["johnlewis"] == "pricerecon.connectors.johnlewis:JohnLewisConnector"


@pytest.mark.asyncio
async def test_watch_executor_filters_by_spec_match_ram(monkeypatch: Any) -> None:
    now = watch_executor.datetime.utcnow()
    watch = Watch(
        id=99,
        name="RAM floor watch",
        query="laptop",
        category="laptop",
        sources=[SourceConfig(connector="aliexpress", config={})],
        filters=WatchFilters(
            price_max=None,
            spec_match=SpecMatch(ram_gb=32),
            min_seller_feedback=None,
            min_seller_feedback_pct=None,
        ),
        schedule=WatchSchedule(time_window=None),
        grouping=WatchGrouping(product_key=None),
        notifications=WatchNotification(
            webhook_url=None,
            telegram_bot_token=None,
            telegram_chat_id=None,
            discord_webhook_url=None,
        ),
        enabled=True,
        created_at=now,
        updated_at=now,
        last_check_at=None,
        status="active",
    )

    listings = [
        NormalizedListing(
            source="aliexpress",
            source_type=SourceType.MARKETPLACE,
            source_listing_id="1",
            title_raw="Lenovo ThinkPad T14 16GB RAM 512GB SSD",
            price=Decimal("499.99"),
            currency="GBP",
            url="https://example.com/1",
            timestamp_seen=now,
            product_normalized=None,
            variant_normalized=extract_specs("Lenovo ThinkPad T14 16GB RAM 512GB SSD", "laptop"),
            condition=None,
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
            category="laptop",
        ),
        NormalizedListing(
            source="aliexpress",
            source_type=SourceType.MARKETPLACE,
            source_listing_id="2",
            title_raw="Lenovo ThinkPad T14 32GB RAM 1TB SSD",
            price=Decimal("699.99"),
            currency="GBP",
            url="https://example.com/2",
            timestamp_seen=now,
            product_normalized=None,
            variant_normalized=extract_specs("Lenovo ThinkPad T14 32GB RAM 1TB SSD", "laptop"),
            condition=None,
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
            category="laptop",
        ),
    ]

    recorded: list[tuple[str, str, str | None, dict[str, object] | None]] = []

    class FakeConnector:
        async def initialize(self) -> Any:
            return None

        async def search(self, query: Any, connector_filters: Any) -> Any:
            assert connector_filters == {}
            return listings

        async def cleanup(self) -> Any:
            return None

    class FakeCursor:
        def execute(self, *args: Any, **kwargs: Any) -> Any:
            return None

        def fetchone(self) -> Any:
            return None

    class FakeConn:
        def cursor(self) -> Any:
            return FakeCursor()

        def commit(self) -> Any:
            return None

        def close(self) -> Any:
            return None

    class FakeDiffResult:
        has_events = False
        new_listings: list[Any] = []
        price_drops: list[Any] = []
        stock_changes: list[Any] = []
        listings_gone: list[Any] = []

    monkeypatch.setattr(watch_executor, "get_watch", lambda watch_id: watch)
    monkeypatch.setattr(
        watch_executor, "run_check", lambda *_args, **_kwargs: (True, FakeDiffResult(), [])
    )
    monkeypatch.setattr(watch_executor, "get_db", lambda: FakeConn())
    monkeypatch.setattr(
        "pricerecon.connectors.discover_connectors",
        lambda: {"aliexpress": FakeConnector},
    )
    monkeypatch.setattr(
        watch_executor,
        "upsert_connector_health",
        lambda connector_id, status, last_error=None, details=None: recorded.append(
            (connector_id, status, last_error, details)
        ),
    )

    result = await watch_executor.execute_watch(99)

    assert result["success"] is True
    assert result["listings_found"] == 1
    assert recorded[0][0] == "aliexpress"
    assert recorded[0][1] == "ok"


def test_reddit_hardwareswapuk_price_parser_uses_visible_gbp_amount() -> None:
    listing = parse_hardwareswapuk_post(
        "[SG] Sealed ASUS GeForce RTX 5090 OC Edition 32GB GPU [W] £3,000",
        "",
        "seller",
        "https://www.reddit.com/r/hardwareswapuk/comments/abc123/post/",
    )
    assert listing["price"] == Decimal("3000")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("connector_cls", "expected_path"),
    [
        (HotUKDealsConnector, "/rss/new"),
        (RedditHardwareSwapUKConnector, "/r/hardwareswapuk/new/.rss"),
        (RedditBapcSalesUKConnector, "/r/bapcsalesuk/new/.rss"),
    ],
)
async def test_signal_rss_connectors_use_canonical_feeds_and_filter_locally(
    connector_cls: Any, expected_path: str
) -> None:
    feed = """<?xml version='1.0' encoding='UTF-8'?>
<rss><channel>
  <item>
    <title>RTX 5070 GPU bargain</title>
    <link>https://example.com/1</link>
    <description>RTX 5070 GPU bargain</description>
    <guid>1</guid>
  </item>
  <item>
    <title>Gaming laptop sale</title>
    <link>https://example.com/2</link>
    <description>Gaming laptop sale</description>
    <guid>2</guid>
  </item>
</channel></rss>
"""
    captured: list[str] = []

    async def handler(request: Request) -> Response:
        captured.append(str(request.url))
        return Response(200, text=feed, request=request)

    transport = httpx.MockTransport(handler)
    connector = connector_cls()
    connector._client = httpx.AsyncClient(transport=transport, timeout=30.0)
    listings = await connector.search("RTX 5070")
    await connector.cleanup()

    assert captured
    assert expected_path in captured[0]
    assert "search.rss" not in captured[0]
    assert len(listings) == 1
    assert "RTX 5070" in listings[0].title_raw


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status_code", "expected_status"),
    [(429, ConnectorStatus.rate_limited), (403, ConnectorStatus.bot_blocked)],
)
async def test_template_connector_classifies_upstream_status_codes(
    status_code: int, expected_status: ConnectorStatus
) -> None:
    template = ConnectorTemplateConfig(
        source="reddit_test",
        display_name="Reddit test",
        source_role=SourceType.SIGNAL,
        endpoint_url="https://example.com/rss?q={query}&limit={limit}",
    )
    connector = TemplateConnector(template)

    async def handler(request: Request) -> Response:
        return Response(status_code, text="", headers={"Retry-After": "120"}, request=request)

    connector._client = httpx.AsyncClient(transport=httpx.MockTransport(handler), timeout=30.0)

    with pytest.raises(ConnectorDegradedError) as exc_info:
        await connector.search("RTX 5070")

    err = exc_info.value
    assert err.status == expected_status
    detail = cast(dict[str, Any], err.detail)
    assert detail["status_code"] == status_code
    assert detail["requested_url"].startswith("https://example.com/rss?q=RTX")
    assert detail["requested_url"].endswith("&limit=25")
    if status_code == 429:
        assert detail["retry_after_seconds"] == 120
    else:
        assert "retry_after_seconds" not in detail or detail["retry_after_seconds"] is None
    await connector.cleanup()


def test_rss_template_loader_skips_non_rss_html_templates(tmp_path: Any) -> None:
    (tmp_path / "scan.yml").write_text(
        """name: scan\nsource_type: retailer\nbase_url: https://example.com\nsearch_url: https://example.com/search?q={query}\nselectors:\n  card: article\n  title: h3\n  price: .price\n  url: a\n"""
    )
    (tmp_path / "hotukdeals.yml").write_text(
        """name: hotukdeals\nsource_type: signal\nbase_url: https://example.com\nsearch_url: https://example.com/rss?q={query}\nselectors:\n  card: article\n  title: h3\n  price: .price\n  url: a\n"""
    )
    (tmp_path / "reddit_hardwareswapuk.yml").write_text(
        """source: reddit_hardwareswapuk\nsource_role: marketplace\nendpoint_url: https://example.com/rss?q={query}&limit={limit}\n"""
    )

    configs = load_template_configs(tmp_path)
    assert set(configs) == {"reddit_hardwareswapuk"}


def test_rss_template_loader_returns_failure_for_invalid_yaml(tmp_path: Any) -> None:
    bad_template = tmp_path / "reddit_hardwareswapuk.yml"
    bad_template.write_text(
        """source: reddit_hardwareswapuk\nsource_role: marketplace\nendpoint_url: [oops\n"""
    )

    result = load_template_configs_result(tmp_path)

    assert isinstance(result, Failure)
    assert "invalid YAML" in result.failure()


@pytest.mark.asyncio
async def test_facebook_marketplace_connector_parses_concatenated_gbp_price() -> None:
    cards = [
        {
            "title": "£550Nvidia GeForce rtx 4060 8GB",
            "url": "https://www.facebook.com/marketplace/item/123",
            "text": "£550Nvidia GeForce rtx 4060 8GB",
        },
        {
            "title": "£450ASUS GEFORCE RTX 5070",
            "url": "https://www.facebook.com/marketplace/item/456",
            "text": "£450ASUS GEFORCE RTX 5070",
        },
    ]

    class FakeLocator:
        def __init__(self, payload: Any) -> None:
            self.payload = payload

        async def evaluate_all(self, _script: Any) -> Any:
            return self.payload

    class FakePage:
        async def goto(self, *_args: Any, **_kwargs: Any) -> Any:
            return None

        async def wait_for_timeout(self, *_args: Any, **_kwargs: Any) -> Any:
            return None

        def locator(self, _selector: Any) -> Any:
            return FakeLocator(cards)

    class FakeContext:
        pass

    connector = FacebookMarketplaceConnector(browser_client=None)
    connector._context = cast(Any, FakeContext())
    connector._page = cast(Any, FakePage())

    listings = await connector.search("rtx")

    assert [listing.price for listing in listings] == [Decimal("550"), Decimal("450")]
    assert [listing.title_raw for listing in listings] == [card["title"] for card in cards]


@pytest.mark.asyncio
async def test_shopify_connector_fetches_products_and_variants() -> None:
    calls: list[str] = []

    async def handler(request: Request) -> Response:
        calls.append(str(request.url))
        if str(request.url).endswith("/search?q=RTX+4070&type=product"):
            return Response(
                200, text="<html><body>Shopify</body></html>", headers={"X-ShopId": "123"}
            )
        if str(request.url).endswith("/products.json?limit=250"):
            return Response(
                200,
                json={
                    "products": [
                        {
                            "handle": "rtx-4070",
                            "title": "RTX 4070 Ti",
                            "product_type": "gpu",
                            "image": {"src": "/img.jpg"},
                            "variants": [
                                {"id": 1, "title": "Base", "price": "599.99", "available": True}
                            ],
                        }
                    ]
                },
            )
        raise AssertionError(f"unexpected url {request.url}")

    transport = httpx.MockTransport(handler)
    connector = ShopifyConnector(base_url="https://shop.example")
    connector._client = httpx.AsyncClient(transport=transport, timeout=30.0)
    listings = await connector.search("RTX 4070")
    await connector.cleanup()
    assert calls[0].endswith("/search?q=RTX+4070&type=product")
    assert calls[1].endswith("/products.json?limit=250")
    assert len(listings) == 1
    assert listings[0].price == Decimal("599.99")
    assert listings[0].source == "shopify"


@pytest.mark.asyncio
async def test_shopify_connector_requires_store_base_url() -> None:
    connector = ShopifyConnector()

    with pytest.raises(ConnectorDegradedError) as exc_info:
        await connector.search("RTX 4070")

    await connector.cleanup()
    err = exc_info.value
    assert err.status == ConnectorStatus.auth_failed
    assert err.connector_id == "shopify"
    assert err.detail == {"missing": ["base_url"], "accepted_keys": ["base_url", "store_url"]}


@pytest.mark.asyncio
async def test_shopify_connector_accepts_store_url_alias() -> None:
    calls: list[str] = []

    async def handler(request: Request) -> Response:
        calls.append(str(request.url))
        if str(request.url).endswith("/search?q=RTX+4070&type=product"):
            return Response(
                200, text="<html><body>Shopify</body></html>", headers={"X-ShopId": "123"}
            )
        if str(request.url).endswith("/products.json?limit=250"):
            return Response(
                200,
                json={
                    "products": [
                        {
                            "handle": "rtx-4070",
                            "title": "RTX 4070 Ti",
                            "product_type": "gpu",
                            "variants": [
                                {"id": 1, "title": "Base", "price": "599.99", "available": True}
                            ],
                        }
                    ]
                },
            )
        raise AssertionError(f"unexpected url {request.url}")

    transport = httpx.MockTransport(handler)
    connector = ShopifyConnector(store_url="https://shop.example")
    connector._client = httpx.AsyncClient(transport=transport, timeout=30.0)
    listings = await connector.search("RTX 4070")
    await connector.cleanup()
    assert calls[0].endswith("/search?q=RTX+4070&type=product")
    assert calls[1].endswith("/products.json?limit=250")
    assert len(listings) == 1
    assert listings[0].source_listing_id == "1"


@pytest.mark.asyncio
async def test_aliexpress_connector_uses_top_sync_endpoint_and_signed_requests() -> None:
    calls: list[dict[str, object]] = []

    class DummyResponse:
        def __init__(self, payload: dict[str, object], status_code: int = 200) -> None:
            self._payload = payload
            self.status_code = status_code
            self.headers: dict[str, str] = {}

        def raise_for_status(self) -> Any:
            if self.status_code >= 400:
                raise httpx.HTTPStatusError(
                    "boom",
                    request=httpx.Request("POST", "https://example.test"),
                    response=httpx.Response(self.status_code),
                )

        def json(self) -> Any:
            return self._payload

    class DummyClient:
        async def get(
            self, url: Any, params: Any = None, headers: Any = None, timeout: Any = None
        ) -> Any:
            calls.append(
                {
                    "url": url,
                    "method": "GET",
                    "params": params,
                    "headers": headers,
                    "timeout": timeout,
                }
            )
            assert url == "https://api-sg.aliexpress.com/rest/auth/token/refresh"
            assert isinstance(params, dict)
            return DummyResponse(
                {
                    "code": "0",
                    "access_token": "fresh-token",
                    "refresh_token": "fresh-refresh",
                    "expires_in": 7200,
                }
            )

        async def post(
            self, url: Any, json: Any = None, headers: Any = None, data: Any = None
        ) -> Any:
            body = data if data is not None else json
            calls.append({"url": url, "body": body, "headers": headers})
            if (
                isinstance(body, dict)
                and body.get("method") == "aliexpress.affiliate.product.query"
            ):
                return DummyResponse(
                    {
                        "result": {
                            "items": [
                                {
                                    "productId": "1005008557811111",
                                    "title": "Ali CPU",
                                    "displayPrice": "199.99",
                                    "originalPrice": "249.99",
                                    "shippingCost": "4.99",
                                    "shopName": "SZCPU",
                                    "evaluateRate": "4.8",
                                    "orders": "123",
                                    "inStock": True,
                                    "currency": "GBP",
                                }
                            ]
                        }
                    }
                )
            if isinstance(body, dict) and body.get("method") == "aliexpress.ds.product.get":
                return DummyResponse(
                    {
                        "result": {
                            "data": {
                                "title": "Ali CPU DS",
                                "displayPrice": "189.99",
                                "originalPrice": "239.99",
                                "shippingCost": "3.99",
                                "shopName": "SZCPU DS",
                                "rating": "4.9",
                                "sales": "456",
                                "inStock": True,
                                "coupons": [{"text": "£10 off"}],
                            }
                        }
                    }
                )
            raise AssertionError(body)

        async def aclose(self) -> Any:
            return None

    class DummyBrowserPage:
        async def goto(self, url: Any, wait_until: Any = None, timeout: Any = None) -> Any:
            calls.append({"url": url, "kind": "goto"})

        async def content(self) -> Any:
            return '<html><body><h1>Ali CPU Browser 1005008557811111</h1><script>priceCurrency:"GBP",price:"189.99"</script><div>Extra 10% off with coins</div><div>1,234 sold</div></body></html>'

    class DummyBrowserContext:
        async def new_page(self) -> Any:
            return DummyBrowserPage()

        async def close(self) -> Any:
            return None

    class DummyBrowserClient:
        async def new_context(self) -> Any:
            return DummyBrowserContext()

    connector = AliExpressConnector(
        {
            "manual_pids": ["1005012248779870"],
            "ds_access_token": "stale-token",
            "ds_refresh_token": "refresh-token",
            "ds_app_key": "app-key",
            "ds_app_secret": "app-secret",
            "ds_expires_at": "2026-01-01T00:00:00+00:00",
        },
        browser_client=cast(Any, DummyBrowserClient()),
        http_client=cast(Any, DummyClient()),
    )
    listings = await connector.search(
        "1005008557811111",
        {
            "browser_enrich": True,
            "browser_enrich_all": True,
            "enrich_with_ds": True,
            "brave_discovery": False,
        },
    )
    await connector.cleanup()

    refresh_calls = [
        call
        for call in calls
        if call.get("url") == "https://api-sg.aliexpress.com/rest/auth/token/refresh"
    ]
    assert len(refresh_calls) == 1
    refresh_params = refresh_calls[0].get("params")
    assert isinstance(refresh_params, dict)
    assert refresh_calls[0].get("method") == "GET"
    assert refresh_params["sign_method"] == "sha256"
    assert refresh_params["sign"] == connector._ds_system_sign(
        "/auth/token/refresh", refresh_params, "app-secret"
    )

    api_calls = [call for call in calls if call.get("url") == "https://api-sg.aliexpress.com/sync"]
    assert api_calls, calls

    def body_method(call: dict[str, Any]) -> str | None:
        body = call.get("body")
        return body.get("method") if isinstance(body, dict) else None

    def body_has_sign(call: dict[str, Any]) -> bool:
        body = call.get("body")
        return isinstance(body, dict) and body.get("sign_method") == "md5" and "sign" in body

    assert any(body_method(call) == "aliexpress.affiliate.product.query" for call in api_calls)
    assert any(body_method(call) == "aliexpress.ds.product.get" for call in api_calls)
    assert all(body_has_sign(call) for call in api_calls)
    assert any("goto" == call.get("kind") for call in calls)
    assert any(listing.source_listing_id == "1005008557811111" for listing in listings)
    manual = next(
        listing for listing in listings if listing.source_listing_id == "1005012248779870"
    )
    assert manual.variant_normalized is not None
    assert manual.variant_normalized["aliexpress_watch_mode"] == "manual_pid"
    assert manual.price == Decimal("189.99")
    assert manual.variant_normalized["aliexpress_source_lane"] in {"ds", "browser"}
    affiliate = next(
        listing for listing in listings if listing.source_listing_id == "1005008557811111"
    )
    assert affiliate.price == Decimal("189.99")
    assert affiliate.variant_normalized is not None
    assert affiliate.variant_normalized["aliexpress_source_lane"] in {"ds", "browser"}
    assert affiliate.variant_normalized["aliexpress_coupon_layers"]


@pytest.mark.asyncio
async def test_aliexpress_connector_uses_manual_pid_and_ds_and_browser(monkeypatch: Any) -> None:
    calls: list[tuple[str, str]] = []

    class DummyResponse:
        def __init__(self, payload: dict[str, object], status_code: int = 200) -> None:
            self._payload = payload
            self.status_code = status_code

        def raise_for_status(self) -> Any:
            if self.status_code >= 400:
                raise httpx.HTTPStatusError(
                    "boom",
                    request=httpx.Request("POST", "https://example.test"),
                    response=httpx.Response(self.status_code),
                )

        def json(self) -> Any:
            return self._payload

    class DummyClient:
        async def get(
            self, url: Any, params: Any = None, headers: Any = None, timeout: Any = None
        ) -> Any:
            calls.append((url, "GET"))
            assert url == "https://api-sg.aliexpress.com/rest/auth/token/refresh"
            assert isinstance(params, dict)
            return DummyResponse(
                {
                    "code": "0",
                    "access_token": "fresh-token",
                    "refresh_token": "fresh-refresh",
                    "expires_in": 7200,
                }
            )

        async def post(
            self, url: Any, json: Any = None, headers: Any = None, data: Any = None
        ) -> Any:
            body = data if data is not None else json
            calls.append((url, "POST"))
            if (
                isinstance(body, dict)
                and body.get("method") == "aliexpress.affiliate.product.query"
            ):
                return DummyResponse(
                    {
                        "result": {
                            "items": [
                                {
                                    "productId": "1005008557811111",
                                    "title": "Ali CPU",
                                    "displayPrice": "199.99",
                                    "originalPrice": "249.99",
                                    "shippingCost": "4.99",
                                    "shopName": "SZCPU",
                                    "evaluateRate": "4.8",
                                    "orders": "123",
                                    "inStock": True,
                                    "currency": "GBP",
                                }
                            ]
                        }
                    }
                )
            if isinstance(body, dict) and body.get("method") == "aliexpress.ds.product.get":
                return DummyResponse(
                    {
                        "result": {
                            "data": {
                                "title": "Ali CPU DS",
                                "displayPrice": "189.99",
                                "originalPrice": "239.99",
                                "shippingCost": "3.99",
                                "shopName": "SZCPU DS",
                                "rating": "4.9",
                                "sales": "456",
                                "inStock": True,
                                "coupons": [{"text": "£10 off"}],
                            }
                        }
                    }
                )
            raise AssertionError(body)

        async def aclose(self) -> Any:
            return None

    class DummyBrowserPage:
        async def goto(self, url: Any, wait_until: Any = None, timeout: Any = None) -> Any:
            calls.append((url, "goto"))

        async def content(self) -> Any:
            return '<html><body><h1>Ali CPU Browser 1005008557811111</h1><script>priceCurrency:"GBP",price:"189.99"</script><div>Extra 10% off with coins</div><div>1,234 sold</div></body></html>'

    class DummyBrowserContext:
        async def new_page(self) -> Any:
            return DummyBrowserPage()

        async def close(self) -> Any:
            return None

    class DummyBrowserClient:
        async def new_context(self) -> Any:
            return DummyBrowserContext()

    connector = AliExpressConnector(
        {
            "manual_pids": ["1005012248779870"],
            "ds_access_token": "stale-token",
            "ds_refresh_token": "refresh-token",
            "ds_app_key": "app-key",
            "ds_app_secret": "app-secret",
            "ds_expires_at": "2026-01-01T00:00:00+00:00",
        },
        browser_client=cast(Any, DummyBrowserClient()),
        http_client=cast(Any, DummyClient()),
    )
    listings = await connector.search(
        "1005008557811111",
        {
            "browser_enrich": True,
            "browser_enrich_all": True,
            "enrich_with_ds": True,
            "brave_discovery": False,
        },
    )
    await connector.cleanup()

    assert calls
    assert ("https://api-sg.aliexpress.com/rest/auth/token/refresh", "GET") in calls
    assert ("https://api-sg.aliexpress.com/sync", "POST") in calls
    assert any("goto" == kind for _, kind in calls)
    assert any(listing.source_listing_id == "1005008557811111" for listing in listings)
    manual = next(
        listing for listing in listings if listing.source_listing_id == "1005012248779870"
    )
    assert manual.variant_normalized is not None
    assert manual.variant_normalized["aliexpress_watch_mode"] == "manual_pid"
    assert manual.price == Decimal("189.99")
    assert manual.variant_normalized["aliexpress_source_lane"] in {"ds", "browser"}
    affiliate = next(
        listing for listing in listings if listing.source_listing_id == "1005008557811111"
    )
    assert affiliate.price == Decimal("189.99")
    assert affiliate.variant_normalized is not None
    assert affiliate.variant_normalized["aliexpress_source_lane"] in {"ds", "browser"}
    assert affiliate.variant_normalized["aliexpress_coupon_layers"]


def test_aliexpress_connector_extracts_nested_ds_payload_shape() -> None:
    now = watch_executor.datetime.utcnow()
    connector = AliExpressConnector({})
    listing = NormalizedListing(
        source="aliexpress",
        source_type=SourceType.MARKETPLACE,
        source_listing_id="1005008557811111",
        title_raw="1005008557811111",
        price=Decimal("0"),
        currency="GBP",
        url="https://www.aliexpress.com/item/1005008557811111.html",
        timestamp_seen=now,
        product_normalized=None,
        variant_normalized={
            "aliexpress_product_id": "1005008557811111",
            "aliexpress_watch_mode": "manual_pid",
        },
        condition=None,
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
        category="cpu",
    )

    detail = {
        "ae_item_sku_info_dtos": {
            "ae_item_sku_info_d_t_o": [
                {
                    "offer_sale_price": "261.59",
                    "sku_price": "379.12",
                    "currency_code": "GBP",
                    "sku_available_stock": 19,
                }
            ]
        },
        "ae_item_base_info_dto": {
            "subject": "AMD Ryzen 9 5950X New Ryzen 9 5000 Series Vermeer (Zen 3) 16-Core 3.4 GHz Socket AM4 105W Socket AM4 but without cooler",
            "evaluation_count": "28",
            "sales_count": "48",
            "product_status_type": "onSelling",
            "avg_evaluation_rating": "4.6",
            "product_id": 1005008557811111,
        },
    }

    merged = connector._merge_listing_with_detail(listing, detail, "1005008557811111")

    assert merged.title_raw.startswith("AMD Ryzen 9 5950X")
    assert merged.price == Decimal("261.59")
    assert merged.in_stock is True
    assert merged.variant_normalized is not None
    assert merged.variant_normalized["aliexpress_source_lane"] == "ds"
    assert merged.variant_normalized["aliexpress_display_price"] == "261.59"
    assert merged.variant_normalized["aliexpress_original_price"] == "379.12"
    assert merged.variant_normalized["aliexpress_rating"] == "4.6"
    assert merged.variant_normalized["aliexpress_sales"] == "48"


@pytest.mark.asyncio
async def test_aliexpress_connector_surfaces_ds_auth_failure() -> None:
    refresh_calls: list[dict[str, Any]] = []

    class FailingClient:
        async def get(
            self, url: Any, params: Any = None, headers: Any = None, timeout: Any = None
        ) -> Any:
            refresh_calls.append({"url": url, "params": params})
            assert url == "https://api-sg.aliexpress.com/rest/auth/token/refresh"
            raise httpx.HTTPStatusError(
                "403", request=httpx.Request("GET", url), response=httpx.Response(403)
            )

        async def post(
            self, url: Any, json: Any = None, headers: Any = None, data: Any = None
        ) -> Any:
            if (
                url == "https://api-sg.aliexpress.com/sync"
                and isinstance(data, dict)
                and data.get("method") == "aliexpress.affiliate.product.query"
            ):

                class Resp:
                    status_code = 200

                    def raise_for_status(self) -> Any:
                        return None

                    def json(self) -> Any:
                        return {
                            "items": [
                                {
                                    "productId": "1005008557811111",
                                    "title": "Ali CPU",
                                    "displayPrice": "199.99",
                                    "shippingCost": "4.99",
                                    "shopName": "SZCPU",
                                    "evaluateRate": "4.8",
                                    "orders": "123",
                                    "inStock": True,
                                    "currency": "GBP",
                                }
                            ]
                        }

                return Resp()
            raise AssertionError(url)

        async def aclose(self) -> Any:
            return None

    connector = AliExpressConnector(
        {
            "ds_refresh_token": "refresh-token",
            "ds_app_key": "app-key",
            "ds_app_secret": "app-secret",
        },
        http_client=cast(Any, FailingClient()),
    )
    with pytest.raises(ConnectorDegradedError) as exc_info:
        await connector.search("CPU", {"enrich_with_ds": True, "brave_discovery": False})
    err = exc_info.value
    assert err.status == ConnectorStatus.auth_failed
    assert err.connector_id == "aliexpress"
    assert len(refresh_calls) == 1
    refresh_params = refresh_calls[0]["params"]
    assert isinstance(refresh_params, dict)
    assert refresh_params["sign_method"] == "sha256"
    assert refresh_params["sign"] == connector._ds_system_sign(
        "/auth/token/refresh", refresh_params, "app-secret"
    )
    await connector.cleanup()


@pytest.mark.asyncio
async def test_aliexpress_connector_continues_when_affiliate_lane_fails(
    monkeypatch: Any,
) -> None:
    connector = AliExpressConnector({})

    async def failing_affiliate(query: str, filters: Any) -> Any:
        raise ConnectorDegradedError(
            status=ConnectorStatus.auth_failed,
            message="AliExpress affiliate search failed",
            connector_id="aliexpress",
            detail={"error": "missing credentials"},
        )

    async def brave_results(query: str, filters: Any) -> list[NormalizedListing]:
        return [
            NormalizedListing.model_validate(
                {
                    "source": "aliexpress",
                    "source_type": SourceType.RETAILER,
                    "source_listing_id": "1005008557811111",
                    "title_raw": "RTX 4070 Ti AliExpress",
                    "price": Decimal("599.99"),
                    "currency": "GBP",
                    "url": "https://www.aliexpress.com/item/1005008557811111.html",
                    "category": "gpu",
                    "variant_normalized": {"aliexpress_product_id": "1005008557811111"},
                }
            )
        ]

    async def no_manual(pids: list[str], filters: Any) -> list[NormalizedListing]:
        return []

    monkeypatch.setattr(connector, "_affiliate_search", failing_affiliate)
    monkeypatch.setattr(connector, "_brave_search", brave_results)
    monkeypatch.setattr(connector, "_manual_pid_search", no_manual)

    listings = await connector.search("RTX 4070 Ti")
    await connector.cleanup()

    assert len(listings) == 1
    assert listings[0].source_listing_id == "1005008557811111"
    assert listings[0].price == Decimal("599.99")
    assert listings[0].variant_normalized is not None
    assert listings[0].variant_normalized["aliexpress_product_id"] == "1005008557811111"


@pytest.mark.asyncio
async def test_overclockers_fails_fast_with_truthful_bot_blocked_status() -> None:
    connector = OverclockersConnector()
    with pytest.raises(ConnectorDegradedError) as exc_info:
        await connector.search("RTX 5070")
    err = exc_info.value
    assert err.status == ConnectorStatus.bot_blocked
    assert err.connector_id == "overclockers"
    detail = cast(dict[str, Any], err.detail)
    assert detail["url"] == "https://www.overclockers.co.uk"
    assert "WAF" in err.message
    await connector.cleanup()


@pytest.mark.asyncio
async def test_dell_uk_connector_parses_visible_listing_cards_and_registers_entry_point(
    monkeypatch: Any,
) -> None:
    html = """
    <html><body>
      <article>
        <h3><a href="//www.dell.com/en-uk/shop/laptops-2-in-1-pcs/dell-15-laptop/spd/dell-dc15250-laptop/cndc1525015sc_noac">Dell 15 Laptop</a></h3>
        <p>Order Code cndc1525015sc_noac</p>
        <p>Dell Price £398.99 Save £380.00 (49%)</p>
        <p>13th Gen Intel Core i5-1334U, 16 GB DDR5, 512 GB SSD, 15.6-in. display Full HD</p>
        <img src="/img/dell15.jpg" />
      </article>
      <article>
        <h3><a href="//www.dell.com/en-uk/shop/laptops-2-in-1-pcs/dell-16-plus-laptop/spd/dell-db16250-laptop/cndb1625006sc_noac?ref=variantstack">Dell 16 Plus Laptop</a></h3>
        <p>Order Code cndb1625006sc_noac</p>
        <p>Base model from £599.00</p>
        <p>Intel Core Ultra 7 256V, 16 GB LPDDR5X, 512 GB SSD, 16.0-in. display 2.5K</p>
      </article>
    </body></html>
    """

    class DummyPage:
        async def goto(self, url: Any, wait_until: Any = None, timeout: Any = None) -> Any:
            self.url = url

        async def wait_for_timeout(self, ms: Any) -> Any:
            return None

        async def content(self) -> Any:
            return html

    class DummyContext:
        async def new_page(self) -> Any:
            return DummyPage()

        async def close(self) -> Any:
            return None

    class DummyBrowserClient:
        async def new_context(self) -> Any:
            return DummyContext()

        async def close(self) -> Any:
            return None

    connector = DellUKConnector(browser_client=cast(Any, DummyBrowserClient()))
    listings = await connector.search(
        "laptops", {"listing_url": "https://www.dell.com/en-uk/search/laptops"}
    )
    await connector.cleanup()

    assert len(listings) == 2
    assert [listing.source for listing in listings] == ["dell_uk", "dell_uk"]
    assert [listing.source_listing_id for listing in listings] == [
        "cndc1525015sc_noac",
        "cndb1625006sc_noac",
    ]
    assert listings[0].price == Decimal("398.99")
    assert (
        listings[0].url
        == "https://www.dell.com/en-uk/shop/laptops-2-in-1-pcs/dell-15-laptop/spd/dell-dc15250-laptop/cndc1525015sc_noac"
    )
    assert listings[0].variant_normalized is not None
    assert listings[0].variant_normalized["ram_gb"] == 16
    assert listings[0].category == "laptop"
    assert listings[0].seller_or_store == "Dell UK"

    import importlib.metadata

    entry_points = {
        ep.name: ep.value for ep in importlib.metadata.entry_points(group="pricerecon.connectors")
    }
    assert entry_points["dell_uk"] == "pricerecon.connectors.dell_uk:DellUKConnector"


@pytest.mark.asyncio
async def test_watch_executor_records_non_empty_timeout_health(monkeypatch: Any) -> None:
    now = watch_executor.datetime.utcnow()
    watch = Watch(
        id=42,
        name="Overclockers GPU watch",
        query="RTX 5070",
        category="gpu",
        sources=[SourceConfig(connector="overclockers", config={})],
        filters=WatchFilters(
            price_max=None,
            min_seller_feedback=None,
            min_seller_feedback_pct=None,
        ),
        schedule=WatchSchedule(time_window=None),
        grouping=WatchGrouping(product_key=None),
        notifications=WatchNotification(
            webhook_url=None,
            telegram_bot_token=None,
            telegram_chat_id=None,
            discord_webhook_url=None,
        ),
        enabled=True,
        created_at=now,
        updated_at=now,
        last_check_at=None,
        status="active",
    )

    recorded: list[tuple[str, str, str | None, dict[str, object] | None]] = []

    class FakeConnector:
        async def initialize(self) -> Any:
            return None

        async def search(self, query: Any, connector_filters: Any) -> Any:
            raise httpx.ConnectTimeout("", request=httpx.Request("POST", "http://example.test/v1"))

        async def cleanup(self) -> Any:
            return None

    class FakeCursor:
        def execute(self, *args: Any, **kwargs: Any) -> Any:
            return None

        def fetchone(self) -> Any:
            return None

    class FakeConn:
        def cursor(self) -> Any:
            return FakeCursor()

        def commit(self) -> Any:
            return None

        def close(self) -> Any:
            return None

    class FakeDiffResult:
        has_events = False
        new_listings: list[Any] = []
        price_drops: list[Any] = []
        stock_changes: list[Any] = []
        listings_gone: list[Any] = []

    monkeypatch.setattr(watch_executor, "get_watch", lambda watch_id: watch)
    monkeypatch.setattr(
        watch_executor, "run_check", lambda *_args, **_kwargs: (True, FakeDiffResult(), [])
    )
    monkeypatch.setattr(watch_executor, "get_db", lambda: FakeConn())

    # Mock discover_connectors to return our fake connector class
    monkeypatch.setattr(
        "pricerecon.connectors.discover_connectors",
        lambda: {"overclockers": FakeConnector},
    )
    monkeypatch.setattr(
        watch_executor,
        "upsert_connector_health",
        lambda connector_id, status, last_error=None, details=None: recorded.append(
            (connector_id, status, last_error, details)
        ),
    )

    result = await watch_executor.execute_watch(42)

    assert result["success"] is True
    assert recorded[0][0] == "overclockers"
    assert recorded[0][1] == "timeout"
    assert recorded[0][2]
    assert recorded[0][2] != ""
    assert recorded[0][3] is not None
    assert recorded[0][3]["error_type"] == "ConnectTimeout"
