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
