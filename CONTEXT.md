# PriceRecon Domain Model

## Glossary

### Watch
A tracked search across one or more sources. Owns its full spec: what to search for, where, and what to accept as a match.

### Display Title (`display_title`)
The human-readable name shown in the dashboard UI. Does not affect search queries or matching. Example: "Strix Halo 128GB".

### Query (`query`)
The default search string sent to a connector when no per-connector override is configured.

### Source Queries (`source_queries`)
Per-connector raw query overrides. Passed through to each connector's native query syntax untouched by PriceRecon. Advanced mode only.

### Synonym Groups (`synonym_groups`)
Title-matching rule: OR-within-group, AND-across-groups. A listing title must contain at least one term from every group to pass the safety-net filter. Always active.

### Excluded Terms (`excluded_terms`)
Flat title exclude list. Always active. A listing containing any excluded term is dropped.

### Connector
A source adapter (eBay, CeX, Amazon UK, etc.) that implements search against a specific retailer or marketplace API.

### Normalized Listing
A search result normalised to a common schema regardless of source connector.

### Safety-Net Filter
The title-match filter (synonym groups + exclusions) that runs on every normalised listing regardless of which query produced it. Provides precision; the query provides recall.
