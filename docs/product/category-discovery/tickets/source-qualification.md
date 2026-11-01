# Which source routes can support an honest watch discovery claim?

Tracker identity: `source-qualification`  
Parent: [Find the route to trustworthy category deal discovery](../MAP.md)  
Label: `wayfinder:research`  
Type: Research (AFK)  
Status: closed  
Assignee: jtstothard (Codex; 2026-10-27)  
Blocked by: None

## Question

Choose a representative watch cohort and explicit route roster covering AliExpress, eBay/relevant second-hand, brand-direct, UK and UK-shipping international retail, search engines, shopping aggregators and deal communities. Which routes can discover, monitor, enrich and verify an offer, and under what access, pagination and freshness limits?

## Evidence required

Use the audit's registration inventory and inspect current official source/API access and retention terms. Specify a separately authorised bounded live read-only protocol; actual live access is not granted by this ticket. Record per-route timestamp, query/category, pages/caps, credential/account prerequisites, destination, exact variant, stock, currency/shipping/tax fields, success/failure/partial result and evidence pointers. Distinguish historical receipts, fixtures, source inspection and fresh live observations. Identify watch-relevant second-hand and direct merchants rather than inferring relevance from a PC retailer connector.

Starting context: [source audit](../audit.md), [domain proposal](../domain.md), [product brief](../brief.md), [slice](../vertical-slice.md). These are inputs, not accepted answers.

Additional input: [prior watch corpus, manifest and proposed cases](../watch-research-context.md). Use the source conflicts as investigation cases; do not accept the prior evidence labels or prices without reconciliation.

## Decision and acceptance gate

Accept a coverage matrix naming qualified, provisional, blocked and unsupported routes with explicit evidence level and gaps. No supported/working designation solely from registration or mock tests. Gate remains open where required live receipts or access authority are missing. Recommend the smallest useful cohort without deleting mandatory source families. This is the first unresolved gate.

## Resolution comments

Resolved by the dated decision comment below. Earlier progress entries are retained as the investigation record.

## Progress comment — 2026-10-27

Claimed by jtstothard, driven by Codex. Completed a bounded source/documentation investigation with a research subagent; see [source qualification documentation, coverage matrix and proposed live protocol](../source-qualification-research.md). The proposed five-case cohort adds a Casio exact-colour-reference case to the four retained conflict cases for mainstream retail/used coverage. Exact configurations and route qualification remain unaccepted.

No route qualified: no merchant offer, connector, credential, basket or checkout was exercised. Required live receipts and access/retention prerequisites remain missing, so this is a progress comment, **not a resolution**; status stays open and downstream dependencies stay blocked. The asset proposes an anonymous public read-only pass capped at 60 minutes/60 document navigations, with named hosts, per-host caps and stop rules. That pass awaits explicit authority under the map's standing boundary; credentialed APIs, connector execution and checkout would still be excluded.

## Progress comment — approved anonymous pass, 2026-10-27

The user explicitly approved the proposed public read-only protocol after reviewing it. Executed its preflight in an Incognito T3 preview; see [approved pass receipts and limits](../source-qualification-live-pass.md). All 12 host preflights were attempted; 15 explicit navigations and one observed automatic redirect, zero offer searches/details, zero qualified routes. Access restrictions, unresolved identification and inspection failure stopped acquisition. Google redirected outside the allowlist automatically; no further navigation followed and incidental content is excluded. No APIs, credentials, connectors, basket or checkout were used.

This comment supersedes the earlier statement that the proposed first pass awaits approval. The approval was consumed by this pass and does not authorise a repeat or broader lane. **Not a resolution:** live offer qualification and retention/access gates remain unmet; status and downstream blockers remain unchanged.

## Access-plan discussion — 2026-10-27

User agreed to Camofox, Playwright and CloakBrowser as browser options, and per-connector sessions. These are planning choices, not proof of installed services or authorization to install/deploy/connect accounts. Session isolation must be demonstrated per connector and storefront; a shared Shopify adapter must not share merchant state by default. Persistent authenticated state remains subject to separate account authority.

User asked whether Byparr should replace FlareSolverr. Recommendation: qualify Byparr as the preferred solver candidate through the existing FlareSolverr-compatible adapter, before changing any working service. Current PriceRecon sends `request.get`, URL and `maxTimeout`, and reads `solution.response`; upstream Byparr exposes that request/response shape. This is inspected compatibility, not a live acceptance result. Keep the protocol name distinct from the deployed provider; no new backend type is necessary just to name Byparr.

Important session limit: the reviewed Byparr main-branch request model has no session identifier or session-management commands; its browser dependency creates a fresh context per request. PriceRecon's solver request also sends no session field. Therefore Byparr is a candidate for isolated one-shot HTML retrieval, not accepted persistent per-connector sessions. Use the agreed browser services for persistent sessions where needed, and verify separate profiles/contexts, cleanup, expiry and absence of state transfer across connectors. Current Camofox defaults include shared generic identifiers; configuration must explicitly override those for this plan.

