# AliExpress Connector Contract

This document defines the supported modes and failure handling behavior for the AliExpress connector.

## Summary

The AliExpress connector supports two primary modes of operation:

1. **Generic search** — Discover listings via query-based search with automatic fallback
2. **Manual PID watch** — Monitor specific known product IDs with layered enrichment

Both modes are supported and serve different use cases. Generic search is resilient to affiliate-lane degradation and falls through to discovery lanes. Manual PID watch is the canonical path for long-term monitoring of known products.

## Mode 1: Generic Search (Discovery)

**Purpose:** Find AliExpress listings for a search query (e.g., "RTX 4070 Ti").

**Flow:**

1. **Affiliate search** (primary lane)
   - Queries AliExpress affiliate API (`aliexpress.affiliate.product.query`)
   - Returns listings with prices from affiliate data
   - Raises `ConnectorDegradedError` on auth failures or API errors

2. **Brave discovery** (fallback lane, enabled by default)
   - Queries Brave Search for `site:aliexpress.com/item/ "{query}"`
   - Extracts PIDs from search results
   - Creates placeholder listings (price=None) for enrichment
   - Labeled with `aliexpress_watch_mode: "brave_discovery"`

3. **Manual PIDs from query** (fallback lane)
   - Extracts PID if query matches 10-20 digit number
   - Resolves short links (a.aliexpress.com, s.click.aliexpress.com)
   - Labeled with `aliexpress_watch_mode: "manual_pid"`

4. **Enrichment** (applies to all lanes)
   - DS enrichment (if configured): `aliexpress_source_lane: "ds"`
   - Browser enrichment (if configured): `aliexpress_source_lane: "browser"`
   - Affiliate lookup (for manual PIDs only): `aliexpress_source_lane: "affiliate"`

5. **Filtering**
   - Deduplicate by source_listing_id
   - Annotate with query match confidence
   - Filter out listings that don't match query
   - Filter out unresolved placeholders (price=None)

**Resilience:**

- Affiliate lane failures do **not** abort the entire search
- `ConnectorDegradedError` from affiliate search is caught, logged at WARNING level
- Search continues into Brave and manual PID lanes
- If no listings after all lanes and affiliate failed, logs debug message

**Configuration:**

```python
{
    "affiliate_api_endpoint": "https://api-sg.aliexpress.com/sync",  # optional
    "affiliate_currency": "GBP",  # default
    "brave_discovery": True,  # default
    "brave_max_pids": 25,  # default
    "manual_pids": ["1005012248779870"],  # optional global list
    "enrich_with_ds": False,  # default, or True if DS creds present
    "browser_enrich": False,  # default
}
```

**Per-call filters:**

```python
connector.search(query, {
    "affiliate_only": False,  # default True, False disables affiliate lane
    "brave_discovery": True,  # overrides config default
    "enrich_with_ds": True,  # overrides config default
    "browser_enrich": True,  # overrides config default
})
```

## Mode 2: Manual PID Watch (Monitoring)

**Purpose:** Monitor specific known product IDs with price and stock tracking.

**Flow:**

1. **Resolve targets** from:
   - Query PID (if query is a 10-20 digit number)
   - `manual_pids` in per-call filters
   - `manual_pids` in connector config (global list)
   - `manual_links` in per-call filters
   - `manual_links` in connector config (global list)
   - Short links resolved from query

2. **Create placeholder listings**
   - `source_listing_id`: PID
   - `price`: None (placeholder)
   - `aliexpress_watch_mode`: "manual_pid"

3. **Layered enrichment** (tries in order, stops on first success)

   For each PID:
   
   a. **DS API** (if configured and `enrich_with_ds` enabled)
      - Endpoint: `ds/product/get`
      - Returns: title, price, stock, rating, sales, coupons
      - Sets `aliexpress_source_lane: "ds"`
   
   b. **Affiliate API lookup** (if DS failed)
      - Queries affiliate API for specific PID
      - Returns: title, price, shipping, seller info
      - Sets `aliexpress_source_lane: "affiliate"`
   
   c. **Browser PDP scrape** (if `browser_enrich` enabled and Camofox configured)
      - Uses Camofox browser-assisted scraping
      - Extracts price from product detail page
      - Sets `aliexpress_source_lane: "browser"`
   
   d. **Simple HTTP fetch** (final fallback)
      - Basic HTTP GET to product URL
      - Attempts to extract price from HTML
      - Sets `aliexpress_source_lane: "http"`

