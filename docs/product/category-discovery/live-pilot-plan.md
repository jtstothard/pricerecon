# One-off live watch pilot proposal

Status: ready for scope review; offer acquisition NOT started. Prepared 2026-10-28
against integration `84314a7351ac1c87c31ee2543592935f01ea0bf2`.

## Purpose and products

Test whether real source outcomes can enter the approved comparison/product UI
without overstating identity, availability or UK delivered cost. Two subjects:
Addiesdive AD2066 Mint Green, and Casio MTP-B145D-2A2VEF. One unit, new condition,
fixed-price only, GB destination. No buyer postcode/address, account linking,
cart, checkout, purchase, seller contact or personal benefits. Missing shipping,
tax, selected variation or destination support means unknown delivered total.
No price history/baseline, savings claim, market-best claim or numerical freshness
policy is established by this single capture. Preserve the five-case offline
fixture unchanged; other three subjects remain outside live collection.

## Routes and current gates

Primary offer candidate: existing eBay Browse UK adapter, separate exact-reference
queries for the two subjects. One page of at most five leads each; at most two
candidate details per query, chosen by exact-reference evidence, not cheapest
price. Do not follow next pages or use auction/used/near-reference substitutes.

Preflight must establish the existing app's approval/intended use and permitted
transient retention before any token/query/detail requests. Prior successful
API calls are not sufficient proof. No new account, credential scope, affiliate
registration, service or purchase is proposed. Reuse existing authorized secret
handling only; values/tokens never enter logs or artifacts.

Addiesdive direct is excluded from automated product acquisition: its freshly
reviewed terms prohibit scraping. Direct image embedding approved in this chat
is separate from acquisition/retention of offer data. Casio official pages may
supply source identity context, not assumed stock or delivered price. No fallback
to AliExpress, a search provider, proxy or browser lane within this proposal.
If eBay prerequisites cannot be demonstrated, return a blocked preflight receipt;
do not spend the remaining request allowance on another route.

