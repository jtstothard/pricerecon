# Ticket12: connected offline watch proof and buyer handoff

Dated 2026-10-27. **Ticket12 remains open. Actual buyer walkthrough feedback is
unproven and belongs to the parent merger.** This package demonstrates deterministic
application behavior; it does not establish live workflow proof, release readiness,
complete coverage or a global best price. Collection remains staged.

The sole implementer used `/Users/jay/.t3/worktrees/pricerecon/t3-dbe22e28`, branch
`t3/watch-workflow-verification`. Its initially clean `ef86af6` fast-forwarded to
integration `9ce8d31236192a8e6b98152a835ff68b4dd03bda` before edits. Local commits
are authorized by the dispatch, superseding the ticket's older no-commit sentence.
No application production module or frontend behavior was changed. Final checkout,
ancestry, protected-worktree readback and content hashes are in
[handoff.json](artifacts/watch-workflow/handoff.json) and
[provenance.json](artifacts/watch-workflow/provenance.json).

## Connected proof, with explicit boundaries

[The new application workflow](../../tests/monitoring/watch_workflow.py) follows
one persisted five-case feed through discovery, preferences, exact tracking,
cost evidence, observations, notifications, failures, corrections and restart.
It calls the real application API and `execute_discovery`, using the existing
qualification/cost/coupon/history/assessment/admission/notification owners. All
application imports occur inside `MonitoringHarness` in fresh children. SQLite is
under a marked `/tmp/pricerecon-offline-*` directory; socket/native curl/browser/
subprocess/unmarked database guards remain active. Captured send functions retain
normal dispatcher and delivery-log behavior. No new production arithmetic,
scheduler, notification service or source registry was introduced.

The named positive fixtures intentionally invent dimensions, merchant assertions,
prices, FX and dates. For example their common synthetic VH31 identity is a test
input, **not a claim about the actual San Martin or Casio movement**. CEX/Scan in
this fixture identify controlled acquisition edges, not sellers proven to stock
these watches. The £1 lead is deliberately unusable as a delivered price. Original
illustrations are labelled as illustrations, not product photos.

[expected.json](artifacts/watch-workflow/expected.json) contains independently
specified outcomes; [observed.json](artifacts/watch-workflow/observed.json) contains
API observations, gate states, exact IDs/revisions, policy values and checkpoints.
The readable projection omits repeated field-evidence bodies and keeps the latest assessment per checkpoint, with retained counts. Its byte-complete
source is [raw-api.json.gz](artifacts/watch-workflow/raw-api.json.gz), ordinary gzip
JSON with the same checkpoint keys. Fixture code and retained artifact hashes
provide provenance; no fixture is reclassified as real market evidence.

| Named case | Connected deterministic result | Real-offer gate |
| --- | --- | --- |
| Militado ML05/ML05B | Lead visible independent of saved Watches; configuration unresolved, unknown dimensions/total, no alert. No manufactured report fills the gap. | **Blocked:** store/manufacturer, selection and UK offer evidence missing. |
| Addiesdive AD2066 mint | £70.10 base includes quoted VAT once; separate conditional cashback never changes payable. £58.10 crossing, same-price suppression, £56.10 further drop. A distinct synthetic receipt yields £45.10 while base stays £50.10. Scoped current-best/dated-low are separate from unavailable usual/personal price and null savings. Correction to salmon withdraws dependent price/coupon/history/assessment/alert eligibility and retains target £60. | **Unproven:** actual exact variation, fresh UK checkout, live coupon and retained history. |
| San Martin SN0144 | Mint configuration versus Space Gray selected dial rejects binding. Fresh compatible selection with missing shipping has unknown total; subsequent assumed regional shipping is conditional, not verified alert evidence. | **Unproven:** independent retailer lead is not manufacturer authority or complete UK delivery proof. |
| Merkur Lightning salmon | Visible unresolved lead, unknown total, no inferred identity/currency/availability and no verified alert. No easier product substituted. | **Blocked:** exact reconciled reference/configuration and offer evidence absent. |
| Casio MTP-B145D-2A2VEF | Missing shipping remains unknown; USD shipping without payment FX remains unknown. A synthetic evidenced 0.8 GBP/USD shipping conversion gives £49.68. Casio's separate £40 target/configuration/intended-values survive the Addiesdive correction. | **Unproven:** actual suffix/variation, buyability and complete current UK cost. |