4. **Filter**
   - Returns only listings where price is not None
   - Unenriched PIDs are dropped (avoids price=0 listings)

**Configuration:**

```python
{
    "ds_access_token": "...",
    "ds_refresh_token": "...",
    "ds_app_key": "...",
    "ds_app_secret": "...",
    "ds_expires_at": "2026-07-12T00:00:00+00:00",
    "ds_product_endpoint": "https://api-sg.aliexpress.com/sync",  # optional
    "manual_pids": ["1005012248779870", "1005022248779871"],  # global list
    "manual_links": ["https://a.aliexpress.com/item/123.html"],  # global list
    "camofox_url": "https://camofox.example",  # for browser enrichment
    "camofox_user_id": "pricerecon-aliexpress",
    "camofox_session_key": "watcher",
    "camofox_wait_s": 12,
}
```

**Per-call filters:**

```python
connector.search("1005012248779870", {
    "manual_pids": ["1005022248779871"],
    "manual_links": ["https://a.aliexpress.com/item/123.html"],
    "manual_title": "Custom title for query PID",
    "enrich_with_ds": True,
    "browser_enrich": True,
})
```

## Variant Normalization

Listings carry `variant_normalized` metadata to track provenance:

```python
{
    "aliexpress_product_id": "1005008557811111",
    "aliexpress_watch_mode": "brave_discovery" | "manual_pid",
    "aliexpress_source_lane": "ds" | "browser" | "affiliate" | "http",
    "aliexpress_display_price": "199.99",  # from DS/affiliate
    "aliexpress_original_price": "249.99",  # from DS/affiliate
    "aliexpress_coupon_layers": [{"text": "£10 off"}],  # from DS
    "aliexpress_rating": "4.8",  # from DS/affiliate
    "aliexpress_sales": "123",  # from DS/affiliate
    "aliexpress_shop_name": "SZCPU",  # from DS/affiliate
}
```

## Error Handling

### Generic Search Mode

- **Affiliate lane failures**: Caught, logged at WARNING, search continues
- **Brave lane failures**: Caught, logged at WARNING, search continues
- **No results after all lanes**: Returns empty list (does NOT raise)
- **All lanes fail with no manual PIDs**: Returns empty list

### Manual PID Watch Mode

- **DS enrichment failures**: Falls through to affiliate lookup
- **Affiliate lookup failures**: Falls through to browser enrichment
- **Browser enrichment failures**: Falls through to simple HTTP
- **All enrichment fails**: Listing is filtered out (price=None)
- **Auth failures on DS API**: Raises `ConnectorDegradedError` with `ConnectorStatus.auth_failed`

## Supported Distinction

Both modes are supported:

- **Generic search** is for discovering new listings via queries
- **Manual PID watch** is for monitoring known products over time

They are not mutually exclusive. A single connector instance can:

1. Discover PIDs via generic search (affiliates → Brave)
2. Monitor specific PIDs via manual PID watch (DS → affiliate → browser)

The canonical path for **long-term price watching** is the **manual PID mode**, as it provides:

- Layered enrichment with fallbacks
- Consistent monitoring of specific products
- Better data quality from DS API when available

Generic search with fallback lanes ensures the connector remains useful even when affiliate credentials are missing or expired.

## Test Coverage

- `test_aliexpress_connector_uses_manual_pid_and_ds_and_browser`: Validates manual PID enrichment pipeline
- `test_aliexpress_brave_discovery_routes_into_ds_enrichment_and_keeps_manual_flow`: Validates Brave discovery + manual PID in same search
- `test_aliexpress_connector_continues_when_affiliate_lane_fails`: Validates affiliate failure resilience
- `test_aliexpress_connector_surfaces_ds_auth_failure`: Validates DS auth error propagation

## Changelog

- **2026-07-13**: Fixed generic search to survive affiliate-lane `ConnectorDegradedError` and continue to fallback lanes (commit 2b74c5d)