from decimal import Decimal
from datetime import datetime

from pricerecon.core.hardware_routes import route_for_query, route_title_matches
from pricerecon.core.watch_executor import apply_post_normalization_filters
from pricerecon.models import NormalizedListing, SourceType, SpecMatch, WatchFilters


def listing(title: str) -> NormalizedListing:
    return NormalizedListing(
        source="cex",
        source_type=SourceType.RETAILER,
        source_listing_id=title,
        title_raw=title,
        price=Decimal("1000"),
        currency="GBP",
        url="https://example.test/item",
        timestamp_seen=datetime.utcnow(),
        product_normalized=None,
        variant_normalized=None,
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
        category=None,
    )


def test_glm_routes_have_strict_variant_and_source_allowlists() -> None:
    route = route_for_query("Strix Halo 128GB")
    assert route is not None
    assert route.name == "***REMOVED***"
    assert "cex" in route.allowed_sources
    assert "amazon" not in route.allowed_sources
    assert route_title_matches("GMKtec Strix Halo 128GB mini PC", route)
    assert route_title_matches("GMKtec Strix-Halo 128 GB mini PC", route)
    assert not route_title_matches("GMKtec Strix Halo 192GB mini PC", route)
    assert not route_title_matches("iPhone 15 128GB", route)


def test_glm_routes_cover_mac_variants_and_phone_false_positives() -> None:
    route = route_for_query("Mac Studio Ultra 256/512GB")
    assert route is not None
    assert route.name == "mac-studio-ultra-256-or-512gb"
    assert route_title_matches("Apple Mac Studio M3 Ultra 256GB", route)
    assert route_title_matches("Apple Mac Studio M3 Ultra 512GB", route)
    assert not route_title_matches("Apple Mac Studio M3 Ultra 128GB", route)

    route = route_for_query("Mac Studio Ultra 512GB")
    assert route is not None
    assert route.name == "mac-studio-ultra-512gb"
    assert route_title_matches("Apple Mac Studio M3 Ultra 512GB", route)
    assert not route_title_matches("Apple Mac Studio M3 Ultra 256GB", route)
    assert not route_title_matches("MacBook Pro M5 Max 512GB", route)

    route = route_for_query("MacBook Pro M5 Max 128GB")
    assert route is not None
    assert route_title_matches("Apple MacBook Pro M5 Max 128GB", route)
    assert not route_title_matches("MacBook Air M5 Max 128GB", route)


def test_title_terms_are_applied_by_post_normalization_filter() -> None:
    filters = WatchFilters(
        spec_match=SpecMatch(
            required_title_terms=["strix", "halo", "128gb"],
            excluded_title_terms=["192gb", "iphone"],
        ),
        price_max=None,
        min_seller_feedback=None,
        min_seller_feedback_pct=None,
    )
    results = apply_post_normalization_filters(
        [
            listing("Strix Halo 128GB mini PC"),
            listing("Strix Halo 192GB mini PC"),
            listing("iPhone 15 128GB"),
        ],
        filters,
    )
    assert [item.title_raw for item in results] == ["Strix Halo 128GB mini PC"]


def test_glm_watch_synonym_groups_are_applied_without_legacy_routes() -> None:
    """Watch-level groups accept chipset naming and reject unsafe variants."""
    filters = {
        "spec_match": {
            "excluded_title_terms": [
                "iphone",
                "ipad",
                "android",
                "galaxy",
                "pixel",
                "phone",
                "tablet",
            ]
        }
    }
    groups = [["strix halo", "ryzen ai max", "ai max+ 395", "395+"], ["128gb"]]
    results = apply_post_normalization_filters(
        [
            listing("AMD Ryzen AI Max+ 395 128GB Mini PC"),
            listing("GMKtec EVO-X2 AMD Ryzen AI Max+ 395 128GB"),
            listing("GMKtec Strix Halo 128GB Mini PC"),
            listing("AMD Ryzen AI Max+ 395 192GB Mini PC"),
            listing("AMD Ryzen AI Max+ 395 1280GB Mini PC"),
            listing("iPhone 15 128GB"),
        ],
        filters,
        groups,
    )
    assert [item.title_raw for item in results] == [
        "AMD Ryzen AI Max+ 395 128GB Mini PC",
        "GMKtec EVO-X2 AMD Ryzen AI Max+ 395 128GB",
        "GMKtec Strix Halo 128GB Mini PC",
    ]


def test_glm_watch_exclusions_stay_active_with_watch_synonym_groups() -> None:
    filters = {"spec_match": {"excluded_title_terms": ["iphone", "phone", "tablet"]}}
    groups = [["strix halo", "ryzen ai max", "ai max+ 395", "395+"], ["128gb"]]
    results = apply_post_normalization_filters(
        [listing("AMD Ryzen AI Max+ 395 128GB Mini PC"), listing("iPhone 15 128GB")],
        filters,
        groups,
    )
    assert [item.title_raw for item in results] == ["AMD Ryzen AI Max+ 395 128GB Mini PC"]


def test_regression_cex_iphone_excluded_from_strix_halo_128gb() -> None:
    """Regression test: CeX iPhone should be excluded from Strix Halo 128GB watch.

    This proves the fix for the bug where CeX returned iPhones for the
    'Ryzen AI Max+ 395 128GB Strix Halo' watch because generic storage
    capacity matched.
    """
    route = route_for_query("Strix Halo 128GB")
    assert route is not None, "Route should exist for Strix Halo 128GB"

    # iPhone listing should be excluded
    assert not route_title_matches(
        "Apple iPhone 12 Pro Max 128GB", route
    ), "iPhone listing should be excluded from Strix Halo 128GB watch"

    # Genuine Strix Halo listing should be included
    assert route_title_matches(
        "GMKtec Strix Halo 128GB mini PC", route
    ), "Genuine Strix Halo listing should be included"