All five abstain from claims of real qualification. “Passed” above refers to
expected deterministic handling, including deliberate abstention.

The Addiesdive history checkpoint retains initial/unchanged/increased/decreased/
unchanged/decreased captures (£70.10/70.10/80.10/58.10/58.10/56.10), plus explicit
cached, failed and capped outcomes. Synthetic observations have
`market_history_eligible=false`. Recapture does not rewrite the first observation;
correction retains its original configuration and marks dependent use invalid.
Intervals remain unobserved. Sparse synthetic dates never establish an ordinary
price, continuous availability, real longitudinal history or a savings percentage.

A successful recovery of the same price after the simulated source failure sends
nothing. The synthetic receipt later produces a third captured send at **base
£50.10**, because this target policy permits **public_no_coupon only**. The £45.10
coupon comparison does not silently opt the target into coupons. The retained08
coupon-crossing workflows separately prove explicit opt-in through the same owner.

The connected run exhausts its original durable **12-request** grant; changing a
policy label is not a recovery mechanism. On a fresh child process, the same
12 requests remain used, no acquisition transport/search or notification runs,
events remain identical, and correction withholding persists. This new restart
case proves withholding under correction/exhaustion; qualified restart dedup and
recovery spacing are additionally covered by the retained cases below.

## Retained gates reused, not substituted for the connected story

These receipts describe earlier exact fixtures and scopes. The final full suite
reruns their assertions unchanged alongside the connected story. No slice receipt
alone is presented as complete workflow proof.

| Gate | Exact retained evidence and scope |
| --- | --- |
| Identity traps | [Qualification receipt](watch-qualification.md), `tests/monitoring/qualification_workflows.py`: movement/dial/size/generation/strap/accessory/selected-SKU conflicts, unresolved fields, copied issuer lineage. |
| UK liabilities, basket and FX boundaries | [Cost receipt](watch-costs.md), `cost_workflows.py`: unknown component/currency/destination, included VAT, import liabilities, basket/quantity, payment versus customs FX, quantum equivalence. These are synthetic arithmetic/evidence contracts, not current tax advice. |
| Coupon opportunity/eligibility/receipt | [Coupon receipt](watch-coupons.md), `coupon_workflows.py`: no-coupon base; advertised opportunity, eligibility/expiry/minimum spend/stack conflicts; checkout receipt role independent of terms/eligibility; changed shipping and receipt invalidation. Live success stays unproven. |
| Cohorts and claims | [Assessment receipt](watch-assessments.md), `assessment_workflows.py`: new/used, auction/buy-now, quantity/basket and destination stay distinct; personal/payment/cashback do not enter public comparison; sparse scope, contradictions, history/coupon opt-in and expiry. Photos establish neither authenticity nor mechanical health. |
| Correction ownership/overlap | [Correction receipt](watch-corrections.md), correction and target-ownership modules: append/invalidation transaction, pending acquisition/send guards, sibling controls, descendant/reverse-order revisions and fresh-process independent intent. |
| Targets/delivery restart | [Tracking receipt](watch-tracking.md), `tracking_workflows.py`: crossing/further drop/rise-recross, same-price and route dedup, qualified fresh-process restart, channel acknowledgements, ambiguous interrupted send. Exactly-once external delivery remains unproven. |
| Legacy scheduling/settings/partial failure | [Monitoring receipt](monitoring-ui-verification.md), `workflows.py`: old schema migration, raw queries/groups/exclusions/price targets/notifications, enabled/disabled jobs, automatic startup, schedule window, overlap, last-good preservation and recovery. |
| Durable admission/recovery | [Collection receipt](watch-collection.md), collection/shared-grant/completion controls: API/scheduler/process overlap share caps, actual transport attempts/retries/details/fallbacks debit, reserved tracking capacity, interrupted restart resumes once with spacing, no refill/catch-up burst, exhausted/zero/expired grants retain successful timestamps. |
| Adapter/source coverage | [Source evidence receipt](watch-source-evidence.md), all 18 source workflows including parent's three retailer controls: AliExpress unbound Space Gray/missing selected-SKU stock with discovered2/inspected1/page1; eBay auction/used/missing currency and next-page gaps; Shopify typed parsing preserves valid201/202 siblings with invalid203 excluded and actual request/page bounds. These are adapter fixture proofs, not source entitlements. |

