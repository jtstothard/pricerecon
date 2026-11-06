"""PDP bot-wall fallback: AliExpress walls product pages, never the search page.

Root cause evidence (live, 2026-11-06): AliExpress's TMD risk control serves
``…/item/<pid>.html/_____tmd_____/punish?x5secdata=…`` in place of a product
page — a 484-byte accessibility stub with no title and no price — while the
search page keeps rendering full cards (title + ``￡`` price beside each
product link). Waiting does not clear it (still a stub at t=20s), so the
connector falls back to the search card instead, with every gate unchanged:
``query_title_mismatch`` still decides on the card's own title, and a GBP
price is still required.
"""

from __future__ import annotations

import json
import re
from decimal import Decimal
from pathlib import Path

import httpx
import pytest

from pricerecon.connectors.aliexpress import AliExpressConnector
from pricerecon.connectors.aliexpress_browser import (
    DiscoveryCard,
    card_offer,
    discovery_cards,
    product_price_text,
)
from pricerecon.connectors.external_browser import (
    ExternalBrowserAdapter,
    ExternalBrowserResult,
    RenderedContent,
)
from pricerecon.connectors.status import ConnectorDegradedError

FIXTURES = Path(__file__).parent / "fixtures" / "aliexpress"
QUERY = "San Martin SN0129 Aventurine"
WATCH_PID = "1005006501023993"
OTHER_PID = "1005008183553198"
WATCH_TITLE = (
    "San Martin 39mm Aventurine Gemstone Dial Luxury Men's Watch NH34 GMT "
    "Automatic Mechanical Sapphire Waterproof Luminous SN0129"
)
OTHER_TITLE = (
    "San Martin New SN0129 39mm Men Automatic Watch Aventurine Dial NH35 "
    "Waterproof 100m Luminous"
)
PUNISH_URL = f"https://www.aliexpress.com//item/{WATCH_PID}.html/_____tmd_____/punish?x5secdata=abc"
# Verbatim shape of the live 484-byte stub (iframe + feedback link, no heading).
PUNISH_STUB = (
    "- iframe\n"
    "- img\n"
    '- link "Click to feedback >" [e1]:\n'
    "  - /url: https://www.aliexpress.com//item/PID/_____tmd_____/page/feedback\n"
)

EVIDENCE_USE = {
    "permission_reference": "synthetic transport for the bot-wall fallback tests (tests only)",
    "retention": "synthetic",
}


def card_block(pid: str, title: str | None, price: str) -> str:
    """A search-card block in the live camofox snapshot shape."""
    if title is None:
        return (
            f'- link "product {price}" [e10]:\n'
            f"  - /url: https://www.aliexpress.com/item/{pid}.html?pdp_ext_f=1\n"
            f'  - img "product"\n'
            f"  - text: {price}\n"
        )
    return (
        f'- link "Report fraud item {title} {price} 4.5 115 sold Save ￡287.36 Free shipping":\n'
        f"  - /url: //www.aliexpress.com/item/{pid}.html?algo_pvid=abc\n"
        f'  - heading "{title}" [level=3]\n'
        f"  - text: {price} 4.5 115 sold Save ￡287.36 Free shipping\n"
    )


def good_pdp_snapshot(title: str, price: str) -> str:
    return (
        f'- heading "{title}" [level=1]\n'
        f"- text: {price}\n"
        "- text: Shipping: Free. Deliver to: United Kingdom. Price includes VAT\n"
    )


