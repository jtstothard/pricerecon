# Public coupon implementation receipt — 2026-10-27

Ticket: [09: Evaluate public coupons without assuming stacks](../../.scratch/watch-category-discovery/issues/09-evaluate-public-coupons.md).
Source complete for parent review; ticket closure and integration acceptance remain parent-owned.

## Workspace and authority

Worktree `/Users/jay/.t3/worktrees/pricerecon/t3-1a9ab422`, branch
`t3/evaluate-public-coupons`, initially clean at `ef86af6`. Before edits,
fast-forward merged `integration/watch-category-discovery` at `375a4a4`, including
closed04 base `c682d568b3ce49e99beaf9d1d325bea75165d954` and the parent claim commit.
Both ancestry checks passed. The pre-handoff merge/check is recorded below.

Read the exact ticket/spec, GLOSSARY, CONTRIBUTING and engineering standard,
accepted public-discount resolution/research, Watch query ADR, implementation
environment and retained cost/discovery/qualification verification contracts.
Used `/Users/jay/.agents/skills/tdd/SKILL.md` at the already approved application
API plus normal `execute_discovery` seam. No additional seam approval was needed.

Used the parent's existing `.venv/bin/python` with this checkout's source on
`PYTHONPATH`. The ignored `frontend/node_modules` symlink points to integration's
installed dependencies. Built frontend sequentially before application imports.
The original dirty parent was not edited; no integration checkout or sibling
dirty work was imported or changed. No installs/downloads, external network/live
acquisition, credentials/accounts, production DB, deployment/activation, push,
PR, delegation or buyer acceptance occurred. Local commits/merges only.

## Implementation and observable contract

- `models/coupons.py`, `core/coupons.py`, `db/coupons.py` own typed acquisition
  inputs, assessment and append-only evidence revisions. Additive migration
  **1.8** adds `discovery_coupons`; existing SQLite initialization/transactions,
  acquisition, connector health and costs remain the owners. No new scheduler,
  queue, collection endpoint or notification service.
- The feed exposes `offers[].coupons`. Read-only
  `GET /api/discovery/offers/{offer_id}/coupons` exposes retained assessments;
  writes return 405. Coverage is explicitly `supplied_acquisition_evidence_only`,
  freshness unvalidated. Empty input means no reproduced applicable public
  coupon in supplied evidence, never an exhaustive search claim.
- Retains opportunity, literal/structured terms, exact selection/basket/
  consignment/destination/payment context, inclusive/exclusive validity instants
  and source time-zone literal, quantity range, minimum spend/currency/basis,
  channel, new-customer/membership/redemption conditions, whole-stack permission
  and evidence. Unknown, forbidden and conditional compatibility cannot support
  a public payable. Terms codes identify the complete ordered promotion set;
  unlisted automatic promotions or changed order/codes withhold reproduction.
- Public, personal, payment and cashback inputs stay separate. App-only terms
  require matching evidenced app context. New-customer/member benefits remain
  conditional even if asserted satisfied; there is no account/benefit execution.
  No personal/payment/cashback opportunity lowers public payable.
- Terms/applicability never deduct anything from `public_no_coupon`. A separate
  `public_coupon` result requires distinct application receipt support, complete
  before/after basket lines and code allocations, exact eligibility, expected
  coupon/offer/binding/configuration/base-cost revisions and policy versions,
  matching terms fingerprint, full resulting payable components and quoted total.
  Every resulting component, FX quote, context and allocation must bind the same
  receipt lineage. Source-supplied `public_coupon` cost inputs alone are withheld.
- The shared cost engine reconciles item/basket allocations and calculates
  payable/FX once. No discount-rate formula or advertised-benefit subtraction is
  introduced. A synthetic £48 item → £43 item plus £2.10 shipping yields a separate
  **£45.10** result; included tax is counted once. The public no-coupon total stays
  **£50.10**. A two-watch plus strap scenario retains the whole **£98.10** basket
  commitment and cannot appear as a standalone watch price.
- Exact duplicate input is deduplicated; conflicting input is retained and
  invalidated. Safe-pointer filtering also covers withheld/conflicting payloads.
  SQL values are parameterized. Each acquisition assigns revisions and assesses
  applications in its existing immediate transaction.