Six required source families and all 16 dated source lanes remain visible in the
actual feed. The browser fixture exercises one controlled source and leaves real
lanes not attempted. Dated adapter receipts preserve actual fixture page/detail
caps and history-rights gaps. Checked qualified coverage never means complete
market coverage; best/low claims remain cohort-, date- and scope-bound.

## Isolated migration, rollback and recovery

[recovery.json](artifacts/watch-workflow/recovery.json) records a marked temporary
old-schema database with one enabled and one disabled saved Watch. The real
lifespan performs additive migration; APIs and scheduler retain rules/settings.
After closing every connection and confirming no WAL file exists, the proof
copies database bytes. Restoring the pre-migration copy and starting again
repeats migration, preserves old Watch intent and has no discovery candidates.
Restoring the closed post-migration copy restores all five candidates and the
same legacy intent. No production database or other checkout was used.

This demonstrates recovery expectations before any later migration approval.
It does **not** qualify online backup, a production WAL/SHM copy, deployment
rollback or permission to migrate. Later approval must define quiescence, actual
source retention/deletion/backup rights, a tested backup/restore process and
physical database/WAL/log limits. Copying a running SQLite file is not this proof.

## Commands and results

All backend workflow commands use this exact prefix from this worktree:

```sh
env -i PATH=/Users/jay/.nvm/versions/node/v24.14.1/bin:/usr/bin:/bin \
  PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PWD/src:$PWD" \
  /Users/jay/.t3/worktrees/pricerecon/t3-7260bb2e/.venv/bin/python
```

Append `-m pytest -q` and these **14 modules only**:

```text
tests/test_collection_workflow.py tests/test_monitoring_workflow.py
tests/test_discovery_workflow.py tests/test_qualification_workflow.py
tests/test_cost_workflow.py tests/test_history_workflow.py
tests/test_coupon_workflow.py tests/test_tracking_workflow.py
tests/test_correction_workflow.py tests/test_correction_target_ownership.py
tests/test_shared_grant_workflow.py tests/test_assessment_workflow.py
tests/test_source_evidence_workflow.py tests/test_watch_workflow.py
```

| Check | Outcome / retained artifact |
| --- | --- |
| Full guarded workflows | **191 passed**, no skip/xfail; `full-workflows-final.log` (189 retained +2 new). |
| Limiter/browser contracts | **37 passed**, ten inherited warnings; `contracts.log`. Same prefix, `-m pytest -q tests/test_rate_limiter.py tests/test_external_browser.py`. |
| Frontend tests | **25 passed**; `frontend-tests.log`. Cleared Node PATH, `npm --prefix frontend test -- --run`. |
| Frontend production build | **Passed before fixture/app imports**, `build.log`. Existing integration node_modules symlink, no installs. Existing large-chunk warning retained. |
| Focused uncached types | **17 application files passed**, `mypy-uncached.log`; exact argv in `checks.json`. No incremental cache relied upon. |
| Changed-file Ruff baseline | **Zero added findings**, `ruff-comparison.json`; no ignores/suppressions/skips or weakened old assertions. |
| Browser/keyboard/UI | **Passed**, `browser/receipt.json`; actual installed Chrome, unique owned agent-browser session, guarded loopback only. |
| ESLint | **Blocked**, unchanged missing `eslint.config.*`; `eslint.log`. No workaround or dependency install. |
| Source/document whitespace | `diff-source-doc.log`; raw retained log whitespace is separate in `diff-raw-logs.log`, not normalized or called globally green. |

`red-missing-workflow.log` records two failures before the new workflow existed.
`first-` through `ninth-connected.log` retain fixture construction errors (wrong
policy helper argument, frozen cap mutation, typoed FX class, stale API revisions,
query-bound history, serialization expectations). `tenth-connected.log` is the
first two-test green. These are verification-harness errors, **not product defects
repaired or evidence of a weakened gate**. The first policy-switch attempt was
correctly refused. The final test uses a bounded original policy and fresh API
revisions. Earlier browser logs similarly retain a missing baseline, inconsistent
multi-route fixture revisions and an empty required rationale; the final driver
uses one controlled source and valid form submissions. Cross-route assertions in
the retained suite remain intact. No production repair was necessary for 12.

Regenerate machine receipts with the backend prefix followed by:

```sh
-m tests.monitoring.watch_workflow_receipts \
  --artifacts "$PWD/docs/testing/artifacts/watch-workflow"
```

