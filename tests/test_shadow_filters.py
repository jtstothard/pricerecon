from decimal import Decimal

from pricerecon.core.watch_executor import (
    SHADOW_FILTER_PATTERN,
    evaluate_shadow_filters,
)
from pricerecon.models.listings import NormalizedListing, SourceType


FP_1424 = "For Mac Studio SSD for M1 Max M1 Ultra 512GB Upgrade PCB Circuit Board with Nand"
GENUINE_1415 = "Corsair AI Workstation 300 Desktop PC - AMD Strix Halo Ryzen AI Max 395+ 128GB UNIFIED RAM 4TB SSD"
GENUINE_1416 = "Gmktec Evo-X2 AMD Ryzen 395+ 128GB RAM, 1TB mini pc"


def listing(title, price: Decimal | None = Decimal("695")):
    return NormalizedListing(
        source="test", source_type=SourceType.MARKETPLACE,
        source_listing_id="fixture", title_raw=title, price=price,
        currency="GBP", url="https://example.test/item",
    )


def test_p1_fixture_matrix():
    import re

    assert re.search(SHADOW_FILTER_PATTERN, FP_1424.casefold())
    assert not re.search(SHADOW_FILTER_PATTERN, GENUINE_1415.casefold())
    assert not re.search(SHADOW_FILTER_PATTERN, GENUINE_1416.casefold())


def test_price_floor_strict_less_than_and_missing_price_review(caplog):
    caplog.set_level("INFO")
    exact = listing("complete system", Decimal("2000"))
    below = listing("complete system", Decimal("1999.99"))
    missing = listing("complete system", None)
    entries = evaluate_shadow_filters([exact, below, missing], {"min_price_gbp": 2000}, 21)
    assert len(entries) == 2
    assert entries[0]["price"] == "1999.99"
    assert entries[1]["review"] == "missing_price"
    assert "shadow_filter" in caplog.text


def test_shadow_evaluation_never_removes_listings():
    items = [listing(FP_1424), listing(GENUINE_1415, Decimal("2500"))]
    assert len(items) == 2
    assert len(evaluate_shadow_filters(items, {"min_price_gbp": 2000}, 21)) == 1
    assert len(items) == 2