- Reads check latest candidate capture, offer, binding and configuration lineage.
  Replacing a SKU/offer, removing a coupon or acquiring newer evidence invalidates
  old usable results. Original evidence and original totals remain explicitly
  historical via `historical_resulting_cost`; they are not transferred to a new
  variant. Repeated reports of one configuration within a single capture are
  retained inputs, not later corrections. A new acquisition needs a newly bound
  receipt rather than replaying an old application.
- `CouponPanel.tsx` adds expandable terms, eligibility, context, provenance,
  reproduced payable and rejection reasons. It reuses existing delivered-cost
  rendering and preserves prominent no-coupon totals. No UI write activates
  collection. Usual price/savings remain unavailable and alerts remain disabled.

## Red/green evidence — 2026-10-27

All tests use fresh child processes, temporary marked SQLite storage, controlled
clock/acquisition and captured notification transports. Assertions inspect API
and normal execution behavior, not database contents or private methods.

| Slice / expected behavior | Observed red | Observed green |
| --- | --- | --- |
| Persist opportunity without reduction | Typed report rejected unknown `coupons` field | Opportunity/history retained; £50.10 unchanged; no result |
| Terms establish applicability only | Terms/eligibility fields rejected | `applicable_not_reproduced`; no total |
| Reproduce exact receipt separately | Application field rejected | £45.10 full result; duplicate input yields one assessment; £50.10 base unchanged |
| Withhold unsupported offer | Missing explicit exact-offer rejection in proof checks | `exact_offer_not_supported`; no coupon total |
| Restart and changed terms | Older successful assessment stayed usable | New assessment invalidated; old £45.10 historical; fresh bound receipt accepted; removal invalidates all prior applications |
| Full allocation/policy contract | New allocation contract initially rejected | Missing/duplicate lines, wrong totals/quantities and changed policies withhold |
| Attribute every reduced line | Unallocated line reduction incorrectly produced a result | `line_eligibility_or_codes_mismatch`; no result |
| Replace selected SKU | Old offer ID still exposed usable application in history | Candidate-capture check invalidates it; corrected selection cannot reuse old costs |
| Browser coupon workflow | Missing coupon-control timeout; then payable amount was hidden behind nested details | Visible separate payable, expanded complete components, advertised/empty paths, unchanged no-coupon total |

Additional passing checks cover start/end inclusive/exclusive seconds, unknown
zone, minimum-spend boundary/currency, quantity range, app mismatch and matched
app, unknown/forbidden/conditional stacks, missing stack evidence, explicitly
supported ordered stack, new-customer/membership restrictions, personal/payment/
cashback separation, altered basket/destination/SKU, wrong/rejected receipts,
missing shipping/components, advertisement reuse, stale revisions, unsafe URLs,
conflicting derivation, malformed timezone input as acquisition `parse_error`,
and default staged execution without external-edge calls.

## Verification commands and results

From this worktree, after the frontend build:

```sh
env -i PATH=/Users/jay/.nvm/versions/node/v24.14.1/bin:/usr/bin:/bin \
  PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PWD/src:$PWD" \
  /Users/jay/.t3/worktrees/pricerecon/t3-7260bb2e/.venv/bin/python -m pytest -q \
  tests/test_coupon_workflow.py tests/test_cost_workflow.py \
  tests/test_qualification_workflow.py tests/test_discovery_workflow.py \
  tests/test_monitoring_workflow.py
```

**Passed: 58 tests in 87.74s**: all **48 retained application workflows** plus
**10 coupon workflows**. No skips, xfails, removed assertions or suppressions.
Earlier combined pass was 56 before the two final safety workflows were added.
Focused Ruff passed all 13 changed Python files. Focused mypy
`--follow-imports=silent` passed all nine changed source files, with inherited
unused-override notes only. `git diff --check` passed.

From `frontend`, using existing Node 24.14.1 on PATH: `npm run build` passed
(inherited large-chunk warning), `npm test -- --run` passed **25 tests**.
`npm run lint` remains **blocked** by the inherited ESLint 10.12.0 missing
`eslint.config.*` error. No lint config/dependency changes were made.

Browser reproduction (build first, run server in one terminal and driver in
another; driver uses existing Chrome, unique session and loopback-only origin):

