"""Live-captured AliExpress PDP enrichment regression tests.

The snapshots under ``tests/fixtures/aliexpress/`` were captured from the
production ``aliexpress_camofox`` transport on 2026-11-04 (see
``capture_summary.json``): ``GET /tabs/{id}/snapshot?format=text`` accessibility
trees, exactly what ``parse_offer`` receives on this lane. Nothing here is
hand-constructed markup. Provenance:

- ``pdp_1005009065415382.txt`` — San Martin SN0109 PDP (query "san martin gmt").
- ``discovery_san_martin_gmt.txt`` — its discovery page, 26 product PIDs, the
  fixture PDP is the first PID.
- ``pdp_1005009154171954.txt`` — Aqara sensor PDP whose selected row is a
  pack size ("Color: 1 piece"), which must never be recorded as a dial.

Discovery fixtures added for the two-cap regression cases, each labelled with
its own provenance header:

- ``discovery_two_pids_watch_first.txt`` — TRIMMED from the live discovery
  capture above (first two of its 26 product links, verbatim). Not itself a
  live capture.
- ``discovery_two_pids_sensor_first.txt`` — SYNTHETIC two-link assembly: the
  live Aqara sensor PDP's PID first (that PID is absent from the
  san-martin-gmt capture) and the live San Martin discovery link second, so the
  first candidate cannot qualify.
"""

from __future__ import annotations

import json
import re
from decimal import Decimal
from pathlib import Path

import httpx
import pytest

from pricerecon.connectors.aliexpress import AliExpressConnector
from pricerecon.connectors.aliexpress_browser import parse_offer
from pricerecon.connectors.external_browser import (
    ExternalBrowserAdapter,
    ExternalBrowserResult,
    RenderedContent,
)

FIXTURES = Path(__file__).parent / "fixtures" / "aliexpress"
WATCH_PID = "1005009065415382"
SENSOR_PID = "1005009154171954"
QUERY = "san martin gmt"


def pdp_result(pid: str) -> ExternalBrowserResult:
    return ExternalBrowserResult(
        selected_backend="camofox",
        attempts=(),
        rendered=RenderedContent(
            final_url=f"https://www.aliexpress.com/item/{pid}.html",
            snapshot=(FIXTURES / f"pdp_{pid}.txt").read_text(),
            snapshot_truncated=False,
        ),
    )


def test_live_pdp_snapshot_extracts_enrichment_dimensions() -> None:
    """The six warning dimensions clear from a live PDP accessibility snapshot."""
    offer = parse_offer(WATCH_PID, pdp_result(WATCH_PID))
    assert offer.title is not None and offer.title.startswith("San Martin")
    assert offer.displayed_price == Decimal("287.57")
    assert offer.currency == "GBP"
    # unit_quantity: a labelled textbox, not a spinbutton (observed live).
    assert offer.quantity == 1
    # dial: the selected property row is the current selection.
    assert offer.selected_options["dial"] == "Black Steel"
    # movement/size: seller-asserted in the PDP h1 ("... 39mm NH34 ...").
    assert offer.selected_options["movement"] == "NH34"
    assert offer.selected_options["size"] == "39mm"
    # No variant requested for this query: the offer is fully qualified.
    assert offer.qualification_issues({}) == []
    warnings = offer.verification_warnings({})
    assert "unit_quantity_unverified" not in warnings
    # Honest residuals: no SKU and no "Ship to:" claim exist in this transport.
    assert "selected_sku_unverified" in warnings
    assert "uk_destination_unverified" in warnings


def test_live_pack_size_color_row_is_never_recorded_as_dial() -> None:
    offer = parse_offer(SENSOR_PID, pdp_result(SENSOR_PID))
    assert offer.selected_options.get("dial") != "1 piece"
    assert not any(
        re.fullmatch(r"\d+\s?pieces?", value, re.IGNORECASE)
        for value in offer.selected_options.values()
    )


def test_live_variant_request_still_gates_on_missing_dimensions() -> None:
    """Enrichment must not weaken a requested-variant mismatch check."""
    offer = parse_offer(WATCH_PID, pdp_result(WATCH_PID))
    issues = offer.qualification_issues(
        {"movement": "VH31", "dial": "Blue", "strap": "Steel", "size": "38mm"}
    )
    assert "movement_mismatch" in issues
    assert "dial_mismatch" in issues
    assert "strap_unverified" in issues


def camofox_fixture_connector(handler, connector_config: dict | None = None) -> AliExpressConnector:
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
    return connector