This runner creates/removes its own marked temporary directories and records
commands, policies, complete API evidence and source/build hashes. It does not
launch a browser or acquire live data. The 60-second child timeout and fixture
resource values are test values, not proposed operational commitments.

## Buyer walkthrough package — parent must obtain feedback

[Buyer guide and exact launch/control commands](watch-workflow-buyer-guide.md)
provide the runnable synthetic fixture, tasks, screenshots and a feedback template.
The browser receipt is automated verification, **not buyer feedback**. The planning
prototype's approval remains a separate historical planning decision.

The actual implemented UI was checked at 1280×900 and 375×812: five-case feed,
expandable costs/claims/assessments and 16-route source coverage; keyboard preference
and target edits; field/value correction at both widths; target/correction reload;
stale-write error, recovery and no horizontal overflow or page exceptions.
All 19 screenshots were opened and inspected. Complete final browser feed JSON is retained in `browser/feed.json.gz`; the post-run driver change only compresses receipt storage, with its tested hash in `browser/provenance.json`. The dense evidence panels require scrolling;
this is a reviewable product behavior for the buyer to judge, not an accepted
accessibility or usability audit. Owned fixture/browser processes were closed.

## Live prerequisites remain unsettled

[live-prerequisites.json](artifacts/watch-workflow/live-prerequisites.json) lists
all 16 actual source lanes with separate unresolved access, capture, display/
derivation, retention, deletion, backup, history, freshness and ownership fields.
Each remains unset, including reviewed lead lanes. It reuses the existing source
projection rather than defining another capability registry.

Before a separately authorized live study/activation, the parent must obtain
actual source-specific authority and choose finite numerical provider/request/
page/detail/retry/fallback limits; browser concurrency/time; AI calls/tokens/spend;
logical storage and **physical database, WAL and log** limits; study duration,
spend and operator-minute ceilings; retention/deletion/backup treatment; semantic
freshness/recheck schedules; and named maintenance plus stop/resume owners.
All such live choices are null/unproven here. No synthetic value is a default,
commitment, entitlement or measured sustainable cadence. Militado/Merkur evidence,
real history/baseline calibration, live coupon/delivery, buyer feedback, migration
approval and activation remain separate gates. PC/pens and personal benefit
execution remain later scope.

## Sole merger technical acceptance — 2026-10-27

**Technical proof accepted for the offline slice; ticket12 stays open pending
actual buyer feedback and the parent's final Standards and Spec review.** This
was the bounded merger verification, not that final two-axis review. No buyer was
contacted and neither actual-feedback checkbox was ticked.

Integration `/Users/jay/.t3/worktrees/pricerecon/watch-category-integration`, branch
`integration/watch-category-discovery`, was clean at
`9ce8d31236192a8e6b98152a835ff68b4dd03bda`. Source
`/Users/jay/.t3/worktrees/pricerecon/t3-dbe22e28`, branch
`t3/watch-workflow-verification`, was clean at
`5dc96638a298635fafb3c07dfaf9a88e87331459`, containing that integration. Integration
had not moved, so no source refresh was needed. Exact identity checks used
`git branch --show-current`, `git status --porcelain`, `git rev-parse HEAD` in
both checkouts and `git merge-base --is-ancestor HEAD 5dc96638a298635fafb3c07dfaf9a88e87331459`
in integration. All exited zero with the stated clean identities.

Executed in integration:

```sh
git merge --no-ff 5dc96638a298635fafb3c07dfaf9a88e87331459 \
  -m "Merge ticket 12 connected offline watch verification"
```

Conflict-free merge **`931b468b9e15603c2462d8ce5f6f0f2ae67e7725`** has parents
`9ce8d31236192a8e6b98152a835ff68b4dd03bda` and
`5dc96638a298635fafb3c07dfaf9a88e87331459`. Full source history is retained; no
squash, rebase, reset, cherry-pick or checkout creation occurred. The merged tree
initially matched source exactly. The only subsequent changes are this receipt,
tracker disposition and merger verification artifacts. Production application,
frontend and existing workflow assertions remain unchanged.

### Independent results and evidence

All commands ran from integration, with existing dependencies and the original
parent interpreter. Build ran first and finished before any application/fixture
import. The exact backend environment prefix is:

```sh
env -i PATH=/Users/jay/.nvm/versions/node/v24.14.1/bin:/usr/bin:/bin \
  PYTHONDONTWRITEBYTECODE=1 \
  PYTHONPATH=/Users/jay/.t3/worktrees/pricerecon/watch-category-integration/src:/Users/jay/.t3/worktrees/pricerecon/watch-category-integration \
  /Users/jay/.t3/worktrees/pricerecon/t3-7260bb2e/.venv/bin/python
```

