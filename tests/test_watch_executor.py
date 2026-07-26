"""Tests for watch_executor filtering logic."""

from decimal import Decimal
from pricerecon.models.listings import Condition, NormalizedListing, SourceType
from pricerecon.core.watch_executor import apply_post_normalization_filters


def test_condition_none_survives_filter():
    """Regression test: condition=None listings should NOT be dropped by condition filter.
    
    Bug: The filter used `lst.condition and lst.condition in conditions` which
    short-circuits to False for None, dropping valid eBay listings that don't
    populate condition. Fix: Use `lst.condition is None or lst.condition in conditions`.
    """
    # Build a listing with condition=None (typical for eBay)
    listing_none = NormalizedListing(
        source="ebay",
        source_type=SourceType.MARKETPLACE,
        source_listing_id="1",
        title_raw="AMD Instinct MI50 32GB",
        price=Decimal("494.00"),
        currency="GBP",
        url="https://example.com/1",
        condition=None,  # Unknown condition from eBay API
    )
    
    # Build a listing with disallowed condition
    listing_fair = NormalizedListing(
        source="ebay",
        source_type=SourceType.MARKETPLACE,
        source_listing_id="2",
        title_raw="AMD Instinct MI50 32GB",
        price=Decimal("300.00"),
        currency="GBP",
        url="https://example.com/2",
        condition=Condition.USED_FAIR,  # NOT in allowed list
    )
    
    # Build a listing with allowed condition
    listing_good = NormalizedListing(
        source="cex",
        source_type=SourceType.RETAILER,
        source_listing_id="3",
        title_raw="AMD Instinct MI50 32GB",
        price=Decimal("400.00"),
        currency="GBP",
        url="https://example.com/3",
        condition=Condition.USED_GOOD,  # In allowed list
    )
    
    # Filters: allow USED_GOOD and USED_LIKE_NEW, plus a spec_match that all listings pass
    from pydantic import BaseModel
    class PostNormalizationFilters(BaseModel):
        price_max: Decimal | None = None
        condition_filter: dict = {}
        spec_match: dict = {}
    
    filters = PostNormalizationFilters(
        price_max=Decimal("600.00"),
        condition_filter={"conditions": [Condition.USED_GOOD, Condition.USED_LIKE_NEW]},
        spec_match={"synonym_groups": [["amd", "instinct"], ["mi50"]]},
    )
    
    # Apply filters
    filtered = apply_post_normalization_filters(
        [listing_none, listing_fair, listing_good],
        filters,
        watch_synonym_groups=None,
    )
    
    # Listings that should survive:
    # - listing_none (condition=None, allowed by fix, passes spec_match)
    # - listing_good (condition in allowed list, passes spec_match)
    # Listing that should be dropped:
    # - listing_fair (condition NOT in allowed list)
    assert len(filtered) == 2
    assert listing_none in filtered
    assert listing_good in filtered
    assert listing_fair not in filtered