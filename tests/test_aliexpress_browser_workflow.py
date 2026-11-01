import json
from decimal import Decimal

import httpx
import pytest

from pricerecon.connectors.aliexpress import AliExpressConnector
from pricerecon.connectors.external_browser import ExternalBrowserAdapter
from pricerecon.connectors.status import ConnectorDegradedError

PID = "1005007071090465"
URL = f"https://www.aliexpress.com/item/{PID}.html"
VARIANT = {"movement": "VH31", "dial": "Blue", "strap": "Steel", "size": "38mm"}
CONFIG = {
    "browser_backends": {
        "browser": {
            "type": "cloakbrowser",
            "endpoint": "http://browser.test",
            "options": {"render_mode": "dom"},
        }
    },
    "browser_default": "browser",
}
CONFLICT = """<h1>Militado ML05 38mm VH31 watch</h1>
<div class="sku-item--property--live">Color: Grey with logo 2035</div>
<span class="price--currentPriceText--live">￡35.82</span>
<input name="quantity" value="1">Price includes VAT"""


def selected_offer(sku="1001", price_sku="1001", currency="£"):
    controls = "".join(
        f'<input type="radio" name="{k}" value="{v}" checked>' for k, v in VARIANT.items()
    )
    return f"""<h1>Militado ML05 38mm watch</h1>{controls}
    <input name="skuId" value="{sku}"><input name="quantity" value="1">
    <span class="price--currentPriceText--live" data-sku-id="{price_sku}">{currency}42.00</span>
    Deliver to: United Kingdom. Shipping: Free. Price includes VAT."""


def connector_for(html, *, truncated=False, status=200):
    calls = []

    def handler(request):
        # Any unapproved affiliate, DS, HTTP or discovery fallback fails this test.
        assert request.url.host == "browser.test"
        body = json.loads(request.content)
        calls.append(body["url"])
        if "/w/wholesale-" in body["url"]:
            content = f'<a href="{URL}">ML05</a><a href="https://evil.test/item/1005007071090999.html">trap</a>'
        else:
            content = html
        return httpx.Response(
            200,
            json={
                "navigated": True,
                "html": content,
                "htmlTruncated": truncated,
                "finalUrl": body["url"],
                "mainStatus": status,
                "networkInterceptionSupported": False,
            },
        )

    connector = AliExpressConnector(
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler))
    )
    connector.configure_external_browser(CONFIG)
    connector._external_browser = ExternalBrowserAdapter.from_config(
        CONFIG,
        session_scope=connector.connector_id,
        client_factory=lambda **kw: httpx.AsyncClient(transport=httpx.MockTransport(handler), **kw),
    )
    return connector, calls


async def test_discovery_follows_shared_browser_without_affiliate_and_preserves_conflict():
    connector, calls = connector_for(CONFLICT)
    try:
        report = await connector.inspect_browser_search(
            "Militado ML05", {"browser_max_products": 1}
        )
        assert report.discovered_count == 1
        offer = report.offers[0]
        assert offer.displayed_price == Decimal("35.82")
        assert offer.selected_options["movement"] == "2035"
        assert offer.selected_sku is None
        assert "movement_mismatch" in offer.qualification_issues(VARIANT)
        assert offer.total_landed_cost is None
        assert len(calls) == 2 and calls[-1] == URL
    finally:
        await connector.cleanup()
        await connector._client.aclose()


async def test_unresolved_offer_is_degraded_not_a_false_exact_match_or_empty_market():
    connector, _ = connector_for(CONFLICT)
    try:
        with pytest.raises(ConnectorDegradedError) as error:
            await connector.search(
                "Militado ML05", {"browser_variant": VARIANT, "browser_max_products": 1}
            )
        assert error.value.detail["reason"] == "unqualified_browser_offer"
        assert connector._last_browser_report.offers[0].displayed_price == Decimal("35.82")
    finally:
        await connector.cleanup()
        await connector._client.aclose()


async def test_bound_selected_sku_has_separate_identity_and_unknown_delivered_total():
    connector, _ = connector_for(selected_offer())
    try:
        rows = await connector.search(
            "Militado ML05", {"browser_variant": VARIANT, "browser_max_products": 1}
        )
        assert len(rows) == 1
        row = rows[0]
        assert row.source_listing_id == f"{PID}:1001"
        assert row.exact_variant_confirmed is True
        assert row.price == Decimal("42.00") and row.currency == "GBP"
        assert row.shipping_cost is None  # Free-shipping wording is only a claim.
        assert row.total_landed_cost is None
        assert row.variant_normalized["browser_evidence"]["shipping_claim"] == "0"
    finally:
        await connector.cleanup()
        await connector._client.aclose()