```sh
env -i PATH=/Users/jay/.nvm/versions/node/v24.14.1/bin:/usr/bin:/bin \
  PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PWD/src:$PWD" \
  /Users/jay/.t3/worktrees/pricerecon/t3-7260bb2e/.venv/bin/python \
  -m tests.monitoring.discovery_ui_server --coupons --port 8889

PATH=/Users/jay/.nvm/versions/node/v24.14.1/bin:$PATH \
  /Users/jay/.t3/worktrees/pricerecon/t3-7260bb2e/.venv/bin/python \
  -m tests.monitoring.discovery_browser_check --coupons --port 8889 \
  --artifacts /tmp/pricerecon-ticket09-browser-final
```

T3 status/open/navigation were attempted first. Both snapshots returned exactly
`Preview snapshot failed: Preview automation snapshot timed out after 15000ms.`
Used the authorized retained Chrome/agent-browser fallback. The installed
agent-browser does not support its newer skill stub's `skills get core` command;
the existing repository driver/CLI was usable without installing anything.

Final driver **passed**: fixture identity checked before writes, keyboard
preferences save/reload, five illustrated cases, full no-coupon path, advertised
opportunity, reproduced receipt and complete payable, expanded evidence,
1280×900/375×812, no horizontal overflow, legacy enabled/paused searches,
and no browser errors. The fixture labels all assertions synthetic. One earlier
follow-up run was interrupted by stopping its fixture before legacy navigation;
it is excluded from the successful final receipt. Both owned servers shut down;
each reported `blocked_edges=[]`, `notifications_sent=0`, `searches=3`,
`temporary_storage=true`.

Retained [browser receipt](artifacts/watch-coupons/receipt.json),
[desktop view](artifacts/watch-coupons/desktop-coupons.png) and
[375px view](artifacts/watch-coupons/narrow-coupons.png). Full-page temporary
captures remain at `/tmp/pricerecon-ticket09-browser-final/` for this run.

## Remaining gates

Fixture success is **not live coupon proof**, settlement, current freshness,
source completeness, lawful retention/access, ordinary-price savings, alerts,
or buyer walkthrough acceptance. No real watch coupon/application or UK tax rule
was qualified. Existing adapters' loose coupon metadata remains unverified;
production evidence mapping needs its own authorized source-specific work.
Collection remains staged; no cadence, cap or freshness policy was invented.

Ticket07 correction UI has not landed in the integration base. Invalidation is
tested at the accepted acquisition/revision/policy seam, including replacement
of a selected SKU and retained old receipts. Parent integration must connect and
verify the later correction UI's append/invalidation transaction against coupon
lineage, including overlapping correction/acquisition. No correction UI, target/
alert subsystem (05), or general observation history (06) was implemented here.

The parent owns integration merge acceptance, ticket closure, any later release
gates and buyer review. This branch grants no operational authority.

## Pre-handoff integration check — 2026-10-27

The integration tip advanced during final handoff to `bd5a3fb` (ticket06's
committed observation history). The first refresh was refused because coupon
edits were uncommitted; no merge ran over them. Committed the completed coupon
slice locally as `9b9f875`, then merged the committed integration tip. This
corrects the premature "Already up to date" wording in the initial slice commit.

Resolved three conflicts by preserving **both** read-only endpoints and **both**
fixture/driver modes. Coupon and history fixture switches are mutually exclusive
to keep fixture identity and synthetic data unambiguous; existing modes remain.
Automatic merges retained ticket06's acquisition/history/schema/typing/UI work
and the coupon feed/storage/wiring. No sibling dirty work was read or imported.
Rebuilt the combined frontend before new application imports.

Before this refresh, the final fixture-only wording correction (consistent
ordered-stack/two-watch terms literals) was followed by **10 coupon workflows
passed in 12.99s** and focused Ruff passed again. No coupon source behavior
changed after the original 58-test pass.

### Combined verification

- **65 passed in 92.84s** using the full command above plus
  `tests/test_history_workflow.py`: all 48 retained workflows, 10 coupon workflows
  and 7 ticket06 history workflows. No skips/xfails or weakened checks.
- Combined frontend build and all 25 frontend tests passed. Focused Ruff passed
  15 files; focused mypy passed 11 source files, including the merged history
  models/storage, with inherited unused-override notes only.