The scoped guarded-workflow command appended `-m pytest -q` and exactly the 14
modules listed above, in that order. This is a scoped command, not the full
repository suite: no full-repository pytest or `tests/test_api.py` ran. Exact
command arrays/environment/results are also retained in
[merger/check-results.json](artifacts/watch-workflow/merger/check-results.json).

| Gate | Independently observed result |
| --- | --- |
| Frontend build first | `env -i PATH=/Users/jay/.nvm/versions/node/v24.14.1/bin:/usr/bin:/bin npm --prefix frontend run build`: exit 0; existing large-chunk warning retained in `merger/build.log`. |
| Guarded application workflows | **191 passed in 177.26s**, no skip/xfail, including all 189 retained and the two connected tests; `merger/full-workflows.log`. |
| Limiter/browser contracts | Same backend prefix plus `-m pytest -q tests/test_rate_limiter.py tests/test_external_browser.py`: **37 passed**, ten inherited warnings; `merger/contracts.log`. |
| Frontend tests | Same cleared PATH, `npm --prefix frontend run test -- --run`: **25 passed**; `merger/frontend-tests.log`. |
| Focused types | Backend prefix and exact `-m mypy --no-incremental` 17-file argv from source `checks.json`: **passed**, retained unused-config note; `merger/mypy.log`. |
| Ruff against 9ce8d31 | Backend interpreter plus `docs/testing/artifacts/watch-workflow/merger/audit_evidence.py`: zero baseline/current/added findings across changed Python and both merger scripts; `merger/ruff.json`. No suppressions or assertion weakening. |
| Evidence integrity | **6 final code hashes, 88 artifact hashes, 254 source/build hashes and 19 screenshot hashes match**; `merger/evidence-audit.json`. All 77 exact original manifest hashes and lengths match. |
| Source/document whitespace | `git diff --cached --check 9ce8d31 -- . ':(glob,exclude)**/*.log'`: passed. Raw log whitespace separately retained in `merger/diff-raw-logs.log`; no globally clean whitespace claim. |
| ESLint | `npm --prefix frontend run lint` in the same cleared environment: exit 2, existing missing `eslint.config.*`; `merger/eslint.log`. **Blocked**, no workaround/install. |
| Retained desktop/narrow browser proof | Read actual driver/server/UI code, receipt and complete compressed feed; opened all 19 PNGs. Evidence reused with matching application/build/current-driver hashes; no new browser run. |
| Additional closed-copy check | Backend prefix plus `docs/testing/artifacts/watch-workflow/merger/recovery_copy_probe.py`: **passed**; `merger/recovery-copy-probe.json` and `.log`. |

The copied source receipts were checked against the actual assertions and public
API/execution behavior, not accepted as independent correctness proof. Fixed
expected literals (70.10/58.10/56.10, 50.10 base versus 45.10 synthetic receipt,
49.68 FX and 60/40 targets) are specified independently of production calculations.
The connected guarded suite verifies all five names: Militado/Merkur deliberately
abstain; the three positive cases retain explicitly fictional VH31 dimensions,
prices and dates. CEX/Scan are fixture edges; original illustrations stay labelled.
Editable preferences, unknown dimensions, selected-dial/missing/conditional/FX
costs and VAT-once, base/coupon separation, crossings/dedup/recovery, versioned
scoped claims, cached/failed/capped history, correction lineage/unrelated intent
and durable 12-request exhaustion across a fresh process are exercised at the
approved seam. No synthetic history becomes market-history eligible. The retained
source roster exposes six families/16 routes, unchecked/unqualified lanes and
rights/caps gaps; none establishes actual stockists or complete market coverage.

The inspected screenshots show readable preference/target/correction controls at
1280×900 and 375×812, amount/scenario distinctions, conditional cashback excluded
from payable, scoped current/dated-low versus unavailable usual/personal/savings,
staged source coverage, saved correction lineage, conflict guidance and resolved
reload. The driver asserts keyboard submission, persistence, 409 rejection/reload,
no horizontal overflow and no page exceptions. A screenshot alone cannot prove
keyboard interaction or absence of every browser error; those claims retain the
driver/receipt boundary. Dense panels scroll and require actual buyer judgement.

