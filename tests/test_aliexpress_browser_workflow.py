import json
from decimal import Decimal

import httpx
import pytest

from pricerecon.connectors.aliexpress import AliExpressConnector
from pricerecon.connectors.external_browser import ExternalBrowserAdapter
from pricerecon.connectors.status import ConnectorDegradedError
from pricerecon.models import VariantMatchConfidence

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


def connector_for(
    html, *, truncated=False, status=200, discovery_html=None, pdp_html=None, config=None
):
    calls = []

    def handler(request):
        # Any unapproved affiliate, DS, HTTP or discovery fallback fails this test.
        assert request.url.host == "browser.test"
        body = json.loads(request.content)
        calls.append(body["url"])
        if "/w/wholesale-" in body["url"]:
            content = discovery_html or (
                f'<a href="{URL}">ML05</a><a href="https://evil.test/item/1005007071090999.html">trap</a>'
            )
        else:
            pid = body["url"].split("/item/", 1)[1].split(".", 1)[0]
            content = (pdp_html or {}).get(pid, html)
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
        config, http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler))
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
        evidence = row.variant_normalized["browser_evidence"]
        assert evidence["shipping_claim"] == "0"
        # This price *is* bound to the selected SKU, so it is a deal price.
        assert evidence["price_scope"] == "selected_variation"
        assert "DISPLAYED_PRICE_UNBOUND_TO_SKU" not in (row.risk_flags or [])
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


UNBOUND_PDP = """<h1>Militado ML05 38mm Wristwatch</h1>
<span class="price--currentPriceText--live">￡35.82</span>
<input name="quantity" value="1">Deliver to: United Kingdom"""


async def test_capped_inspection_is_partial_success_not_degradation():
    second = '<a href="https://www.aliexpress.com/item/1005007071090777.html">ML05 alt</a>'
    discovery = f'<a href="{URL}">ML05</a>{second}<a href="https://evil.test/item/1005007071090999.html">trap</a>'
    connector, calls = connector_for(selected_offer(), discovery_html=discovery)
    try:
        rows = await connector.search(
            "Militado ML05", {"browser_variant": {}, "browser_max_products": 1}
        )
        report = connector._last_browser_report
        assert report.capped is True  # 2 discovered > limit 1: partial success now
        assert report.discovered_count == 2 and report.inspected_count == 1
        assert len(rows) == 1 and rows[0].price == Decimal("42.00")
        assert calls.count(URL) == 1  # only the bounded target's PDP was opened
    finally:
        await connector.cleanup()
        await connector._client.aclose()


async def test_unrequested_dimensions_and_absent_sku_warn_without_gating():
    connector, _ = connector_for(UNBOUND_PDP)
    try:
        rows = await connector.search("Militado ML05", {"browser_max_products": 1})
        assert len(rows) == 1
        evidence = rows[0].variant_normalized["browser_evidence"]
        assert evidence["selected_sku"] is None
        assert "selected_sku_unverified" in evidence["verification_warnings"]
        assert "strap_unverified" in evidence["verification_warnings"]
        assert "uk_destination_unverified" not in evidence["verification_warnings"]
        assert rows[0].source_listing_id == f"{PID}:pdp"
    finally:
        await connector.cleanup()
        await connector._client.aclose()


async def test_explicit_multi_unit_quantity_is_fatal():
    html = selected_offer().replace('name="quantity" value="1"', 'name="quantity" value="2"')
    connector, _ = connector_for(html)
    try:
        with pytest.raises(ConnectorDegradedError):
            await connector.search("Militado ML05", {"browser_max_products": 1})
    finally:
        await connector.cleanup()
        await connector._client.aclose()


def test_compound_title_matches_via_substring_fallback():
    connector = AliExpressConnector()
    # "watch" inside "Wristwatch" is a tokenisation artefact, so word tokens
    # keep the substring fallback …
    assert connector._title_matches_query("Militado ML05 Wristwatch", "Militado ML05 watch")
    assert connector._title_match_kind("Militado ML05 Wristwatch", "Militado ML05 watch") == (
        "substring"
    )
    # … but a model reference never does: "ml05" must not swallow "ml05S".
    assert not connector._title_matches_query("Militado ML05S Wristwatch", "Militado ML05 watch")
    assert connector._title_match_kind("Militado ML05S Wristwatch", "Militado ML05 watch") == (
        "none"
    )
    assert connector._title_matches_query("SAN MARTIN SN0150-G3 automatic", "San Martin SN0150")
    assert not connector._title_matches_query("Tissot Le Locle Powermatic", "San Martin SN0150")
    assert not connector._title_matches_query(None, "San Martin SN0150")
    assert connector._title_matches_query("anything", "the and for")  # no strong tokens


