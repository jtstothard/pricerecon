"""Regression diagnosis for the live Argos Camofox response shape."""

import json
from pathlib import Path

from pricerecon.connectors.argos import ArgosConnector


FIXTURE = Path(__file__).parent / "fixtures" / "argos" / "camofox-laptop-snapshot.json"


def test_argos_live_camofox_snapshot_has_listings() -> None:
    """The real Camofox search response must produce product listings.

    This is intentionally RED on the current implementation: Camofox returns
    an accessibility snapshot (text), while the parser only accepts rendered
    HTML anchors and therefore returns zero listings.
    """
    payload = json.loads(FIXTURE.read_text())
    listings = ArgosConnector()._parse_search_results(payload["snapshot"])

    assert len(listings) > 0
    # The parser may surface promotional blocks (e.g. "Microsoft 365. McAfee")
    # before real products. Assert the Lenovo listing exists anywhere in the
    # results, not necessarily at index 0.
    lenovo = [l for l in listings if l.source_listing_id == "7816905"]
    assert len(lenovo) == 1, f"Lenovo IdeaPad 7816905 not found in {len(listings)} listings"
    assert "Lenovo IdeaPad" in lenovo[0].title_raw
    assert str(lenovo[0].price) == "349.00"