def connector_for(
    discovery: str, pdps: dict[str, tuple[str, str]], connector_config=None, fail_tabs_pids=()
):
    """Camofox transport: one discovery snapshot, one served URL per PDP.

    ``pdps`` maps a discovered pid to the ``(final_url, snapshot)`` the
    transport must serve for it; an unmapped pid fails the test loudly.
    ``fail_tabs_pids`` makes the tab open for that pid fail hard (500).
    """
    opened: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST" and request.url.path == "/tabs":
            url = str(json.loads(request.content)["url"])
            for pid in fail_tabs_pids:
                if f"/item/{pid}.html" in url:
                    return httpx.Response(500, text="camofox exploded")
            opened.append(url)
            return httpx.Response(200, json={"id": "tab-1"})
        if request.method == "GET" and request.url.path.endswith("/snapshot"):
            url = opened[-1]
            if "/w/wholesale-" in url:
                payload = {"url": url, "snapshot": discovery, "truncated": False}
            else:
                match = re.search(r"/item/(\d+)\.html", url)
                assert match is not None
                pid = match.group(1)
                assert pid in pdps, f"no PDP mapped for {url}"
                final_url, snapshot = pdps[pid]
                payload = {"url": final_url, "snapshot": snapshot, "truncated": False}
            return httpx.Response(200, json=payload)
        if request.method == "DELETE":
            return httpx.Response(204)
        raise AssertionError(f"unexpected transport call: {request.url}")

    config = {
        "browser_backends": {
            "camo": {
                "type": "camofox",
                "endpoint": "http://camofox.test",
                "options": {"user_id": "pricerecon-aliexpress"},
            }
        },
        "browser_default": "camo",
    }
    connector = AliExpressConnector(
        connector_config,
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )
    connector.configure_external_browser(config)
    connector._external_browser = ExternalBrowserAdapter.from_config(
        config,
        session_scope=connector.connector_id,
        client_factory=lambda **kw: httpx.AsyncClient(transport=httpx.MockTransport(handler), **kw),
    )
    return connector, opened


async def test_walled_pdp_falls_back_to_the_search_card_without_touching_gates():
    discovery = card_block(WATCH_PID, WATCH_TITLE, "￡299.49")
    connector, _ = connector_for(discovery, {WATCH_PID: (PUNISH_URL, PUNISH_STUB)})
    try:
        rows = await connector.search(QUERY, {"browser_max_products": 1})
        assert len(rows) == 1
        row = rows[0]
        assert row.title_raw == WATCH_TITLE
        assert row.price == Decimal("299.49") and row.currency == "GBP"
        evidence = row.variant_normalized["browser_evidence"]
        assert evidence["inspection_source"] == "discovery_card"
        assert "pdp_blocked_search_result_price" in evidence["verification_warnings"]
        # The card's title was graded against the query exactly as a PDP's.
        assert evidence["title_match"] == "word"
        assert "query_title_mismatch" not in evidence["issues"]
        assert row.risk_flags is not None and "PDP_NOT_INSPECTED" in row.risk_flags
    finally:
        await connector.cleanup()
        await connector._client.aclose()


async def test_card_title_is_still_gated_by_query_title_mismatch():
    """A bot wall must never launder an unrelated card into a listing."""
    discovery = card_block(WATCH_PID, WATCH_TITLE, "￡299.49")
    connector, _ = connector_for(discovery, {WATCH_PID: (PUNISH_URL, PUNISH_STUB)})
    try:
        with pytest.raises(ConnectorDegradedError) as error:
            await connector.search("Proxima PX1756", {"browser_max_products": 1})
        assert error.value.status.value == "parse_error"
        assert error.value.detail["reason"] == "unqualified_browser_offer"
        issues = error.value.detail["issues"]
        assert issues and all("query_title_mismatch" in offer for offer in issues)
    finally:
        await connector.cleanup()
        await connector._client.aclose()


async def test_walled_pdp_without_a_usable_card_still_fails_to_parse():
    """No card title to grade means no listing — the old failure, unchanged."""
    discovery = card_block(WATCH_PID, None, "￡287.57")
    connector, _ = connector_for(discovery, {WATCH_PID: (PUNISH_URL, PUNISH_STUB)})
    try:
        with pytest.raises(ConnectorDegradedError) as error:
            await connector.search(QUERY, {"browser_max_products": 1})
        assert error.value.status.value == "parse_error"
        assert error.value.detail["reason"] == "unqualified_browser_offer"
        assert any("product_title_unresolved" in offer for offer in error.value.detail["issues"])
    finally:
        await connector.cleanup()
        await connector._client.aclose()