# The frozen catalogue holds two explicitly distinct Proxima listings on one
# base reference: PX1692-YunS (product_id=497, $475, G meteorite dial) and
# PX1692-ST (product_id=522, $266, Seagull ST1902). Neither may answer for
# the other, through either the word-boundary or the substring path.
YUNS_TITLE = "Proxima PX1692-YUNS ST1902 Meteorite Dial 39mm Mechanical Chronograph Watch"
ST_TITLE = "Proxima PX1692-ST ZHU TU ST1902 Hand-Wound Chronograph 39mm Watch"


def test_sibling_model_reference_never_cross_matches():
    connector = AliExpressConnector()
    assert not connector._title_matches_query(ST_TITLE, "Proxima PX1692-YunS")
    assert not connector._title_matches_query(YUNS_TITLE, "Proxima PX1692-ST")
    # Spaced query form: "YunS"/"ST" are below the strong-token bar, so the
    # shared base reference must not be enough on its own.
    assert not connector._title_matches_query(ST_TITLE, "Proxima PX1692 YunS")
    assert not connector._title_matches_query(YUNS_TITLE, "Proxima PX1692 ST")
    # The intended one still matches, in both spellings.
    assert connector._title_matches_query(YUNS_TITLE, "Proxima PX1692-YunS")
    assert connector._title_matches_query(YUNS_TITLE, "Proxima PX1692 YunS")
    assert connector._title_matches_query(ST_TITLE, "Proxima PX1692-ST")
    assert connector._title_matches_query(ST_TITLE, "Proxima PX1692 ST")


def test_short_reference_token_cannot_substring_match_unrelated_models():
    connector = AliExpressConnector()
    # The docstring's own example: "SN0150-G3" is short and reference-shaped,
    # so it may never be rescued by substring matching.
    assert connector._title_match_kind(
        "SAN MARTIN SN0150-G3 automatic", "San Martin SN0150-G3"
    ) == ("word")
    assert not connector._title_matches_query(
        "SAN MARTIN SN0150-G34 automatic", "San Martin SN0150-G3"
    )
    assert not connector._title_matches_query("SAN MARTIN SN0150 automatic", "San Martin SN0150-G3")
    assert not connector._title_matches_query(
        "Seagull ST1902 chronograph watch", "San Martin SN0150-G3"
    )


async def test_word_boundary_match_keeps_exact_high_confidence():
    connector, _ = connector_for(selected_offer())
    try:
        rows = await connector.search(
            "Militado ML05", {"browser_variant": VARIANT, "browser_max_products": 1}
        )
        row = rows[0]
        assert row.exact_variant_confirmed is True
        assert row.variant_match_confidence is VariantMatchConfidence.HIGH
        assert row.variant_normalized["browser_evidence"]["title_match"] == "word"
    finally:
        await connector.cleanup()
        await connector._client.aclose()


async def test_substring_only_match_downgrades_confidence_instead_of_claiming_exactness():
    html = selected_offer().replace(
        "<h1>Militado ML05 38mm watch</h1>", "<h1>Militado ML05 Wristwatch 38mm</h1>"
    )
    connector, _ = connector_for(html)
    try:
        rows = await connector.search(
            "Militado ML05 watch", {"browser_variant": VARIANT, "browser_max_products": 1}
        )
        row = rows[0]
        # A fuzzy match must not be labelled an exact variant confirmation:
        # deal alerts would otherwise assert an exactness never established.
        assert row.exact_variant_confirmed is False
        assert row.variant_match_confidence is VariantMatchConfidence.MEDIUM
        assert row.variant_normalized["browser_evidence"]["title_match"] == "substring"
    finally:
        await connector.cleanup()
        await connector._client.aclose()


async def test_displayed_price_without_sku_binding_is_flagged_as_not_a_deal_price():
    connector, _ = connector_for(UNBOUND_PDP)
    try:
        rows = await connector.search("Militado ML05", {"browser_max_products": 1})
        row = rows[0]
        evidence = row.variant_normalized["browser_evidence"]
        assert row.risk_flags is not None
        assert "DISPLAYED_PRICE_UNBOUND_TO_SKU" in row.risk_flags
        assert evidence["price_scope"] == "display_unbound"
    finally:
        await connector.cleanup()
        await connector._client.aclose()
