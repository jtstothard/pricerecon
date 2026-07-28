# Connector status notes

The following connectors are intentionally registered but disabled. They raise
`ConnectorDegradedError(status=disabled)` before making a request, so watches
record an explicit unavailable state instead of a misleading empty result or a
generic transport error. Re-enable a connector only after its endpoint and
access lane have been revalidated and its fixture is updated.

| Connector | Evidence | Current state |
| --- | --- | --- |
| `aria` | `https://www.aria.co.uk/` serves a customer-closure message; the former search route is retired. | `disabled` |
| `ccl` | Direct HTTP returns Cloudflare HTTP 403 domain-wide. Byparr anti-bot route times out (>120s) on CCL. AO/Scan/Box work via Byparr, confirming infrastructure health. CCL hardened protection exceeds current bypass capabilities. See diagnosis task TASK-XXXX. | `bot_blocked` |
| `ebuyer` | `https://www.ebuyer.com/search?q=RTX%205090` returned the site's Not Found page (HTTP 404). | `disabled` |
| `dell_uk` | Dell UK search returned an Akamai Access Denied document (HTTP 403), including an `errors.edgesuite.net` reference. The response is preserved in `tests/fixtures/dell_uk/access_denied.html`. | `bot_blocked` |

This is a registry/template policy, not a health-check bypass: the disabled
status is persisted by the normal watch executor and remains visible through
the existing health API. No active watch currently targets these connectors.