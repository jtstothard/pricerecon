# AliExpress browser discovery and product-page receipts

Observed 2026-10-27 after the user asked for browser access rather than relying on the affiliate API. The earlier [Byparr pass](byparr-live-check.md) had reached only robots.txt; it had not qualified a product page. This pass establishes **point-in-time public browser search and product-page access**, independent of affiliate query/detail methods.

Three top-level page requests: one retained product through CloakBrowser, the same product through Camofox for usable text, and one public wholesale-search page through Camofox. No pagination, new product-detail requests from the search results, login, account session, address, cart, checkout or Open Platform/affiliate/DS API request was performed. The browser's ordinary page subrequests are not individually counted. No images or raw snapshots/HTML were saved to the repository.

Current exact-path robots information is retained in the [earlier Byparr receipt](byparr-live-check.md). Generic rules did not disallow the `/item/...` and `/w/wholesale-...` paths used here; named crawler rules were not substituted for this user-initiated browser's identity. No custom crawler identity was supplied. This small personal investigation is not approval for systematic collection or a historical database under the [current terms](https://terms.alicdn.com/legal-agreement/terms/suit_bu1_aliexpress/suit_bu1_aliexpress202204182115_66077.html).

## Product route

Target: `https://www.aliexpress.com/item/1005007071090465.html`, retained in the supplied watch corpus. Its presence there is a lead, not prior proof of current access or selected configuration.

| UTC | Browser route | Observation |
| --- | --- | --- |
| **10:47:20.315180–10:47:22.810747** | Repaired CloakBrowser through the deployed shared adapter | HTTP 200; final URL unchanged; adapter degradation `none`; 262,144 HTML characters and explicit truncation. ML05 token present, but no useful product heading/price metadata in the received prefix. **Partial**, not accepted product extraction. |
| **10:48:56.352239–10:49:01.379123** | Camofox snapshot through the deployed shared adapter, separate anonymous context | Final tab URL unchanged, checked before snapshot acquisition; adapter degradation `none`; snapshot 14,530 characters. Product heading identified Militado ML05, 38 mm and VH31. Displayed item amount **£35.82**, plus a VAT-included claim. No explicit selected/checked variant control was captured. |

The VAT wording is a merchant/platform claim, not tax verification. The displayed percentage/strike-through and coins opportunity are excluded from accepted savings. The amount is **not** a verified exact-SKU or UK delivered price: selected SKU/dial/strap, dispatch origin, actual inventory, UK destination, shipping and complete total remain unverified. No challenge/login marker was detected by the probe's narrow text checks; that is not proof that no challenge ever occurred or was solved. Camofox's main-document HTTP status is not exposed by this adapter; no status is invented from `degradation=none`.

## Browser discovery route

Target: `https://www.aliexpress.com/w/wholesale-militado-ml05.html`, the public route template already used by the connector's `_site_search` method. **10:54:58.602588–10:55:02.324117 UTC**:

- Camofox final tab URL matched the requested wholesale-search URL.
- Adapter degradation `none`; snapshot **48,280 characters**.
- **28 distinct `/item/…` links** were present in the received snapshot, including the product PID above. These are link candidates, not 28 qualified watches or a complete result count. Only up to 20 ID digests and a small bounded heading/query excerpt were emitted; no price table or catalogue was retained.
- The query was shown in the search control. Bounded visible candidate headings included **VH31**, **Miyota 2035** and **Ronda 515** ML05 configurations. A family title alone cannot merge them into one comparable offer.
- No forced-login/challenge marker matched the probe checks. No result link was followed, pagination changed, result sorted or account used.

This is the first observed browser discovery-to-known-product link for this cohort. Its search response and earlier direct product response are separate timestamped observations, not a continuously held selection or price guarantee.

## Interpretation and integration boundary

The route does not call the affiliate catalogue, so affiliate API catalogue limits did not determine these browser results. However, no comparison against affiliate eligibility was made: **this does not prove that any particular observed item is non-affiliate**, nor that the browser covers all inventory.

These observations used PriceRecon's repaired shared browser adapter, not the full AliExpress connector's search/normalisation/fallback pipeline. Source inspection shows `_site_search` currently uses direct HTTP and title/price heuristics, while browser PDP enrichment has its own extraction path. Browser capability is now observed; routing/normalisation of a complete browser-first discovery workflow remains to be qualified or implemented. No change to that connector or its production selection was made here.

For the source plan, browser discovery is the appropriate **candidate primary lane** to investigate for broader AliExpress coverage; affiliate query/detail can remain optional enrichment for eligible products. Acceptance still requires exact selected configuration, UK cost context, freshness and permitted ongoing use/retention. Do not silently fall back to the affiliate lane and claim equivalent coverage.

Both new anonymous Camofox contexts were closed by their exact derived IDs after their probes. Existing account profiles were not selected. Raw tool observations remain in this conversation, not a licensed price/content archive. Source ticket remains open.
