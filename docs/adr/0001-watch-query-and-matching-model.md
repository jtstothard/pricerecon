# ADR: Watch query and matching model

## Date
2026-07-23

## Status
Accepted

## Context
PriceRecon watches use a single `query` string that serves two purposes: it is sent to every connector as-is, and it is the basis for post-fetch title matching. This causes two problems:

1. **Over-strict matching.** A watch for "Strix Halo 128GB" requires the literal terms "strix" and "halo" in every listing title, but genuine listings often use the chipset name ("AMD Ryzen AI Max+ 395 128GB") or vendor product codes without the marketing name. This blocks real results.
2. **Query shape mismatch.** Different connectors have different query capabilities. eBay's Browse API supports boolean syntax; Amazon is keyword-based; CeX has no query syntax at all. Sending the same query string to all three is suboptimal.

A previous attempt (commit 8a92bd4) introduced a hardcoded `HardwareRoute` table with per-route source allowlists and literal `required_terms`. This was GLM-specific, not generalisable, and still failed on real listing titles.

## Decision

Replace the single-query model with a general watch configuration that separates four concerns:

### 1. Display title (`display_title`)
What appears in the UI and dashboard. Human-readable, e.g. "Strix Halo 128GB". Does not affect search or matching.

### 2. Synonym groups (`synonym_groups`)
OR-within-group, AND-across-groups title matching. Always active as a safety-net filter. Replaces `required_terms`.

Example for Strix Halo 128GB:
```
synonym_groups: [
  ["strix halo", "ryzen ai max", "ai max+ 395", "395+"],
  ["128gb"]
]
```

A listing title must contain at least one term from every group to pass. Generalises to any product category.

### 3. Per-connector raw queries (`source_queries`)
Optional per-connector query overrides, passed through to each connector's native query syntax untouched. PriceRecon does not parse or translate these.

Example:
```
source_queries:
  ebay: '(ryzen OR strix OR "ai max") AND 128gb'
  cex: "ryzen ai max 128gb"
  amazon_uk: "ryzen ai max 395 128gb"
```

When absent for a connector, falls back to the watch's `query` field.

### 4. Excluded terms (`excluded_terms`)
Flat exclude list, always active. Replaces the hardcoded `_COMMON_EXCLUDES`.

### Simple vs Advanced mode (UI)

- **Simple mode (default):** synonym groups + excluded terms. Covers ~90% of watches. No boolean syntax shown.
- **Advanced mode (opt-in toggle):** per-connector raw query strings. Power users get full connector-native query power. The synonym-group safety net still runs underneath.

### Token-based matching with phrase support

Synonym group terms match against the tokenized title, not via naive substring:

1. **Single tokens** (`"128gb"`) match if the tokenized title contains them as a complete token (after normalization — casefold, remove punctuation, collapse `"128 GB"` → `"128gb"`). So `"1280gb"` won't satisfy `"128gb"`.
2. **Multi-word phrases** (`"mac studio"`, `"ryzen ai max"`) match if the phrase appears as a contiguous sequence in the tokenized title.
3. **Special characters** like `+` in `"395+"` are preserved as part of the token so `"395+"` won't match `"3950"` or `"3955"`.

### `synonym_groups` replaces `required_title_terms`

The `required_title_terms` field added in commit `8a92bd4` is replaced by `synonym_groups`. A flat `["strix", "halo", "128gb"]` is equivalent to three single-element groups. Existing watches with `required_title_terms` are auto-migrated: each term becomes its own single-element group, preserving AND semantics. `excluded_title_terms` is unchanged.

### Backward compatibility

The new fields (`display_title`, `synonym_groups`, `source_queries`) are optional. Watches without `synonym_groups` fall back to the existing `_filter_listings_by_query` behavior (all query terms must appear in the title). Non-GLM watches are unaffected.

### Migration of existing GLM watches (18–22)

The five GLM watches are migrated in place at deploy time. Each gets pre-populated synonym groups and excluded terms based on the route definitions we already have. Per-connector queries are left empty initially (falling back to the `query` field) and tuned later.

### Removal of `HardwareRoute`

The hardcoded route table (`src/pricerecon/core/hardware_routes.py`) is removed. All matching logic moves into watch configuration. No central route table, no auto-detection by query text inspection.

## Consequences

- Setting up a new watch requires configuring synonym groups and optionally per-connector queries, rather than just typing a search string. This is a one-time setup cost.
- The title-match filter (synonym groups + exclusions) runs on every result regardless of query source, so even aggressive raw queries are safe.
- No nested boolean DSL is needed; each connector uses its native syntax in advanced mode.
- The data model is general and applies to any product category, not just hardware.