Browser provenance documents a storage-only post-run change from hash
`c26f5fa4a92056434b6c3a6a23afa843ef28a9c0f4d2e6883c98131ba7947240` to current
`0d867837b886fca65ca9052be71c37c4c70fb3977b70b38ed7b8c8751e9d504e`.
Current bytes and all retained artifacts match; prior driver bytes are not
retained for an independent historical diff. The storage-only explanation is
documented provenance, not a newly reproduced browser run. An attempted hash
reconstruction was an overconstraint in the merger audit, failed and was removed;
`merger/audit-first.log` is retained. This did not change application tests or
assertions. No UI changed and no substantive UI evidence gap required a new run.

### Bounded recovery boundary check

The source recovery receipt did not independently record connection closure for
each copy, so one additional check instrumented only SQLite connection closure
and `shutil.copy2`. It invoked the retained recovery workflow in a fresh guarded
process with marked temporary storage. At all four copies every opened connection
was closed, neither source nor destination had a WAL, and source/destination
SHA256 and lengths matched. Independently specified public API assertions retain
enabled 7/disabled 8, raw queries, groups, exclusions, schedules, notifications and
target. Seed/feed counts are 5/5, pre-migration restore 0, post-migration restore 5.
The source's schedule check remains active. Temporary storage was removed.

The first probe expected only one initial feed read, while `seed()` and its caller
each read it. That bookkeeping failure is retained in
`merger/recovery-copy-probe-first.log`; corrected expected call counts pass.
All copy-boundary and API-content assertions passed in both attempts. No product
defect, reproducer requiring a product fix or assertion weakening was found.
This proves closed temporary byte-copy roundtrips only. It does not certify a
running database/WAL backup, deployment rollback or migration permission.

Raw merger logs and probe/source hashes are retained in
[merger/raw-sha256.json](artifacts/watch-workflow/merger/raw-sha256.json). The
original preservation authority is
`/Users/jay/.scratch/watch-category-discovery-implementation/initial-worktree-manifest.json`,
SHA256 `93ada3e762355f117518d20a6dd2d0ad6f80e01cb2d49bea8ddff073e390c6b9`.
The final local receipt commit follows the merge; resolve it with
`git rev-parse integration/watch-category-discovery`. Source remains at the exact
supplied SHA and clean. Both source and merge are ancestors of the final receipt
commit. All 77 original hashes/lengths were checked again at handback. No application
ran in the original checkout.

### Parent continuation and unresolved gates

The [buyer guide](watch-workflow-buyer-guide.md) is runnable from integration after
this merge: use the integration path instead of its example source `cd`, finish
the documented cleared-environment build, then use the backend prefix above with
`-m tests.monitoring.discovery_ui_server --workflow --port 8892`. No package,
browser, credentials or accounts need installing. Await `OFFLINE_UI_READY`, open
`http://127.0.0.1:8892/discover`, and verify `/api/offline-verification` reports
`ticket12-connected-ui-v1`, temporary storage, automatic checks false, no blocked
edges and zero initial sends. Stop on an occupied port or different marker.
Create the target before the parent's `baseline`; then `cross`, `duplicate`,
`drop`, `costs`, `coupon`, correction and `stale` as directed. The helper is
`-m tests.monitoring.watch_workflow_ui --port 8892 --step STEP` using the same
backend prefix. It verifies per-run identity. Reload after each step, avoid
merchant links, and Ctrl-C the fixture afterwards. This merger left no owned
fixture/browser running.

Actual buyer task feedback and parent's final Standards and Spec review/fixes,
closure and cleanup remain outstanding. Real Militado/Merkur evidence is blocked;
live offers/coupons/delivery, retained history/calibration, source-specific rights,
retention/deletion/backup, numerical operating/physical DB/WAL/log/study/spend/
operator limits, freshness, named owners, migration approval and activation are
unproven. Existing ESLint configuration remains blocked. No release/global-best/
complete-coverage claim follows. Collection stays staged. No push/PR, live/network
acquisition, account/production operation, install, activation, purchase or
unrelated cleanup occurred; the original 77 dirty files and source are preserved.

## Parent final review and repairs — 2026-10-27