- Re-ran both browser workflows on the merged tree: coupons on **8889**, history
  on **8890**, with separate fixture storage and browser sessions. Both passed
  fixture identity, API/UI assertions, reload, desktop/narrow layout, legacy
  navigation and browser-error checks. The coupon run includes the complete
  £45.10 receipt and unchanged £50.10 public base; the history run includes all
  retained capture/gap/age/policy evidence assertions. Updated retained coupon
  screenshots from this combined run. The additional history receipt is retained
  beside them as `merged-history-receipt.json`; full temporary artifacts are at
  `/tmp/pricerecon-ticket09-browser-merged` and
  `/tmp/pricerecon-ticket09-history-merged`.
- Both combined fixture servers shut down: coupon `searches=3`, history
  `searches=10`; each reported `blocked_edges=[]`, `notifications_sent=0` and
  temporary storage. No automatic collection or live proof.

Integration then advanced to `b97f37a` with the parent's ticket06 merger receipt
and retained diagnostic. Its documented **derived-capture independence gap**
remains open for the ticket06 owner; the 65 passing workflows do not close that
additional failing acceptance probe or certify history independence. This worker
reviewed the record and did not implement ticket06's repair or repeat the probe.

Final refresh merged `b97f37a44241bf29d5a252a191e93e8bc240cb0f` without conflicts;
only the parent's documentation/tracker/diagnostic artifacts were added, with no
application-source changes after combined verification. Both latest integration
and closed04 ancestry checks passed. The worktree was clean after local merges.

## Merger verification — 2026-10-27

**Ticket09 remains open: compatibility or eligibility evidence alone can support
a reproduced coupon payable.** This merger-only pass makes no production repair.

### Integration identity and history

Integration `/Users/jay/.t3/worktrees/pricerecon/watch-category-integration`,
branch `integration/watch-category-discovery`, was clean at requested
`b97f37a44241bf29d5a252a191e93e8bc240cb0f`. Source
`/Users/jay/.t3/worktrees/pricerecon/t3-1a9ab422`, branch
`t3/evaluate-public-coupons`, was clean at requested
`db08536203eeba32cd7e462b28b977237492d955`. The integration tip was already
an ancestor of source. The explicit `git merge --no-ff --no-edit db085362...`
produced `2b4686bc2c60ff397502c9ace2f10e225423199f`, with integration/source
as its first/second parents, without conflicts. Source remains unchanged and
clean at its requested HEAD. The original dirty parent and active05/06 repair
checkouts were not modified. Only the existing parent's Python executable and
installed integration frontend dependencies were used.

Read the spec/issue09, accepted public-discount resolution/research, standards,
and this source receipt against history. Reviewed the source's prior merge
`f5cf24a` conflict resolution: both read-only coupon/history endpoints remain,
and both guarded fixture/driver modes remain, mutually exclusive. Its later
`3dab4d6` merge brought in `b97f37a` documentation/probe artifacts only.
The resulting integration application/frontend/driver/server tree exactly
matches source HEAD. No actual conflict or implementation change was required
in this merger.

### Passing checks and bounded evidence

- **65 passed in 78.31s** using the cleared-environment six-file pytest command
  documented above, including `tests/test_history_workflow.py`: all **48 baseline**,
  **seven history** and **ten coupon** workflows. No skips, xfails, removals or
  weakened assertions. These passes do not override the additional failure below.
- **25 frontend tests passed**, and the production TypeScript/Vite build passed,
  run sequentially before application imports using installed Node24.14.1.
  The existing large-chunk warning remains. Prior ESLint10 missing-config
  blockage is retained from source; lint was not rerun or worked around.
- Focused Ruff passed **15 merged Python files**, plus the new merger probe.
  Focused mypy `--follow-imports=silent` passed **11 source files**, including
  merged history storage/models; only inherited unused-override notes appeared.
  `git diff --check` passed. No suppressions or dependency changes were added.
- Inspected the actual retained [desktop PNG](artifacts/watch-coupons/desktop-coupons.png),
  [375px PNG](artifacts/watch-coupons/narrow-coupons.png), browser JSON and driver.
  They expose separate GBP45.10 payable, observation-only wording, explicit
  compatibility/terms/minimum/time boundaries and no-coupon preservation.
  The retained driver additionally asserts complete payable, expanded evidence,
  opportunity/empty scope, reload, legacy navigation and no narrow overflow.
  No new browser session or buyer acceptance is claimed. PNG SHA-256:
  desktop `2623ce8463f889f9d52f0991cc5115b4208fc6b4f24e61684a9ae373684d2376`,
  narrow `9b6b008d81d0118430e06a904c48c2e687bc73954a6fadc315ce948afcf22ba6`.
