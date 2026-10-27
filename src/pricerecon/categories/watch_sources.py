"""Read-only projection of the accepted watch roster, not an acquisition registry.

No routes, credentials, cadence or activation are configured here. These rows keep
unavailable mandatory families visible even when no connector was ever attempted.
"""

from pricerecon.models.discovery import DiscoveryCapture, SourceCoverage


def source_coverage(captures: list[DiscoveryCapture]) -> list[SourceCoverage]:
    rows = [
        SourceCoverage(
            family="aliexpress",
            source="AliExpress browser-first",
            route="aliexpress_browser_first_v1",
            accepted_status="reviewed_lead",
            reason="Bounded displayed selections; no accepted selected SKU stock or UK total.",
            prerequisites=[
                "capture/display/reuse authority",
                "bounded browser-origin accounting",
                "separate archive grant",
            ],
        ),
        SourceCoverage(
            family="aliexpress",
            source="AliExpress affiliate",
            route="aliexpress_affiliate",
            accepted_status="unqualified",
            reason="Narrower affiliate inventory cannot replace browser discovery; detail unqualified.",
            prerequisites=[
                "intended capture and retention authority",
                "detail/selection qualification",
            ],
        ),
        SourceCoverage(
            family="aliexpress",
            source="AliExpress DS",
            route="aliexpress_ds",
            accepted_status="unsupported",
            reason="No existing DS entitlement assumed.",
            prerequisites=["demonstrated DS entitlement", "source retention authority"],
        ),
        SourceCoverage(
            family="ebay_secondhand",
            source="eBay Browse new / used",
            route="ebay_browse_search_v1",
            accepted_status="reviewed_lead",
            reason="Condition and purchase mode remain distinct; search pages do not certify selected offers.",
            prerequisites=[
                "provider-approved capture/display use",
                "retention/derivation grant",
                "destination and complete UK cost",
                "freshness review",
            ],
        ),
        SourceCoverage(
            family="ebay_secondhand",
            source="Chrono24",
            route="chrono24_manual_lead",
            accepted_status="blocked",
            reason="Manual lead only; automated acquisition and history unqualified.",
            prerequisites=[
                "approved automated/API/retention route",
                "dealer/private seller and shipping quote evidence",
            ],
        ),
        SourceCoverage(
            family="brand_direct",
            source="Militado",
            route="militado_read_only",
            accepted_status="blocked",
            reason="Store/manufacturer ownership and exact cohort fields remain unproven.",
            prerequisites=[
                "recognized Web Bot Auth signer",
                "store/manufacturer identity",
                "capture/reuse authority",
            ],
        ),
        SourceCoverage(
            family="uk_retail",
            source="Watch Shop",
            route="watch_shop_public",
            accepted_status="unqualified",
            reason="Current exact offer and use/access qualification missing.",
            prerequisites=[
                "current applicable access/use terms",
                "selected offer delivery evidence; checkout may be required",
            ],
        ),
        SourceCoverage(
            family="uk_retail",
            source="WatchGecko",
            route="watchgecko_public",
            accepted_status="unqualified",
            reason="Public reading does not grant reusable archive or deep-link publication.",
            prerequisites=[
                "intended storage/display/deep-link authority",
                "selected complete-watch offer",
            ],
        ),
        SourceCoverage(
            family="uk_shipping_international",
            source="Sakura Watches",
            route="sakura_clean_category",
            accepted_status="unqualified",
            reason="Clean category distinct from restricted search/paging; physical versus orderable stock unresolved.",
            prerequisites=[
                "route-specific access and retention review",
                "selected stock and buyer import cost",
            ],
        ),
        SourceCoverage(
            family="uk_shipping_international",
            source="San Martin independent retailer",
            route="shopify_products_v1",
            accepted_status="reviewed_lead",
            reason="sanmartin.watch is an independent retailer; selected stock, dispatch origin and UK fees unqualified.",
            prerequisites=[
                "store-specific reuse/archive authority",
                "selected SKU and fulfilment evidence",
                "UK checkout costs",
            ],
        ),
        SourceCoverage(
            family="search_aggregator_community",
            source="Brave API",
            route="brave_search",
            accepted_status="unqualified",
            reason="Runtime access and plan/storage entitlement unresolved.",
            prerequisites=[
                "existing token and actual plan inventory",
                "storage-entitled plan",
                "merchant re-verification",
            ],
        ),
        SourceCoverage(
            family="search_aggregator_community",
            source="SearXNG",
            route="searxng_search",
            accepted_status="unqualified",
            reason="Healthy transport/configuration is not permitted merchant discovery.",
            prerequisites=[
                "actual engine/upstream use and storage terms",
                "merchant re-verification",
            ],
        ),
        SourceCoverage(
            family="search_aggregator_community",
            source="Google Shopping",
            route="google_shopping_lead",
            accepted_status="blocked",
            reason="Retained search-path access stop; aggregator is not selected-price authority.",
            prerequisites=[
                "permitted exact search route",
                "merchant re-verification and reuse rights",
            ],
        ),
        SourceCoverage(
            family="search_aggregator_community",
            source="Google Custom Search JSON API",
            route="google_custom_search",
            accepted_status="unsupported",
            reason="Closed to new customers; retained decision records existing-service end 2027-01-01.",
            prerequisites=["supported alternative under separate decision"],
        ),
        SourceCoverage(
            family="search_aggregator_community",
            source="HotUKDeals",
            route="hotukdeals_feed",
            accepted_status="blocked",
            reason="Retained terms/robots HTTP403; no automation/storage grant established.",
            prerequisites=["readable applicable feed/use conditions", "retention authority"],
        ),
        SourceCoverage(
            family="search_aggregator_community",
            source="Reddit watch communities",
            route="reddit_watch_communities",
            accepted_status="blocked",
            reason="RSS/browser fallback does not replace provider-approved API use.",
            prerequisites=["provider-approved app/use case", "approved retention scope"],
        ),
    ]
    for row in rows:
        for capture in captures:
            for outcome in capture.outcomes:
                receipt = outcome.source_evidence
                if receipt and receipt.route == row.route:
                    if row.route == "shopify_products_v1" and receipt.source_host not in {
                        "sanmartin.watch",
                        "www.sanmartin.watch",
                    }:
                        continue
                    row.last_outcome = outcome
                    break
                if (
                    receipt is None
                    and outcome.state in {"blocked", "capped", "failed", "not_attempted"}
                    and (row.route, outcome.source)
                    in {
                        ("aliexpress_browser_first_v1", "aliexpress"),
                        ("ebay_browse_search_v1", "ebay"),
                    }
                ):
                    row.last_outcome = outcome
                    break
            if row.last_outcome is not None:
                break
    return rows
