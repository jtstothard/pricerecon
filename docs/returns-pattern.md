# PriceRecon connector pattern note: typed composition with returns

Use `returns` at seams where the system can produce a structured, inspectable failure that callers may want to branch on without throwing.

Good fits:
- loading user-provided or file-backed connector templates
- normalizing/validating boundary payloads before they enter the app
- multi-step acquisition flows where a failure should be returned as data and then composed/decided at the edge

Bad fits:
- internal programmer errors and invariants
- places that already have a domain-specific exception type and no meaningful alternate branch
- broad replacement of exceptions in hot code just because `returns` is available

Current example in the repo:
- `src/pricerecon/connectors/rss.py` exposes `load_template_configs_result()` for typed success/failure handling and keeps `load_template_configs()` as a compatibility wrapper.
- `tests/test_connectors.py` covers the success path and an invalid-YAML failure path.

Boundary rule:
- keep validation at the edge, compose result objects across the seam, then convert to the repo’s existing domain error or fallback behavior where needed.
