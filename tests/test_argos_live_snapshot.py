"""Regression test: argos parser must handle the REAL (unescaped) Camofox snapshot.

The checked-in JSON fixture was stored double-escaped (backslash-escaped quotes),
which accidentally matched an over-escaped regex. The live Camofox snapshot uses
plain quotes. This test guards against that regression.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from pricerecon.connectors.argos import ArgosConnector

FIXTURE = Path(__file__).parent / "fixtures" / "argos" / "camofox-laptop-live.txt"


def test_argos_parser_handles_real_live_camofox_snapshot() -> None:
    """The live snapshot from .251 Camofox must yield >0 listings."""
    html = FIXTURE.read_text()
    connector = ArgosConnector()
    listings = connector._parse_search_results(html)
    assert len(listings) > 0, "Live Camofox snapshot yielded 0 listings (regression)"
    # Spot-check a known shape: GBP price present
    priced = [listing for listing in listings if listing.price is not None]
    assert priced, "No listings with a price extracted"
    assert all(isinstance(listing.price, Decimal) for listing in priced)
    # Spot-check a source_listing_id derived from /product/<digits>
    with_ids = [listing for listing in listings if listing.source_listing_id]
    assert with_ids, "No listings with a /product/<id> source_listing_id"