async def test_one_walled_sibling_no_longer_sinks_a_qualified_offer():
    """parse_error must mean *nothing* qualified, not *something* didn't."""
    discovery = card_block(WATCH_PID, None, "￡287.57") + card_block(
        OTHER_PID, OTHER_TITLE, "￡311.59"
    )
    connector, _ = connector_for(
        discovery,
        {
            WATCH_PID: (PUNISH_URL, PUNISH_STUB),
            OTHER_PID: (
                f"https://www.aliexpress.com/item/{OTHER_PID}.html",
                good_pdp_snapshot(OTHER_TITLE, "￡311.59"),
            ),
        },
    )
    try:
        rows = await connector.search(QUERY, {"browser_max_products": 2})
        assert [row.source_listing_id for row in rows] == [f"{OTHER_PID}:pdp"]
        assert rows[0].price == Decimal("311.59")
        report = connector._last_browser_report
        assert report is not None and report.inspected_count == 2
    finally:
        await connector.cleanup()
        await connector._client.aclose()


async def test_evidence_lane_points_card_claims_at_the_search_page():
    discovery = card_block(WATCH_PID, WATCH_TITLE, "￡299.49")
    connector, _ = connector_for(
        discovery,
        {WATCH_PID: (PUNISH_URL, PUNISH_STUB)},
        {"evidence_use": EVIDENCE_USE},
    )
    try:
        report = await connector.search_with_evidence(
            QUERY, {"browser_max_products": 1, "evidence_use": EVIDENCE_USE}
        )
        assert len(report.listings) == 1
        assert report.listings[0].price == Decimal("299.49")
        claim = next(
            claim
            for item in report.evidence
            for claim in item.claims
            if claim.field == "item_price"
        )
        # The product page was never observed, so the claim does not point at it.
        assert claim.issuer == "AliExpress search result price"
        assert claim.pointer.startswith("https://www.aliexpress.com/w/wholesale-")
        movement = next(
            claim for item in report.evidence for claim in item.claims if claim.field == "movement"
        )
        assert movement.issuer == "AliExpress product title"
        assert movement.issuer_kind == "seller"
    finally:
        await connector.cleanup()
        await connector._client.aclose()


def test_live_discovery_cards_carry_title_and_price() -> None:
    """The live capture's cards parse, including the title-less earlier block."""
    result = ExternalBrowserResult(
        selected_backend="camofox",
        attempts=(),
        rendered=RenderedContent(
            snapshot=(FIXTURES / "discovery_san_martin_gmt.txt").read_text(),
            snapshot_truncated=False,
        ),
    )
    cards = discovery_cards(result)
    card = cards["1005009065415382"]
    assert card.usable
    assert card.title is not None and card.title.startswith("San Martin 39mm NH34 Mechanical GMT")
    assert card.price_text == "￡287.57"


def test_titleless_card_is_never_usable_fallback_evidence() -> None:
    result = ExternalBrowserResult(
        selected_backend="camofox",
        attempts=(),
        rendered=RenderedContent(
            snapshot=card_block(WATCH_PID, None, "￡287.57"),
            snapshot_truncated=False,
        ),
    )
    card = discovery_cards(result)[WATCH_PID]
    assert not card.usable


def test_card_offer_claims_nothing_the_card_did_not_show() -> None:
    card = DiscoveryCard(WATCH_PID, WATCH_TITLE, "￡299.49")
    offer = card_offer(WATCH_PID, card)
    assert offer.inspection_source == "discovery_card"
    assert offer.displayed_price == Decimal("299.49") and offer.currency == "GBP"
    assert offer.selected_sku is None and offer.price_bound_to_sku is False
    assert offer.destination is None and offer.quantity is None
    # Seller copy read off the card, graded as such, never as a control.
    assert offer.selected_options.get("movement") == "NH34"
    assert offer.title_derived == frozenset({"movement", "size"})
    assert offer.qualification_issues({}) == []
    assert offer.qualification_issues({"movement": "VH31"}) == ["movement_mismatch"]


