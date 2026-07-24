# Connector status notes

The following connectors are intentionally registered but disabled. They raise
`ConnectorDegradedError(status=disabled)` before making a request, so watches
record an explicit unavailable state instead of a misleading empty result or a
generic transport error. Re-enable a connector only after its endpoint and
access lane have been revalidated and its fixture is updated.

| Connector | Evidence | Current state |
| --- | --- | --- |
| `aria` | `https://www.aria.co.uk/` serves a customer-closure message; the former search route is retired. | `disabled` |
| `ccl` | `https://www.cclonline.com/search/RTX%205090` returned Cloudflare HTTP 403. | `disabled` |
| `ebuyer` | `https://www.ebuyer.com/search?q=RTX%205090` returned the site's Not Found page (HTTP 404). | `disabled` |

This is a registry/template policy, not a health-check bypass: the disabled
status is persisted by the normal watch executor and remains visible through
the existing health API. No active watch currently targets these connectors.