def fixture_handler(
    opened: list[str],
    *,
    discovery: str = "discovery_san_martin_gmt.txt",
    pdps: dict[str, str] | None = None,
):
    """Camofox transport serving a discovery page and one PDP snapshot per PID.

    ``pdps`` maps a discovered PID to the snapshot filename the transport must
    serve for it; a PID without a mapping fails the test loudly instead of
    silently serving the wrong product. The default mirrors the original
    handler: the live San Martin PDP is the only PDP served.
    """
    current: dict[str, str] = {}
    snapshots: dict[str, str] = {WATCH_PID: f"pdp_{WATCH_PID}.txt"} if pdps is None else pdps

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST" and request.url.path == "/tabs":
            current["url"] = str(json.loads(request.content)["url"])
            opened.append(current["url"])
            return httpx.Response(200, json={"id": "tab-1"})
        if request.method == "GET" and request.url.path.endswith("/snapshot"):
            url = current["url"]
            if "/w/wholesale-" in url:
                snapshot = (FIXTURES / discovery).read_text()
            else:
                match = re.search(r"/item/(\d+)\.html", url)
                pid = match[1] if match else None
                if pid not in snapshots:
                    raise AssertionError(f"no PDP snapshot mapped for {url}")
                snapshot = (FIXTURES / snapshots[pid]).read_text()
            return httpx.Response(
                200,
                json={"url": url, "snapshot": snapshot, "truncated": False, "refsCount": 1},
            )
        if request.method == "DELETE":
            return httpx.Response(204)
        raise AssertionError(f"unexpected transport call: {request.url}")

    return handler


async def test_live_round_trip_reaches_a_qualified_listing() -> None:
    opened: list[str] = []
    connector = camofox_fixture_connector(fixture_handler(opened))
    try:
        rows = await connector.search(QUERY, {"browser_max_products": 1})
        report = connector._last_browser_report
        assert report.discovered_count >= 20
        assert report.inspected_count == 1
        qualified = [offer for offer in report.offers if not offer.qualification_issues({})]
        assert qualified, [offer.qualification_issues({}) for offer in report.offers]
        assert qualified[0].pid == WATCH_PID
        assert len(rows) == 1
        assert rows[0].price == Decimal("287.57")
        assert rows[0].url == f"https://www.aliexpress.com/item/{WATCH_PID}.html"
        variants = rows[0].variant_normalized
        assert isinstance(variants, dict)
        evidence = variants["browser_evidence"]
        assert isinstance(evidence, dict)
        assert evidence["quantity"] == 1
        options = evidence["selected_options"]
        assert isinstance(options, dict) and options["movement"] == "NH34"
        warnings = evidence["verification_warnings"]
        assert isinstance(warnings, list)
        assert "unit_quantity_unverified" not in warnings
        # Only the qualifying target's PDP was opened (cost bound).
        pdp_opens = [url for url in opened if "/item/" in url]
        assert pdp_opens == [f"https://www.aliexpress.com/item/{WATCH_PID}.html"]
    finally:
        await connector.cleanup()
        await connector._client.aclose()


async def test_early_exit_stops_opening_pdps_after_first_qualified_offer() -> None:
    opened: list[str] = []
    connector = camofox_fixture_connector(fixture_handler(opened))
    try:
        rows = await connector.search(QUERY, {"browser_max_products": 3})
        report = connector._last_browser_report
        # Three targets were allowed, but the first offer already qualified, so
        # no further PDP opens (each costs seconds and slider-captcha exposure).
        assert report.inspected_count == 1
        assert len([url for url in opened if "/item/" in url]) == 1
        assert rows
    finally:
        await connector.cleanup()
        await connector._client.aclose()


@pytest.mark.parametrize("pid", [WATCH_PID, SENSOR_PID])
def test_live_fixture_snapshots_are_complete_and_untruncated(pid: str) -> None:
    """A truncated live capture would silently weaken every assertion above."""
    snapshot = (FIXTURES / f"pdp_{pid}.txt").read_text()
    assert len(snapshot) > 5_000
    assert "heading" in snapshot
    assert pid != ""  # fixtures are addressed by real PIDs captured live


# --- Regression tests for the PR #169 review findings (MAJOR 1 / MAJOR 2) ---

# Evidence-lane authority for these synthetic transport runs; the report is
# built in-process and never leaves the test.
EVIDENCE_USE = {
    "permission_reference": "aliexpress live-capture fixtures 2026-11-04 (tests only)",
    "retention": "synthetic",
}
TWO_PID_DISCOVERY = "discovery_two_pids_watch_first.txt"
SENSOR_FIRST_DISCOVERY = "discovery_two_pids_sensor_first.txt"