def test_product_price_text_skips_savings_and_coupon_badges() -> None:
    """A badge figure is never the product price; only a non-badge money is."""
    # Price-first live shape must stay correct (regression guard).
    assert product_price_text(["￡299.49 4.5 115 sold Save ￡287.36 Free shipping"]) == "￡299.49"
    # Badge-first shape: the Save line must not win.
    assert product_price_text(["Save ￡287.36", "￡299.49 4.5 115 sold"]) == "￡299.49"
    # Title-coupon shape: the coupon inside the title must not win.
    assert (
        product_price_text(["Watch SN0129 ￡50 Coupon 1111 Sale ￡299.49 4.5 sold"]) == "￡299.49"
    )
    for badge in [
        "Save ￡10.00",
        "Saved ￡10.00",
        "Saving ￡10.00",
        "Was ￡10.00",
        "Were ￡10.00",
        "Off ￡10.00",
        "Discount ￡10.00",
        "Coupon ￡10.00",
        "-￡10.00",
        "Was -￡10.00",
        "￡10.00 Off",
        "￡10.00 Coupon",
        "￡10.00 discount",
    ]:
        assert product_price_text([badge]) is None, badge
        assert product_price_text([badge, "￡299.49 4.5 sold"]) == "￡299.49", badge


def test_badge_first_snapshot_card_prices_the_product_not_the_savings() -> None:
    """A `Save …` text line before the price line must not become the price."""
    snapshot = (
        f'- link "Report fraud item {WATCH_TITLE}":\n'
        f"  - /url: //www.aliexpress.com/item/{WATCH_PID}.html?x=1\n"
        f'  - heading "{WATCH_TITLE}" [level=3]\n'
        "  - text: Save ￡287.36\n"
        "  - text: ￡299.49 4.5 115 sold\n"
    )
    result = ExternalBrowserResult(
        selected_backend="camofox",
        attempts=(),
        rendered=RenderedContent(snapshot=snapshot, snapshot_truncated=False),
    )
    card = discovery_cards(result)[WATCH_PID]
    assert card.usable
    assert card.price_text == "￡299.49"
    offer = card_offer(WATCH_PID, card)
    assert offer.displayed_price == Decimal("299.49") and offer.currency == "GBP"


def test_title_coupon_html_card_prices_the_product_not_the_coupon() -> None:
    """A coupon figure inside the title must not become the price."""
    html = (
        f'<a href="//www.aliexpress.com/item/{WATCH_PID}.html?x=1">'
        f"<h3>{WATCH_TITLE} ￡50 Coupon 1111 Sale</h3>"
        "<span>￡299.49</span><span>4.5 sold</span></a>"
    )
    result = ExternalBrowserResult(
        selected_backend="cloakbrowser",
        attempts=(),
        rendered=RenderedContent(html=html),
    )
    card = discovery_cards(result)[WATCH_PID]
    assert card.usable
    assert card.price_text == "￡299.49"
    offer = card_offer(WATCH_PID, card)
    assert offer.displayed_price == Decimal("299.49") and offer.currency == "GBP"


def test_price_first_card_still_prices_the_product_in_both_branches() -> None:
    """The live price-first fixture shape must still parse to 299.49."""
    snapshot = (
        f'- link "Report fraud item {WATCH_TITLE} ￡299.49 4.5 115 sold Save ￡287.36 '
        f'Free shipping":\n'
        f"  - /url: //www.aliexpress.com/item/{WATCH_PID}.html?x=1\n"
        f'  - heading "{WATCH_TITLE}" [level=3]\n'
        "  - text: ￡299.49 4.5 115 sold Save ￡287.36 Free shipping\n"
    )
    result = ExternalBrowserResult(
        selected_backend="camofox",
        attempts=(),
        rendered=RenderedContent(snapshot=snapshot, snapshot_truncated=False),
    )
    card = discovery_cards(result)[WATCH_PID]
    assert card.price_text == "￡299.49"
    html = (
        f'<a href="//www.aliexpress.com/item/{WATCH_PID}.html?x=1">'
        f"<h3>{WATCH_TITLE}</h3>"
        "<span>￡299.49 4.5 115 sold Save ￡287.36 Free shipping</span></a>"
    )
    result = ExternalBrowserResult(
        selected_backend="cloakbrowser",
        attempts=(),
        rendered=RenderedContent(html=html),
    )
    assert discovery_cards(result)[WATCH_PID].price_text == "￡299.49"