Acceptance before any provider switch: pin a reviewed Byparr version, verify request/timeout/error/HTML semantics, test representative permitted watch routes, confirm session isolation and resource limits, and retain the existing working route until the replacement passes. No live solver request, health check, installation, service replacement or config change was performed in this discussion.

Primary sources inspected: [Byparr request/response model](https://github.com/ThePhaseless/Byparr/blob/main/src/models.py), [API endpoints](https://github.com/ThePhaseless/Byparr/blob/main/src/endpoints.py), [per-request browser lifecycle](https://github.com/ThePhaseless/Byparr/blob/main/src/utils.py). These are mutable main-branch inspection links, not a pinned release qualification. Local evidence: [solver adapter](../../../../src/pricerecon/connectors/flaresolverr.py), [external browsers and session defaults](../../../../src/pricerecon/connectors/external_browser.py). Source gate remains open.

## Progress comment — existing Byparr verified, 2026-10-27

User authorised running the existing solver test. [Deployment and live client receipts](../byparr-live-check.md) confirm Byparr is already running on Proxmox VM 101 and reachable from the deployed PriceRecon client. The deployed client matches the worktree source hash. The control page and AliExpress robots page returned HTML; the earlier AliExpress preview inspection failure is therefore resolved for this alternate, now-authorised lane. No challenge solve, watch discovery or offer qualification is claimed. No installs or service/config changes were needed. The running API exposes no named-session support, so per-connector persistent sessions remain an unproven browser requirement. Source ticket remains open; downstream blockers unchanged.

## Progress comment — browser readiness and isolation, 2026-10-27

User authorised continued existing-service work. [Browser readiness and live control receipts](../browser-readiness-check.md) prove that the installed CloakBrowser binary isolates explicitly separate contexts, while exposing a deployed content-contract gap: the wrapper/adapter control returns a correct title with no HTML/snapshot/network content and degradation `none`. Camofox is reachable/connected but protected operations were not exercised. Its context is keyed by `userId`; `sessionKey` is only a tab-group key, so distinct session keys alone do not meet the agreed connector isolation requirement. Standalone Playwright's expected binary is missing in the inspected container. No install, source/service/config change, credential or account access occurred.

[Route-specific documentation](../source-access-followup.md) corrects the earlier blanket treatment of search-path blocks and identifies clean category/product candidates. Militado's explicit read-only route still needs agent identification; successful retrieval alone cannot establish it. No merchant offers were acquired and the source gate remains open. Required corrections/access prerequisites are now concrete in the readiness asset; downstream blockers remain unchanged.

## Progress comment — browser fixes applied and live-verified, 2026-10-27

The user explicitly instructed fixing both browser integrations. [Deployment and verification receipt](../browser-fix-deployment.md) records the scoped exception to the original planning-only boundary: corrected the existing wrapper and PriceRecon client, recreated only those two services, and verified the live connector paths. CloakBrowser now returns bounded HTML and page metadata; title-only responses no longer pass. Anonymous Camofox contexts are connector/merchant-scoped, with actual cookie/storage isolation verified. Existing assigned account profiles and production concurrency guards were preserved. Internal service-key use was limited to new test contexts' evaluation/cleanup without exposing the key or accessing account state. No global browser default or new monitoring route was enabled.

69 focused local Python tests, 2 wrapper tests, and 54 deployment-specific Python tests passed. Post-deployment checks passed through the actual connector interface. Browser integration acceptance is now established for the tested content/session paths; merchant coverage, identity, destination, costing and source access/retention gates remain unqualified. Source ticket stays open; downstream decision blockers are unchanged.

## Progress comment — first merchant-route evidence, 2026-10-27

Continued within the authorised existing-browser investigation. [San Martin retailer category/product receipts](../san-martin-source-receipts.md) establish a point-in-time Camofox discovery path and partial selected-product fields, including two different Miyota movement configurations under SN0144. CloakBrowser category HTML was truncated before useful body links; it is not an empty catalogue. The second product diagnostic was incomplete because script text overwhelmed output, and was not refetched past the detail cap. Only factual receipts were saved, and the anonymous test context was closed. No UK delivered total, accepted saving, SKU completeness, recurring monitoring or archive permission is established.

[Remaining access actions](../source-access-actions.md) distinguish infrastructure from source entitlements/signing/use rights. Boolean inventory confirms existing eBay and AliExpress application credential fields are set; no source API credentials were used. A concrete five-request read-only API probe is specified there for explicit credential-use approval. Source ticket stays open and assigned, with downstream blockers unchanged.

## Progress comment — approved source API probes, 2026-10-27

User explicitly approved the five-request, no-retry credentialed API protocol. [Dated API receipts and limits](../source-api-access-receipts.md) record four actual requests: eBay token, UK watch query and returned item detail all succeeded; AliExpress affiliate signed query returned four records, but no detail candidate was established and no fifth call was made. The AliExpress selection diagnostic covered fewer title aliases than the production parser, so it does not establish an empty/irrelevant market result. No raw content/history, tokens, credentials or account data were saved and no app monitoring/deployment occurred.

Raw eBay field availability and AliExpress affiliate query access are now live-observed. Exact configuration, UK offer completeness, normalised connector behaviour, repeated freshness/retention and other source families remain open. An existing credential-derived eBay OAuth log key was identified in source; this bounded probe avoided that helper, and no production-log exposure is asserted. Any correction is separate scope. Source ticket remains open and assigned; downstream blockers unchanged.

## Progress comment — browser-first AliExpress evidence and OAuth correction, 2026-10-27

User asked for the AliExpress browser route rather than affiliate-only access and explicitly approved correcting the eBay helper. [AliExpress browser receipts](../aliexpress-browser-receipts.md) now establish a public wholesale-search snapshot with 28 distinct item links and the tested ML05 PID, plus a separate direct product snapshot with title and displayed price/VAT claim. The browser route makes no affiliate API call, but no item's non-affiliate eligibility or market completeness is asserted. Selected SKU and UK delivered total remain unverified. This used the repaired shared adapter, not accepted full-connector browser-first routing. New anonymous contexts were closed.

[OAuth helper correction](../ebay-auth-logging-fix.md) removes credential-bearing diagnostics and sanitizes auth errors. It passed 24 focused tests and staged/deployed synthetic checks, and was deployed as a source-only image update without touching existing credentials/token storage or browser fixes. This is the explicit maintenance exception for that helper; historical logs were not audited or purged. Source qualification stays open; downstream blockers unchanged.


## Progress comment — staged browser-first connector, 2026-10-27

User agreed to implement the browser-first workflow. [Implementation and staged receipts](../aliexpress-browser-workflow.md) establish full connector discovery/product inspection through Camofox without affiliate calls. Final run found 24 item links and inspected the discovered ML05 PID; it retained the selected 2035 movement despite the VH31 title, GBP35.82 display and a VAT claim. Search inspection was capped; selected SKU/price binding and UK delivered cost remain unknown, so the route rejects ordinary monitoring output. CloakBrowser's live search remained truncated and was rejected. 66 focused Python tests, narrow mypy, two Node contracts and an isolated native-browser DOM fixture passed. The changes are staged, not deployed; production polling unchanged. Source ticket remains open and assigned, with downstream blockers unchanged.


## Authority update — 2026-10-27

After reviewing the staged AliExpress connector results, the user stated: “I approve you doing everything needed for this ticket of the wayfindder”. Continue the source investigation and necessary targeted corrections/verification without repeating earlier per-pass user approval requests. This supersedes those earlier user-scope blockers for this ticket; it does not establish provider entitlements, permitted retention, selected-offer truth or acceptance of ongoing polling. The ticket remains claimed by jtstothard. Source access/retention documentation is being refreshed while remaining live fields are investigated.


## Resolution comment — 2026-10-27

Accept the [source roster, five-case cohort and operation-specific coverage classifications](../source-qualification-decision.md), supported by the [fresh primary-source access/retention review](../source-qualification-access-resolution.md) and linked live/staged receipts. The Casio case is pinned to manufacturer reference MTP-B145D-2A2VEF. AliExpress Camofox browser discovery is independent of affiliate filtering, and public variant selection changed the observed price from GBP35.82 (2035) to GBP48.52 (VH31); stable SKU/UK delivered proof remains missing. eBay UK Browse supplies distinct full-reference/new and used-condition evidence, with counterexamples correctly excluded from exact comparison. Existing SearXNG transport is healthy but search/retention remains unqualified.

Each mandatory source family remains represented. Restricted/missing operations have evidenced access stops or named prerequisites rather than fabricated success: Militado signing identity, Reddit approval, HUKD access/use information, actual Brave storage-plan authority, eBay historical-use/derivation rights, and retailer selected-offer/reuse gaps. The exact Google Shopping search candidate is robots-disallowed; Sakura and Chrono24 clean/root crawlability does not grant general automation or archival rights. No route is accepted for complete selected UK offer verification or repeated monitoring.

This closes the **research classification decision**, not source activation or later identity/history/cost acceptance. The original gate's required live/access outcomes are supplied as tested positive operations or explicit blocked/unqualified outcomes, consistent with its qualified/provisional/blocked/unsupported matrix requirement. Missing rights and offer fields are carried into the existing downstream questions, with no mandatory family dropped and no inferred grant. The next frontier is [What constitutes an exact configuration and sufficient identity evidence?](identity-evidence.md). No other ticket was resolved, and the map remains open.

Verification: new documentation links checked; prior 66 focused tests and staged connector verification remain linked in their receipt, with no new runtime source change in this pass. The exact anonymous Camofox context was removed (HTTP200/ok), and production PriceRecon/CloakBrowser image readbacks remain unchanged. No new production polling, deployment, raw price archive, commit or push was needed to resolve this research question.