@pytest.mark.parametrize("html", [selected_offer(price_sku="9999"), selected_offer(currency="$")])
async def test_wrong_sku_price_or_ambiguous_currency_cannot_enter_comparison(html):
    connector, _ = connector_for(html)
    try:
        with pytest.raises(ConnectorDegradedError):
            await connector.search(
                "Militado ML05", {"browser_variant": VARIANT, "browser_max_products": 1}
            )
    finally:
        await connector.cleanup()
        await connector._client.aclose()


def test_query_tokens_preserve_uppercase_model_and_brand():
    connector = AliExpressConnector()
    assert connector._query_strong_tokens("Militado ML05") == ["militado", "ml05"]


@pytest.mark.parametrize("value", [0, 11, True, "1"])
async def test_inspection_limits_are_validated_before_network(value):
    connector, calls = connector_for(CONFLICT)
    try:
        with pytest.raises(ValueError):
            await connector.inspect_browser_search("Militado ML05", {"browser_max_products": value})
        assert calls == []
    finally:
        await connector._client.aclose()


@pytest.mark.parametrize("kwargs", [{"truncated": True}, {"status": 403}])
async def test_incomplete_or_blocked_browser_discovery_never_falls_back(kwargs):
    connector, calls = connector_for(CONFLICT, **kwargs)
    try:
        with pytest.raises(ConnectorDegradedError):
            await connector.search("Militado ML05", {"browser_variant": VARIANT})
        assert len(calls) == 1
    finally:
        await connector._client.aclose()


async def test_distinct_selected_skus_keep_distinct_listing_identity():
    ids = []
    for sku in ("1001", "1002"):
        connector, _ = connector_for(selected_offer(sku=sku, price_sku=sku))
        try:
            rows = await connector.search("Militado ML05", {"browser_variant": VARIANT})
            ids.append(rows[0].source_listing_id)
        finally:
            await connector._client.aclose()
    assert ids == [f"{PID}:1001", f"{PID}:1002"]


@pytest.mark.parametrize("complete", [None, True])
def test_snapshot_without_explicit_completeness_is_rejected(complete):
    from pricerecon.connectors.aliexpress_browser import discovery_ids
    from pricerecon.connectors.external_browser import ExternalBrowserResult, RenderedContent

    result = ExternalBrowserResult(
        selected_backend="camofox",
        attempts=(),
        rendered=RenderedContent(snapshot=f"- /url: {URL}", snapshot_truncated=complete),
    )
    with pytest.raises(ValueError, match="Partial"):
        discovery_ids(result)


def test_complete_snapshot_discovery_accepts_only_real_product_links():
    from pricerecon.connectors.aliexpress_browser import discovery_ids
    from pricerecon.connectors.external_browser import ExternalBrowserResult, RenderedContent

    result = ExternalBrowserResult(
        selected_backend="camofox",
        attempts=(),
        rendered=RenderedContent(
            snapshot=f"- /url: {URL}\n- /url: https://evil.test/item/1005007071090999.html\nProduct 1005007071090888",
            snapshot_truncated=False,
        ),
    )
    assert discovery_ids(result) == [PID]


def test_real_snapshot_quotes_preserve_selected_conflict_without_using_other_options():
    from pricerecon.connectors.aliexpress_browser import parse_offer
    from pricerecon.connectors.external_browser import ExternalBrowserResult, RenderedContent

    result = ExternalBrowserResult(
        selected_backend="camofox",
        attempts=(),
        rendered=RenderedContent(
            final_url=URL,
            snapshot_truncated=False,
            snapshot="""- heading "Militado ML05 VH31 watch" [level=1]
- text: ￡35.82
- text: "Color: Grey with logo 2035"
- img "Blue VH31"
- img "Grey with logo VH31"
- text: Price includes VAT""",
        ),
    )
    offer = parse_offer(PID, result)
    assert offer.selected_options == {"dial": "Grey with logo 2035", "movement": "2035"}
    assert "movement_mismatch" in offer.qualification_issues(VARIANT)
    assert offer.selected_sku is None
