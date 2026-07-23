# Spec: General Watch Query and Matching Model

**Status:** ready-for-agent
**ADR:** [0001-watch-query-and-matching-model](adr/0001-watch-query-and-matching-model.md)

## Problem Statement

As a PriceRecon operator, I track hardware across multiple retailers and marketplaces, but the single search query per watch is sent verbatim to every connector and also used as the title-matching filter. This causes two problems:

1. **Over-strict matching blocks real results.** A watch for "Strix Halo 128GB" requires the literal marketing terms in every listing title, but genuine listings say "AMD Ryzen AI Max+ 395 128GB Mini PC" — no "strix", no "halo". The current filter rejects these. Result: GLM hardware watches return zero listings.

2. **One query shape doesn't fit all connectors.** eBay supports boolean query syntax; Amazon is keyword-based; CeX has no query syntax at all. Sending the same query string to all three is suboptimal and limits recall.

## Solution

Replace the single-query model with a general watch configuration that separates four concerns: what we display, what we search for (per-connector), what we accept (title matching), and what we exclude. This is a general PriceRecon feature — not GLM-specific — that applies to any product category.

## User Stories

1. As a watch operator, I want to set a display title separate from my search query, so that the dashboard shows a clean name like "Strix Halo 128GB" regardless of what query string is sent to each connector.

2. As a watch operator, I want synonym groups for title matching, so that "AMD Ryzen AI Max+ 395 128GB" is accepted as a valid Strix Halo match without requiring the literal marketing name.

3. As a watch operator, I want excluded terms to be always active, so that iPhones, tablets, and wrong-capacity variants are filtered out regardless of the search query used.

4. As a power user, I want to set per-connector query strings in the connector's native syntax, so that I can craft an eBay boolean query like `(ryzen OR strix OR "ai max") AND 128gb` while sending a simpler query to CeX.

5. As a watch operator, I want the synonym-group safety net to always run, so that even if an advanced per-connector query is too broad, mismatched results are still filtered out.

6. As a watch operator, I want token-based matching, so that "128gb" matches "128GB" and "128 GB" but does not match "1280GB".

7. As a watch operator, I want existing watches to keep working unchanged, so that my DDR4 and CPU watches don't break when the new model is deployed.

8. As a watch operator, I want the GLM hardware watches to return real listings after migration, so that I'm actually tracking the market instead of seeing zero results.

9. As a frontend user, I want a simple mode that shows synonym groups and exclusions, so that I don't need to understand boolean syntax to set up a watch.

10. As a frontend user, I want an advanced mode toggle that reveals per-connector query fields, so that I can craft connector-specific queries when I need to.

## Implementation Decisions

### Model changes (Watch / WatchFilters / SpecMatch)

- Add `display_title: Optional[str]` to Watch. Shown in UI. Does not affect search or matching.
- Add `synonym_groups: list[list[str]]` to SpecMatch. Replaces `required_title_terms`. OR-within-group, AND-across-groups.
- Add `source_queries: dict[str, str]` to Watch. Per-connector raw query overrides, passed through untouched.
- Keep `excluded_title_terms` on SpecMatch. Renamed conceptually to "excluded terms" but field name stays for backward compat.
- Remove `required_title_terms` from SpecMatch. Auto-migrate: each existing term becomes a single-element synonym group.

### Token-based title matching

- Normalize: casefold, remove punctuation, collapse whitespace, merge "128 GB" → "128gb".
- Single tokens match as complete tokens in the normalized title token set.
- Multi-word phrases match as contiguous token sequences.
- Special characters like `+` are preserved within tokens.

### Connector query routing

- When a watch has `source_queries[connector_id]`, send that query to the connector instead of the watch's `query` field.
- When absent, fall back to the watch's `query` field (existing behavior).
- PriceRecon does not parse, validate, or translate connector-native query syntax.

### Safety-net filter

- The synonym-group + excluded-terms filter runs on every normalized listing regardless of which query produced it.
- Provides precision (rejects mismatches); the query provides recall (finds candidates).

### Backward compatibility

- All new fields are optional.
- Watches without `synonym_groups` fall back to existing `_filter_listings_by_query` behavior.
- Non-GLM watches are unaffected.

### Removal of HardwareRoute

- Delete `src/pricerecon/core/hardware_routes.py` and its auto-detection (`route_for_query`).
- All matching logic moves into watch configuration. No central route table.

### Migration of GLM watches (18–22)

- Migrate in place at deploy time.
- Pre-populate synonym groups and excluded terms based on the route definitions from the deleted table.
- Leave `source_queries` empty initially (fall back to `query` field).

### Frontend

- Simple mode (default): synonym groups + excluded terms editors. No boolean syntax shown.
- Advanced mode (opt-in toggle): per-connector raw query fields revealed.

## Testing Decisions

### Primary seam: `apply_post_normalization_filters`

The existing pure function in `watch_executor.py` that takes a list of `NormalizedListing` objects and a `WatchFilters` config, returns the filtered list. This seam already exists and is used by `test_hardware_routes.py`. All matching behavior (synonym groups, token-based matching, exclusions, backward compat) is tested here without coupling to connector internals.

Test cases:
- Synonym group accepts "AMD Ryzen AI Max+ 395 128GB" for a Strix Halo route
- Synonym group rejects "iPhone 15 128GB"
- Token matching: "128gb" does not match "1280gb"
- Token matching: "395+" does not match "3950"
- Phrase matching: "mac studio" matches as contiguous tokens
- Excluded terms drop listings regardless of synonym match
- Backward compat: watch without synonym_groups uses old query-term filtering
- Auto-migrated required_title_terms preserve AND semantics

### Secondary seam: connector query routing

Test that when a watch has `source_queries`, the correct query string reaches each connector's `search()` method. Testable with mock connectors or by asserting the query passed to a connector instance. No live API calls needed.

## Out of Scope

- Reddit API / browser fallback activation (separate task `t_41a99393`)
- Browser backend wiring for retailers (separate task `t_41a99393`)
- Aria / Novatech endpoint drift (separate task `t_55108e0c`)
- Nested boolean DSL parser (rejected in ADR)
- Structured spec matching (gpu_model, ram_gb, etc.) — unchanged, orthogonal
- Notification pipeline changes

## Further Notes

- The ADR is committed at `254094f` in `docs/adr/0001-watch-query-and-matching-model.md`.
- The domain glossary is in `CONTEXT.md`.
- This spec supersedes the monolithic task `t_25120dea`.
