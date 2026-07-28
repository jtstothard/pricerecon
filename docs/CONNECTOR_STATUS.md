# Connector status notes

The following connectors are intentionally registered but disabled. They raise
`ConnectorDegradedError(status=disabled)` before making a request, so watches
record an explicit unavailable state instead of a misleading empty result or a
generic transport error. Re-enable a connector only after its endpoint and
access lane have been revalidated and its fixture is updated.

| Connector | Evidence | Current state |
| --- | --- | --- |
| `ao` | The 2026-07-28 direct probe returned a Cloudflare challenge (HTTP 403, `Just a moment...`) for `https://www.ao.com/uk/search?search=RTX%205070`; the configured Byparr/FlareSolverr lane previously returned an HTTP 404 AO error page. Both access lanes are exhausted; see `docs/connector-baseline-2026-07.md`. | `disabled` |
| `ccl` | Direct HTTP returns Cloudflare HTTP 403 domain-wide. Byparr anti-bot route times out (>120s) on CCL. AO/Scan/Box work via Byparr, confirming infrastructure health. CCL hardened protection exceeds current bypass capabilities. See diagnosis task TASK-XXXX. | `bot_blocked` |
| `ebuyer` | The endpoint `/searchresults?descriptionfilter=RTX 5070` returns HTTP 200 via `httpx` but timed out under the baseline's `urllib` probe. The HTML selectors target empty placeholder elements; product data is in client-side JSON and card attributes. Fixed in commit on `wt/t_4ee91da0`: JSON parser now joins `ecommerceData.impressions` to card `li-url` and `li-imageurl` attributes for real product URLs and images; `use_flare_solverr` disabled (direct HTTP works). | `enabled` (verified working) |
| `dell_uk` | Dell UK search returned an Akamai Access Denied document (HTTP 403), including an `errors.edgesuite.net` reference. The response is preserved in `tests/fixtures/dell_uk/access_denied.html`. | `bot_blocked` |

This is a registry/template policy, not a health-check bypass: the disabled
status is persisted by the normal watch executor and remains visible through
the existing health API. No active watch currently targets these connectors.