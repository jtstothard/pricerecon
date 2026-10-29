# Browser readiness and connector-session evidence

Investigated 2026-10-27 following the user's approval to continue the existing-service work. Parent: [Which source routes can support an honest watch discovery claim?](tickets/source-qualification.md). Related: [Byparr receipts](byparr-live-check.md), [route-specific access follow-up](source-access-followup.md).

## Result

Existing services can be reused, but the agreed browser options are not three interchangeable, qualified acquisition routes. Byparr retrieves HTML. CloakBrowser can launch and isolate contexts, but its deployed HTTP wrapper omits page content. Camofox is reachable and connected, with protected operations requiring an API key. Standalone Playwright's expected Chromium binary is absent in the inspected container.

This pass used read-only inspection, public documentation, service health reads and disposable browser/control-page probes. It installed nothing, changed no service/configuration, used no account/profile or credential, and triggered no PriceRecon monitoring, notifications or DB writes. Browser processes/contexts created for the probes were closed. No merchant offer/category page was fetched in this pass. The earlier prediction that a watch-source route would be tested did not become an offer acquisition: access requirements and the browser content contract remained unresolved.

## Observed deployment and probes

| Component | Evidence | Accepted conclusion |
| --- | --- | --- |
| Byparr | Prior live adapter receipts and pinned deployed image in [existing check](byparr-live-check.md) | HTML retrieval works. No named persistent-session support demonstrated. No reason to install a replacement. |
| CloakBrowser service | Container `cloakbrowser` on Proxmox VM 101; package `cloakbrowser` **0.5.0**; installed binary **146.0.7680.177.5** at `/home/node/.cloakbrowser/chromium-146.0.7680.177.5/chrome`. Shared network namespace with `gluetun`; reachable from deployed PriceRecon at `http://gluetun:9378`. | Existing binary and service available. Private network endpoint is a probe observation, not a configuration change. |
| Playwright | Existing Node package resolves expected standalone Chromium to `/home/node/.cache/ms-playwright/chromium-1228/chrome-linux64/chrome`; file absent. | The package exists, but its expected standalone browser is missing in this container. No host-wide claim and no install attempted. |
| Camofox | Proxmox VM **102 / media-vm**, container `camofox-browser`, image `camofox-browser-local:135.0.1-healthfix`; endpoint `http://<private-host>:9377`. At **10:10:31.129404 UTC**, health HTTP 200, `ok=true`, `browserConnected=true`, `browserRunning=true`, `activeSessions=0`. | Service reachable from deployed PriceRecon. This is not a successful merchant navigation or protected API call. |
| CloakBrowser health | **10:10:31.227267 UTC**, HTTP 200, `ok=true`, `activeSessions=0`. | Service responds before the control probe. |
| CloakBrowser via deployed PriceRecon adapter | At **10:10:32.293554 UTC**, temporary in-process backend `qualification_cloak` selected only `http://gluetun:9378`; navigated `https://example.com` with 100 ms settle and 25 s timeout. Result: title `Example Domain`, degradation `none`, **HTML length 0, snapshot length 0, network responses 0**. | Reproduced a content-contract gap through the actual adapter. No production backend selection was saved; no fallback engine used. Success status/title do not establish usable extraction content. |

Execution receipts are the tool-call history in this conversation. No raw website content or credentials were saved into this asset.

## CloakBrowser isolation probe

**10:08:57.181–10:08:57.891 UTC.** Used the installed CloakBrowser binary through its existing Playwright package, with no downloaded browser and no CloakBrowser auto-update call. A fresh browser contained contexts A and B. Each context intercepted every page request and fulfilled an in-memory HTML document at `https://pricerecon-probe.invalid`; no merchant navigation or external request was issued by these context pages.

A received a synthetic cookie and local-storage marker. Results:

- A contained both markers: **true**.
- B contained neither marker: **true**.
- A retained both after reload within that context: **true**.
- A was closed; a newly created context contained neither marker: **true**.

Contexts and browser were closed in cleanup. This proves basic isolation between explicitly separate contexts using the installed binary. It does **not** prove persistent profiles, restart recovery, production connector-to-context assignment, or account/session transfer. It is not a test of an independent stock Playwright Chromium installation.

## Camofox: isolation key is userId

Read the deployed `/app/server.js` on VM 102. `POST /tabs` obtains the browser context through `getSession(userId)`; `sessionKey` selects a tab group inside that existing context. Therefore:

**Different sessionKey values under the same userId are not an accepted cookie/storage isolation boundary.**

The accepted per-connector-session requirement needs separate context-owning `userId` values per connector/merchant/user context, in addition to whatever tab-group keys are used. The shared Shopify connector must not reuse merchant state across storefronts. A connector with public and personal-account lanes needs explicit separation between them. These are requirements for later implementation, not changes made by this probe.

The deployed service reports an API-key environment variable present, without exposing or using its value. Evaluation and session deletion are protected routes. No disposable Camofox sessions were created because their full probe/cleanup would require protected operations. No Facebook session, key, cookie export or other user's state was used. Camofox isolation is source-inspected, not runtime-proven here.

## CloakBrowser: precise content-contract gap

The deployed wrapper's normal `/api/browser/session` handler creates a fresh browser/context per request and closes the browser afterward. Its `_render` result contains navigation/title/status metadata and selected response metadata, but **does not contain `html`, `content`, `snapshot` or a final-page URL**. The PriceRecon adapter reads missing HTML/snapshot fields as empty strings, which the control test reproduced.

Required correction before merchant qualification:

1. Define which evidence the connector needs: rendered HTML/text versus captured API response, plus final URL, main-document status and blocked-page classification.
2. Make the wrapper return that bounded evidence and make the consumer reject missing required content. Preserve response redaction and size caps; do not manufacture an intercepted-response claim from a title or DOM.
3. Prove the contract with a controlled page containing known fields and an empty/blocked/error page, then one permitted merchant route.
4. If persistent per-connector sessions are needed, specify ownership, lifetime, cleanup and expiry; the current one-browser-per-call endpoint cannot be described as persistent.

These are planning findings. No wrapper or application source was modified or deployed.

## Watch-source access remains a separate gate

The [documentation follow-up](source-access-followup.md) identifies clean category/product candidates instead of treating a search-path prohibition as a blanket host prohibition. Militado explicitly describes read-only public HTML, but requires agent identification including Web Bot Auth for remote/server traffic. No such signer or identity was demonstrated in the existing browser services.

Current [AliExpress terms](https://terms.alicdn.com/legal-agreement/terms/suit_bu1_aliexpress/suit_bu1_aliexpress202204182115_66077.html), updated 26 August 2026 and effective 26 September 2026, restrict systematic collection/database compilation without written permission. This is a collection/retention prerequisite for the proposed history workflow; do not infer it from a successful robots fetch or equate crawler-specific robots rules with every user-initiated browser. No AliExpress offer history/archive was started.

Source gate stays open. The next work is concrete: correct/qualify the bounded content contract, establish a permitted identified source route, and verify connector/merchant context ownership. The existing solver and browser binaries can be reused; additional installation is not the first unresolved step for CloakBrowser.