Current primary references checked during preparation:
- [eBay Buy requirements](https://developer.ebay.com/api-docs/buy/static/buy-requirements.html): production approval/contract prerequisites.
- [eBay API licence](https://developer.ebay.com/join/api-license-agreement): displayed listing age, limited copies and derivation constraints; do not create category averages or infer an archive grant.
- [Addiesdive terms](https://www.addiesdivewatches.com/policies/terms-of-service), section12: automated scraping restriction.
- [Casio UK terms](https://www.casio.com/uk/legal/terms-of-use/): source context only; no new general reuse grant asserted.

These are dated source findings, not proof of the app-specific agreement. Existing
[source readiness decision](source-qualification-decision.md) supplies history,
not current authorization to start this pilot.

## Proposed finite envelope (requires approval)

These are deliberately small proposed ceilings, not measured capacity or defaults.
Every cap is shared across the entire run and does not refill after restart.

| Dimension | Proposed maximum |
| --- | --- |
| Execution window | One run, 20 minutes from explicit start; no automatic resumption |
| Operator effort | 30 minutes for execution/review; stop if exceeded |
| Preflight documentation requests | 6 total, including redirects; existing preparation reads excluded and already reported |
| eBay requests | 7 total: 1 token, 2 search pages, up to4 details; any necessary extra auth consumes this same cap |
| Total acquisition requests | 13 including preflight and eBay; no redirect/fallback allowance beyond those counted requests |
| Search pages/results | 2 pages, 5 leads per page, no pagination |
| Item details | 4 maximum, 2 per subject; zero if no exact candidate |
| Retries / fallbacks | 0 / 0; redirects counted and only followed within approved hosts/routes |
| Browser contexts / browser time | 0 / 0 seconds; API-only arm |
| AI acquisition calls/tokens | 0 / 0; no paid extraction service |
| Incremental spend | GBP0; no purchase, new paid plan or paid provider route |
| Response body | 2 MiB per response; 8 MiB aggregate decoded response bodies |
| Normalized evidence | 2 MiB total |
| Redacted logs | 1 MiB total |
| Physical run directory incl DB/WAL/temp/logs | 50 MiB; stop before a write would exceed cap |
| Parallel requests | 1 |
| Recurring refresh / external notifications | None / none |

The existing OperatingPolicy/DurableAdmission path supplies non-refilling
request/provider/page/detail/retry/fallback/time and logical retained-storage
accounting. This proposal does not claim it enforces all physical disk, streaming
body, operator-time or billing ceilings. BEFORE a live call, implement/verify any
missing wrapper enforcement offline: allowlisted hosts, bounded streaming body,
physical run directory limit, wall-clock cancellation, secret-safe logs, denied
retry/redirect/fallback paths and cleanup. Unsupported/unobservable dimensions
block that lane; do not silently relabel a logical payload debit as physical disk.
Grant start/stop UTC values are assigned only when approved execution begins.
All tracking reserves are zero in this isolated pilot: no legacy production work
shares the run or loses budget. Production scheduler and active policies untouched.

## Storage, retention and deletion

Use a new marked temporary on-disk SQLite/run directory; never the production DB
or the buyer's synthetic walkthrough DB. Scheduler disabled, notification transport
captured/disabled, only explicitly admitted acquisition edges enabled.

Raw responses remain in bounded memory only; no HTML/API archives, cookies,
bearer headers, tokens, screenshots of merchant pages or copied image files.
Minimize seller data to fields necessary for exact-offer separation; no personal
seller identifiers in the permanent receipt. Any transient normalized listing
retention must be established as permitted by the source-specific preflight.

Transient offer data displayed only during this session, with capture time and
explicitly unknown post-session freshness. Delete the entire run DB/WAL/temp data
at stop (20-minute cap or earlier), no backup/export/indexing of merchant data.
Exclude the run directory from repository and existing backup tooling before
acquisition; verify cleanup including sidecars. If exclusion/deletion cannot be
proved, do not acquire. A permanent minimal run receipt may retain code/policy
versions, request counts, durations, byte counts, gate outcomes and reasons, with
no merchant prices, titles, IDs, payloads or user secrets. Such deletion is an
operating proposal, not an assertion that20 minutes is an automatically permitted
source-retention period. Stop sooner whenever the established grant requires it.

## Execution, ownership and stop conditions

Proposed execution/stop owner: Codex in this active session; Jay is the scope
approver. No unattended maintenance owner is assumed. Session loss/interruption
means stop, no auto-restart/catch-up. The short-lived process must terminate at
its deadline even if orchestration disconnects. Cleanup belongs to the runner's
finally/expiry path; verify it offline before authorizing live startup.

1. Prove bounded runner and containment offline against controlled transports.
2. Reconcile existing app approval and transient use/retention; record only
   non-secret evidence pointers. No new account access or message is implied.
3. Start isolated grant/ledger; execute each exact-reference query once and only
   supported details. Preserve source outcomes: blocked/capped/empty/partial differ.
4. Normalize through the normal application acquisition/execution seam. Display
   exact identity/cost qualification or abstention; do not upgrade raw-field presence.
5. Review both cases in local private UI, record usefulness/unknown fields and
   aggregate resources. Stop and delete all transient merchant records.

Stop immediately at a cap, denial/429/CAPTCHA, unexpected credential need,
redirect outside approved route, schema/identity ambiguity that prevents safe
normalization, unknown rights, unavailable disk/time accounting, cleanup failure,
or any attempted real notification/production write. Report and stop, no bypass.

## Success and handoff

Success can be a qualified current offer OR an honest unknown/blocked result.
Report discovered/inspected counts, exact matches, missing identity/cost fields,
coverage, runtime/bytes/operator minutes and each gate. GBP display alone is not
UK delivery proof; tax-array absence is not zero tax. No legal tax rate is inferred.
No coupon-success proof without exact public application evidence; no baseline
calibration from this run. After stop, live results are not kept on screen as fresh.
A later recurring study requires separate cadence/duration/retention/owner scope.

Approval requested: this numerical envelope, one-off API route and transient-only
retention, with Codex as session execution/stop owner. Approval authorizes bounded
offline runner preparation and gated preflight/execution; it does not override
missing provider prerequisites. No live offer requests have been made in preparing
this plan; four public documentation pages were opened and searched for current
requirements. No credentials, accounts or deployed services were inspected.
