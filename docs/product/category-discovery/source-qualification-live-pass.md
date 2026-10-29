# Anonymous source qualification: approved preflight receipts

Date: 2026-10-27. Operator: jtstothard / Codex. Parent: [Which source routes can support an honest watch discovery claim?](tickets/source-qualification.md).

## Authority, method and result

The user replied “approve” to the [proposed protocol](source-qualification-research.md#proposed-bounded-live-read-only-protocol--not-executed-or-authorised): one anonymous public browsing pass, at most 60 minutes and 60 document navigations, with the named hosts and stop rules. Approval covers this pass; it does not authorise accounts, APIs, connectors, checkout or a repeat session.

Session window: **09:37:14–09:39:17 UTC**. Browser: T3 collaborative preview, fresh Incognito tab `tab_6_cb337ae4-583e-49f4-9519-896a866c83a1`. No credentials or saved profile selected; no login performed. Tool-call history in this conversation is the execution evidence. Page HTTP statuses were not exposed by navigation results; an error page's displayed status is identified as such below.

**Result: 12 host preflights attempted; zero offer searches or details inspected; zero routes qualified.** Stop conditions or unresolved access prerequisites prevented offer acquisition. This establishes access-policy/inspection findings for the attempted anonymous browser lane, not failure of any connector or API.

Count: **15 explicit URL navigations plus one observed automatic cross-host redirect = 16 known document navigations**, within the 60-navigation cap. Hidden redirect hops and browser subresource requests were not instrumented; 16 is the known count, not a network request count. Every host had at most two explicit navigations; repeat navigations to a host were separated by more than five seconds. No result/category query or offer-detail page was requested. The Google landing redirect was incidental and is excluded from cohort coverage.

## Receipts

Every row has status **blocked for this protocol**. Query/category/filter/sort, page/cursor, inspected result count, listing/seller/PID/SKU, variant, condition/purchase mode, stock, currency, price, shipping and tax are **not observed**, because acquisition stopped at preflight. UK destination was not selected or verified. No zero-result search is claimed. Repeated monitoring, connector normalisation and checkout remain **not tested**.

The first two attempts occurred during 09:37:14–09:38:23 UTC; the remaining preflights occurred during 09:38:23–09:39:17 UTC. Individual start/end times were not durably captured for every call; these are session-bounded receipts rather than precise per-request timing records.

| Route / evidence URL | Explicit navigations | Observation and stop reason |
| --- | --- | --- |
| [AliExpress robots](https://www.aliexpress.com/robots.txt) | 1 | Navigation reported the requested URL, but both snapshot inspections failed with `Preview automation snapshot timed out after 15000ms.` No content, permissions or HTTP status established. No reload or alternate browser used. |
| [eBay UK robots](https://www.ebay.co.uk/robots.txt) | 1 | Same snapshot failure; read-only DOM inspection in the same preview then succeeded. Preamble requires express eBay permission for automated access; generic search path `/sch/` disallowed. No such permission established, so stop before search. API lane not exercised. |
| [Chrono24 UK robots](https://www.chrono24.co.uk/robots.txt), [platform terms](https://www.chrono24.co.uk/info/agb.htm) | 2 | Robots alone did not establish a blanket block for the planned route. Displayed terms, last updated 18 October 2021 and marked a translation, sections 6.1–6.3 restrict software/automatic reading, bypassing supplied search forms and building a personal database. Treat intended collection as blocked; do not infer current legal permission from permissive robots. |
| [Militado robots](https://www.militadowatch.com/robots.txt), [agent guidance](https://www.militadowatch.com/agents.md) | 2 | Public read-only HTML is described as available subject to agent identification. Guidance requires agent-initiated traffic identification and Web Bot Auth for hosted/remote browsers. This preview's compliant identification was not established. Stop; no authentication, integration, skill install or account connection attempted. Store guidance was read as source access information, not authority to expand the task. |
| [Watch Shop robots](https://www.watchshop.com/robots.txt) | 1 | Generic rules disallow search-result paths, several filters and a terms path. Planned search acquisition stopped; this does not establish that every product URL is forbidden or unavailable. No replacement route improvised. |
| [WatchGecko robots](https://www.watchgecko.com/robots.txt) | 1 | Generic `/search` and `/policies/` disallowed, alongside transactional/filter paths. Search lane stopped. Allowed category/product paths do not establish collection or retention permission; no substitute category crawl attempted. |
| [Sakura Watches robots](https://www.sakurawatches.com/robots.txt) | 1 | Generic product-search route, filter, paging and `/terms` paths disallowed. Planned search lane stopped. This is not a claim all product detail HTML is prohibited. |
| [San Martin retailer robots](https://www.sanmartin.watch/robots.txt) | 1 | Generic `/search` disallowed, along with transactional and selected API paths. Search lane stopped. Retailer identity from the documentation pass remains distinct from manufacturer-direct qualification. |
| [Google Shopping robots](https://shopping.google.com/robots.txt), [requested landing URL](https://shopping.google.com/) | 2, plus 1 observed redirect | Robots page displayed 404. Landing navigation automatically redirected to `https://www.google.com/shopping?udm=28`, outside the exact host allowlist. Stop: no query, merchant link or subsequent navigation. Incidental DOM text was returned before the redirect was assessed; it is excluded from this asset and from coverage/offer evidence. Future execution must check the final origin before reading content and prevent unapproved cross-host redirects where possible. |
| [Brave Search robots](https://search.brave.com/robots.txt) | 1 | Generic `/search` disallowed except conversation-specific exceptions, which do not qualify the planned watch searches. Stop; API token/plan lane excluded from this pass. |
| [HotUKDeals robots](https://www.hotukdeals.com/robots.txt) | 1 | Generic `/search` disallowed; specific AI/user-agent rules also restrict ordinary content. Stop, with no watch thread, profile or voucher acquisition. |
| [Reddit robots](https://www.reddit.com/robots.txt) | 1 | Generic all-path disallow. Stop before subreddit/search access; no posts, comments or user profiles collected. |

## Inspection and retention limits

Three snapshot calls timed out (two on AliExpress, one on eBay). DOM reading via `preview_evaluate` succeeded for eBay and subsequent hosts in the **same browser engine and session**; it only read `location`, title and visible text. It made no page mutations, network API calls or access bypass. No snapshot retries were used to reload a host.

No raw page captures, screenshots, listing content, images or community threads were saved into the repository. This asset retains operational outcomes and source URLs only. Tool responses remain in the conversation; the unresolved retention position does not make that tool history a licensed product archive. No longitudinal data collection began.

The automatic Google redirect is a protocol limitation, not an approved expansion of hosts. No attempt was made to continue on its destination. Likewise, the absence of a first-party automation grant on a route is recorded as unresolved under this protocol, not a general legal opinion about ordinary human browsing.

## Consequence for the map

Keep the source ticket **open**, with downstream blockers unchanged. Public anonymous search acquisition is not an accepted common route across these sources. A complete coverage claim still needs lawful route-specific access, identity/destination/field receipts and retention decisions; documentation and preflight outcomes do not supply them.

The next investigation can specify permitted API/feed or agent-identified routes and their access prerequisites before proposing another live protocol. Such execution, credential use, new integrations or an expanded browser allowlist is outside this approval. Do not silently substitute a different merchant or source family to close this gate.