The final independent Standards and Spec reviews found four concrete defects;
parent repaired all four. [Separate review reports and remediation proof](watch-final-review.md)
record two Standards P2 findings and Spec P1/P2 findings without cross-axis reranking.
The scoped fourteen-module command now passes **215 guarded workflows** (191
retained plus 24 new), 37 contracts and seven original reviewer script runs.
Uncached five-file types and focused zero-finding Ruff pass. Frontend 25-test/build
and 19-screenshot evidence is reused because UI/schema did not change. Original
77 dirty files remain unchanged.

That reuse claim was scoped to #142 and no longer holds for #149: this change
adds fields to the assessment API schema (envelope `PriceClaim.synthetic`,
`ObservationHistory.market_history_eligible_count`) and changes the frontend
that renders them, so the frontend suite and production build were re-run on
the #149 tree (**88 vitest tests passed, clean build**); the 19-screenshot
evidence predates the #149 rendering change.

## Full repository suite vs the scoped 215 figure

The 215-pass figures above come from the **scoped fourteen-module
guarded-workflow command**; they are not full-suite counts.

Full-suite figures recorded earlier in this file — "854 collected: 828
passed, 15 failed, 11 skipped" at reviewed head `42e7f984`, repeated as the
#149 baseline — **do not reproduce**. Neither the #149 review environment
nor the fix-run environment below produced the 15-failure/11-skip split on
any interpreter; in both re-measures the only failure mode was the missing
frontend build (10 failures of the `pilot_frontend_build_required` family,
0 once `frontend/dist` exists). Treat the earlier figures as records of the
machine that wrote them, not reproducible facts.

Measured on the #149 fix tree (PR branch merged with `origin/main` at
`fbf2d6e`, frontend built from the tree under test, macOS, sequential runs
of `PYTHONPATH=src python -m pytest -q --disable-warnings` from the repo
root):

| Tree | Interpreter | TMPDIR | collected | passed | failed | skipped |
|---|---|---|---|---|---|---|
| #149 fix tree | Py3.14.7 | native (`/var/folders/…`) | 885 | 875 | 0 | 10 |
| #149 fix tree | Py3.14.7 | `/tmp` | 885 | 875 | 0 | 10 |
| #149 fix tree | Py3.13.18 | native | 885 | 875 | 0 | 10 |
| #149 fix tree | Py3.13.18 | `/tmp` | 885 | 875 | 0 | 10 |
| `origin/main` @ `fbf2d6e` | Py3.14.7 | native | 865 | 855 | 0 | 10 |
| `origin/main` @ `fbf2d6e` | Py3.13.18 | native | 865 | 855 | 0 | 10 |

The branch adds 20 collected tests over its base (12 from the original #149
work plus 8 review-fix tests) and changes no outcome: every test that passes
on the base passes on the branch. The three TMPDIR-sensitive workflow
modules also pass with `TMPDIR` unset.

Preconditions for reproducing a full-suite run:

- **Build the frontend from the tree under test** (`npm ci --prefix frontend`
  and `npm run build --prefix frontend`); the pilot UI tests serve
  `frontend/dist` and fail with `pilot_frontend_build_required` when it is
  absent. That single missing precondition accounts for every failure
  observed in either re-measure.
- **The macOS-only private-temp gate**: pilot activation asserts the macOS
  `/var/folders` private temp directory (`macos_private_tmp_required`,
  `src/pricerecon/pilot.py`). Runs above were macOS; non-macOS hosts are
  expected to fail that assertion by design.
- **Run against a clean environment for the checkout under test**
  (`PYTHONPATH=src` from the repo root, or a fresh editable install of it).
  A stale install can register connector entry points from a different tree;
  the environment used here registers 36 `pricerecon.connectors` entry
  points, none named `aria`, and no entry-point failure occurred — the
  earlier "aria" failure record is an artifact of that machine's install,
  not a property of this tree.
- **Quality-tool provenance**: the CI workflow force-installs
  `ruff==0.15.21` and `black==26.5.1` (`.github/workflows/ci.yml`), and
  those pins formatted and linted this tree (`black --check` and
  `ruff check` clean over `src/pricerecon tests`; `mypy` clean in both
  interpreters above). The `pyproject.toml` dev-dependency list separately
  carries `black==26.10.1`; cite the enforcing CI pin, not the dev list,
  when stating formatting provenance.

The buyer guide now targets the retained integration checkout for use after
implementation-worktree cleanup. Actual buyer feedback remains pending; no
response has been inferred from the running fixture, tests or elapsed time.
Ticket12 stays open for that gate. Collection remains staged and all separately
unproven live/rights/calibration/operating/activation prerequisites remain explicit.
