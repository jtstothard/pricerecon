# Overclockers connector disposition — 2026-07-28

- **Issue:** [#61](https://github.com/jtstothard/pricerecon/issues/61)
- **Connector:** `overclockers`
- **Canonical query:** `RTX 5070`
- **Probe method:** read-only `urllib` request, redirects enabled, 20-second timeout, Mozilla-compatible user agent. The response was parsed with BeautifulSoup using the configured card selector. No connector configuration or production state was changed.

## Evidence

| Request | HTTP status | Response evidence | Configured card matches |
|---|---:|---|---:|
| `https://www.overclockers.co.uk/search/?query=RTX%205070` | **403** | Response headers included `Cf-Mitigated: challenge`, `Server: cloudflare`, and a `CF-RAY` identifier; body was 9,349 bytes and contained no product cards | **0** |
| `https://www.overclockers.co.uk/` | **200** | Homepage HTML was 1,240,846 bytes and had title `PCs & Components \| Custom Built or Ready to Ship \| OcUK \| OcUK`; this proves the domain is reachable, not that search is usable | **0** |

The 403 is therefore not classified from status code alone: the response explicitly identifies a Cloudflare-managed challenge, while the separately reachable homepage does not expose the configured product-card structure. The search endpoint did not return product HTML, so the acceptance criteria requiring three parsed real listings cannot be met.

## Disposition

**Closed as blocked / not recoverable in this task.** Keep the connector fail-fast and degraded rather than enabling it or pretending that the homepage is a working search path. The current connector raises `ConnectorDegradedError` with `ConnectorStatus.bot_blocked`; this is the truthful behavior for the observed source response.

A future recovery would need an approved browser/anti-bot route that can complete the source challenge and reach the search endpoint, followed by a fresh live probe proving HTTP 200, three parsed listings, and a parsed product URL. No such route was available or validated here. Possible remediation directions (not implemented) are a maintained browser session, an authorized proxy/scraping service, or a source-supported API/feed.

## Regression coverage

`tests/test_timeout_retailers.py` verifies that Overclockers:

- fails fast without making a network request;
- reports `bot_blocked` for connector `overclockers`;
- includes the WAF/challenge evidence and source URL in structured error details; and
- preserves no-op lifecycle behavior.

The existing template remains enabled because it has no `disabled: true` flag, but the runtime connector remains intentionally degraded. Enabling a template would not recover a search route that is still returning a challenge response.
