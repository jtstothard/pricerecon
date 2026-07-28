from decimal import Decimal

from pricerecon.core.watch_executor import (
    SHADOW_FILTER_PATTERN,
    apply_component_pattern_filter,
    evaluate_shadow_filters,
)
from pricerecon.models.listings import NormalizedListing, SourceType
from pricerecon.models.watches import WatchFilters

FP_1424 = "For Mac Studio SSD for M1 Max M1 Ultra 512GB Upgrade PCB Circuit Board with Nand"
GENUINE_1415 = "Corsair AI Workstation 300 Desktop PC - AMD Strix Halo Ryzen AI Max 395+ 128GB UNIFIED RAM 4TB SSD"
GENUINE_1416 = "Gmktec Evo-X2 AMD Ryzen 395+ 128GB RAM, 1TB mini pc"


def listing(title, price: Decimal | None = Decimal("695")):
    return NormalizedListing(
        source="test",
        source_type=SourceType.MARKETPLACE,
        source_listing_id="fixture",
        title_raw=title,
        price=price,
        currency="GBP",
        url="https://example.test/item",
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


def test_guardrail_matrix_canonical_alert_titles_pattern_only(caplog):
    """Integration guardrail: the P1 title pattern classifies correctly.

    With no price floor, only the title-structure pattern is evaluated.
    Alert 1424 (AliExpress SSD PCB) must match; genuine alerts 1415
    (Corsair Strix Halo system) and 1416 (Gmktec Evo-X2) must not.
    """
    caplog.set_level("INFO")
    fixtures = [
        listing(FP_1424, Decimal("695")),  # alert 1424 — known false positive
        listing(GENUINE_1415, Decimal("2500")),  # alert 1415 — genuine system
        listing(GENUINE_1416, Decimal("1800")),  # alert 1416 — genuine system
    ]
    filters = {"component_subject_pattern": SHADOW_FILTER_PATTERN}
    entries = evaluate_shadow_filters(fixtures, filters, 21)

    # Only the 1424 title should match the component-subject pattern.
    assert len(entries) == 1
    assert entries[0]["title"] == FP_1424
    assert "component_pattern" in str(entries[0]["which_filter_matched"])
    assert "shadow_filter" in caplog.text


def test_guardrail_floor_rejects_1424_price_pattern_rejects_1424_title():
    """Watch-21 floor (£2,000) plus P1 pattern: alert 1424 at £695 matches both."""
    entries = evaluate_shadow_filters(
        [listing(FP_1424, Decimal("695"))],
        {"min_price_gbp": 2000, "component_subject_pattern": SHADOW_FILTER_PATTERN},
        21,
    )
    assert len(entries) == 1
    assert entries[0]["which_filter_matched"] == "both"
    assert entries[0]["floor_value"] == 2000


# --- Enforcement tests ---


def _filters_enforce():
    return WatchFilters()


def test_enforcement_suppresses_component_listing_1424():
    """apply_component_pattern_filter removes the 1424 SSD PCB listing."""
    result = apply_component_pattern_filter([listing(FP_1424)], _filters_enforce())
    assert result == [], "1424 component listing should be suppressed"


def test_enforcement_keeps_genuine_systems_1415_1416():
    """apply_component_pattern_filter passes genuine Strix Halo systems through."""
    result = apply_component_pattern_filter(
        [listing(GENUINE_1415), listing(GENUINE_1416)], _filters_enforce()
    )
    assert len(result) == 2, "genuine systems 1415/1416 should survive"


def test_enforcement_off_passes_everything():
    """With enforce_component_pattern=False, even component listings survive."""
    filters = WatchFilters(enforce_component_pattern=False)
    result = apply_component_pattern_filter([listing(FP_1424)], filters)
    assert len(result) == 1, "enforcement off should pass component listings through"