async def test_early_exit_is_capped_from_inspected_not_planned_targets() -> None:
    """MAJOR 2: a run truncated by the early exit stays capped.

    The trimmed discovery fixture holds exactly two PIDs and
    ``browser_max_products`` allows two targets, so the planned-target cap
    (``len(targets) < len(pids)``) was False while only one PDP was opened.
    #168 requires that truncated run to stay capped and keep the
    ``product_inspection_capped`` receipt issue.
    """
    opened: list[str] = []
    handler = fixture_handler(opened, discovery=TWO_PID_DISCOVERY)
    connector = camofox_fixture_connector(handler, {"evidence_use": EVIDENCE_USE})
    try:
        report = await connector.search_with_evidence(QUERY, {"browser_max_products": 2})
        browser = connector._last_browser_report
        assert browser is not None
        # Discovery depth, plan depth and inspection depth deliberately differ.
        assert browser.discovered_count == 2
        assert browser.inspected_count == 1
        assert len([url for url in opened if "/item/" in url]) == 1
        # Discovered == planned (2 == 2), but inspected < discovered: capped.
        assert browser.capped is True
        receipt = report.source_evidence
        assert receipt is not None
        assert receipt.discovered_count == 2
        assert receipt.inspected_count == 1
        assert "product_inspection_capped" in receipt.issues
        assert receipt.completeness == "partial"
        assert report.completeness == "partial"
        assert len(report.evidence) == 1
    finally:
        await connector.cleanup()
        await connector._client.aclose()


async def test_inspection_loop_continues_past_a_conflicting_first_pdp() -> None:
    """The cost bound stops at a qualifying PDP, never before the next one.

    Discovery leads with a PID whose PDP cannot satisfy the requested movement,
    so the loop must open the second PDP as well; both discovered products are
    inspected and nothing is cut short (``capped is False``).
    """
    opened: list[str] = []
    handler = fixture_handler(
        opened,
        discovery=SENSOR_FIRST_DISCOVERY,
        pdps={
            SENSOR_PID: f"pdp_{SENSOR_PID}.txt",
            WATCH_PID: f"pdp_{WATCH_PID}.txt",
        },
    )
    connector = camofox_fixture_connector(handler)
    try:
        report = await connector.inspect_browser_search(
            QUERY,
            {"browser_max_products": 2, "browser_variant": {"movement": "NH34"}},
        )
        assert report.discovered_count == 2
        assert [offer.pid for offer in report.offers] == [SENSOR_PID, WATCH_PID]
        assert [url for url in opened if "/item/" in url] == [
            f"https://www.aliexpress.com/item/{SENSOR_PID}.html",
            f"https://www.aliexpress.com/item/{WATCH_PID}.html",
        ]
        assert report.inspected_count == 2
        # The first PDP conflicts with the query and the requested movement,
        # so it must not trigger the early exit.
        assert "query_title_mismatch" in report.offers[0].issues
        assert report.offers[0].qualification_issues({"movement": "NH34"})
        # The second PDP qualifies — proof the loop carried on to it.
        assert report.offers[1].qualification_issues({"movement": "NH34"}) == []
        assert report.offers[1].selected_options["movement"] == "NH34"
        # Two inspected == two discovered: this run is not capped.
        assert report.capped is False
    finally:
        await connector.cleanup()
        await connector._client.aclose()


async def test_title_derived_claims_declare_seller_provenance() -> None:
    """MAJOR 1: seller copy is never graded as a visible observation.

    ``movement`` and ``size`` are read out of the seller-authored PDP title on
    this capture, while ``dial`` comes from a displayed selection control.
    """
    opened: list[str] = []
    connector = camofox_fixture_connector(fixture_handler(opened), {"evidence_use": EVIDENCE_USE})
    try:
        report = await connector.search_with_evidence(QUERY, {"browser_max_products": 1})
        browser = connector._last_browser_report
        assert browser is not None
        watch = next(offer for offer in browser.offers if offer.pid == WATCH_PID)
        evidence = next(item for item in report.evidence if item.source_listing_id == WATCH_PID)
        claims = {claim.field: claim for claim in evidence.claims}
        # Title-derived selection: seller-authored copy, not an observation.
        assert claims["movement"].value == "NH34"
        assert claims["movement"].issuer == "AliExpress product title"
        assert claims["movement"].issuer_kind == "seller"
        # A genuinely displayed control keeps the observation grade.
        assert claims["dial"].issuer == "AliExpress displayed control"
        assert claims["dial"].issuer_kind == "visible_observation"
        assert claims["item_price"].issuer_kind == "visible_observation"
        # ``size`` is title-derived too. It is not an IdentityField, so the
        # report carries no size claim at all — its provenance is observable
        # only on the offer, never as an invented field.
        assert {"movement", "size"} <= set(watch.title_derived)
        assert watch.selected_options["size"] == "39mm"
        assert "size" not in claims
        assert "strap" not in claims  # no strap control on this capture
    finally:
        await connector.cleanup()
        await connector._client.aclose()
