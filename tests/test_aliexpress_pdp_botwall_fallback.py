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
from pricerecon.connectors.aliexpress_browser import DiscoveryCard, card_offer, discovery_cards
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


def connector_for(discovery: str, pdps: dict[str, tuple[str, str]], connector_config=None):
    """Camofox transport: one discovery snapshot, one served URL per PDP.

    ``pdps`` maps a discovered pid to the ``(final_url, snapshot)`` the
    transport must serve for it; an unmapped pid fails the test loudly.
    """
    opened: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST" and request.url.path == "/tabs":
            opened.append(str(json.loads(request.content)["url"]))
            return httpx.Response(200, json={"id": "tab-1"})
        if request.method == "GET" and request.url.path.endswith("/snapshot"):
            url = opened[-1]
            if "/w/wholesale-" in url:
                payload = {"url": url, "snapshot": discovery, "truncated": False}
            else:
                pid = re.search(r"/item/(\d+)\.html", url)[1]
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
    connector, _ = connector_for(
        discovery, {WATCH_PID: (PUNISH_URL, PUNISH_STUB)}
    )
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
    discovery = (
        card_block(WATCH_PID, None, "￡287.57") + card_block(OTHER_PID, OTHER_TITLE, "￡311.59")
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
            claim
            for item in report.evidence
            for claim in item.claims
            if claim.field == "movement"
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