def test_badge_only_card_is_dropped_never_priced_from_the_badge() -> None:
    """A card with only a savings/coupon badge has no usable price."""
    snapshot = (
        f'- link "Report fraud item {WATCH_TITLE}":\n'
        f"  - /url: //www.aliexpress.com/item/{WATCH_PID}.html?x=1\n"
        f'  - heading "{WATCH_TITLE}" [level=3]\n'
        "  - text: Save ￡287.36\n"
    )
    result = ExternalBrowserResult(
        selected_backend="camofox",
        attempts=(),
        rendered=RenderedContent(snapshot=snapshot, snapshot_truncated=False),
    )
    card = discovery_cards(result)[WATCH_PID]
    assert card.price_text is None
    assert not card.usable
    html = (
        f'<a href="//www.aliexpress.com/item/{WATCH_PID}.html?x=1">'
        f"<h3>{WATCH_TITLE} ￡50 Coupon 1111 Sale</h3></a>"
    )
    result = ExternalBrowserResult(
        selected_backend="cloakbrowser",
        attempts=(),
        rendered=RenderedContent(html=html),
    )
    card = discovery_cards(result)[WATCH_PID]
    assert card.price_text is None
    assert not card.usable


async def test_badge_only_card_never_becomes_a_listing() -> None:
    """End to end: no real product price means parse_error, never a badge price."""
    discovery = (
        f'- link "Report fraud item {WATCH_TITLE}":\n'
        f"  - /url: //www.aliexpress.com/item/{WATCH_PID}.html?algo_pvid=abc\n"
        f'  - heading "{WATCH_TITLE}" [level=3]\n'
        "  - text: Save ￡287.36\n"
    )
    connector, _ = connector_for(discovery, {WATCH_PID: (PUNISH_URL, PUNISH_STUB)})
    try:
        with pytest.raises(ConnectorDegradedError) as error:
            await connector.search(QUERY, {"browser_max_products": 1})
        assert error.value.status.value == "parse_error"
    finally:
        await connector.cleanup()
        await connector._client.aclose()


def test_brand_and_model_fragment_is_not_a_usable_card_title() -> None:
    """A designation ("San Martin SN0129") is not a product title."""
    assert not DiscoveryCard(WATCH_PID, "San Martin SN0129", "￡299.49").usable


async def test_evidence_report_carries_the_botwall_marker_for_fallback_offers() -> None:
    """F2: the evidence sink records that a fallback price came from the card."""
    discovery = card_block(WATCH_PID, WATCH_TITLE, "￡299.49")
    connector, _ = connector_for(
        discovery,
        {WATCH_PID: (PUNISH_URL, PUNISH_STUB)},
        {"evidence_use": EVIDENCE_USE},
    )
    try:
        report = await connector.search_with_evidence(
            QUERY, {"browser_max_products": 1, "evidence_use": EVIDENCE_USE}
        )
        source = report.evidence[0].source_evidence
        assert source is not None
        assert "pdp_blocked_search_result_price" in source.missing_fields
        assert source.inspection_source == "discovery_card"
        dump = report.model_dump_json()
        assert "pdp_blocked_search_result_price" in dump
        assert "discovery_card" in dump
    finally:
        await connector.cleanup()
        await connector._client.aclose()


async def test_degraded_navigation_on_one_product_does_not_sink_a_sibling() -> None:
    """One unreachable product must not sink a sibling that qualifies."""
    discovery = card_block(WATCH_PID, None, "￡287.57") + card_block(
        OTHER_PID, OTHER_TITLE, "￡311.59"
    )
    connector, _ = connector_for(
        discovery,
        {
            WATCH_PID: (PUNISH_URL, PUNISH_STUB),
            OTHER_PID: (
                f"https://www.aliexpress.com/item/{OTHER_PID}.html",
                good_pdp_snapshot(OTHER_TITLE, "￡311.59"),
            ),
        },
        fail_tabs_pids=(WATCH_PID,),
    )
    try:
        rows = await connector.search(QUERY, {"browser_max_products": 2})
        assert [row.source_listing_id for row in rows] == [f"{OTHER_PID}:pdp"]
        assert rows[0].price == Decimal("311.59")
    finally:
        await connector.cleanup()
        await connector._client.aclose()