- Application workflows exercise persistence/restart, exact SKU/basket/destination/
  payment/quantity context, spend/currency thresholds, inclusive/exclusive expiry,
  app/new-customer/member conditions, explicit ordered stack permission, unknown/
  forbidden stacks and personal/payment/cashback separation. Terms/applicability
  alone normally retain the no-coupon total without creating a coupon payable.
  Complete basket commitment and included-tax-once reconciliation use the shared
  cost engine. Direct source-supplied `public_coupon` costs remain withheld.
- Changed terms fingerprints, acquisition/offer/binding/configuration/base-cost
  revisions and policy versions withdraw old application results. Replacement
  selected SKU cannot inherit the old result; old evidence/total remains
  historical. Ticket07 correction UI is absent. Its correction transaction and
  overlapping acquisition remain an explicit future integration gate, with no
  end-to-end correction acceptance claimed here.

### Reproduced coupon acceptance gap

`core/coupons.py` checks application derivation roots against ordinary terms and
opportunity roots, but excludes `terms.compatibility_evidence` and
`eligibility.evidence`. The generic resulting-component checks then accept those
same roots as application support. The typed `result: applied` and fully
reconciled amounts do not establish that their evidence is a checkout receipt.

The extra [guarded API/execution probe](../../tests/monitoring/coupon_merger_probe.py)
submits two exact supported synthetic offers. In each, all original checkout
evidence is removed from the application, payable context, components and line
allocations. One input reuses only the **unchanged compatibility claim** (ID
`synthetic:stack`, locator `$.terms.stack`, root `synthetic-original:stack`);
the other reuses only the **unchanged eligibility claim** (locator `$.eligibility`,
root `synthetic-original:eligibility`). Their evidence IDs, context, pointers,
timestamps and roots remain visible as those non-application claims. No independent
checkout capture supports either reduced payable.

**Expected:** preserve the opportunity/terms/applicability and original evidence,
but withhold reproduced application and verified coupon payable.

**Observed independently in an inline diagnostic and the retained module:** both
feed and persisted coupon-history API return `state: reproduced_at_observation`,
`issues: []`, and verified resulting/merchant payable **GBP45.10**. All public
no-coupon totals remain **GBP50.10**, savings remain null and alerts ineligible.
This is a coupon evidence-classification failure independent of ticket06's
documented derived-capture history gap.

The same probe includes a positive shipping control with genuine synthetic
checkout provenance and newly quoted **GBP4.20** shipping. The shared cost engine
correctly yields **GBP47.20**, rather than reusing base shipping or subtracting
an advertised discount. The JSON is written before the intended failing
assertion. [Recorded receipt](artifacts/watch-coupons/merger-receipt-provenance.json).

Reproduce from integration using existing dependencies only; current expected
exit is **1**, naming both unsupported receipt cases:

```sh
env -i PATH=/Users/jay/.nvm/versions/node/v24.14.1/bin:/usr/bin:/bin \
  PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PWD/src:$PWD" \
  /Users/jay/.t3/worktrees/pricerecon/t3-7260bb2e/.venv/bin/python \
  -m tests.monitoring.coupon_merger_probe \
  /tmp/pricerecon-ticket09-receipt-provenance.json
```

All inputs are original synthetic data. Temporary marked SQLite, paused checks,
staged collection, controlled acquisition/time, captured notification transports
and blocked outgoing edges were used. Both diagnostics recorded
`blocked_edges: []`, `notifications_sent: 0`. No pytest test was weakened or
replaced by this intentionally failing, non-collected acceptance probe.

### Disposition and remaining gates

**09 stays open for receipt-provenance repair**; the unchecked distinction between
terms/applicability and reproduced exact application prevents acceptance. The
passing no-coupon path does not close that gate. No later implementation or
production fix was made. Ticket06's parent-owned lineage gap remains open,
without repeating or modifying its diagnostic; active05/06 repair worktrees and
their status were untouched. Ticket12 remains blocked by09 and its other gates.

Collection stays staged. No live coupon/buyer proof, account eligibility,
production evidence mapping, source rights/retention, freshness, comparisons,
savings, alerts, deployment or activation acceptance is established. No installs,
external network/live acquisition, credentials/accounts, production DB operations,
activation/deploy, push, PR, delegation or unrelated cleanup occurred. Only the
local history-preserving merge, probe, receipt and tracker changes were committed.
