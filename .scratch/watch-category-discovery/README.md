# Watch category discovery implementation

Spec: [Trustworthy UK watch discovery](../../docs/specs/watch-category-discovery.md).

Integration branch: `integration/watch-category-discovery`. Base: `ef86af6d41fbb3cac8982f43997068e906477025`.

This is the implementation tracker. The planning decisions under `docs/product/category-discovery/tickets/` remain their own closed investigation graph. Named **Blocked by** links in these implementation issues define the frontier. Claim ready issues before starting; close them only with dated evidence against their checklists. Record partial, blocked and unproven acceptance explicitly.

| Ticket | Requires | State |
| --- | --- | --- |
| [01: Existing monitoring](issues/01-verify-existing-monitoring.md) | None | Closed |
| [02: Candidate discovery](issues/02-discover-candidates.md) | 01 | Closed |
| [03: Qualification](issues/03-explain-offer-qualification.md) | 02 | Closed |
| [04: UK delivered cost](issues/04-show-uk-delivered-cost.md) | 03 | Closed |
| [05: Exact tracking](issues/05-track-exact-products.md) | 04 | Closed |
| [06: Observation history](issues/06-show-observation-history.md) | 04 | Closed |
| [07: Corrections](issues/07-correct-identities.md) | 05, 06 | Closed |
| [08: Comparisons](issues/08-compare-qualified-offers.md) | 07 | Closed |
| [09: Public coupons](issues/09-evaluate-public-coupons.md) | 04 | Closed |
| [10: Shared limits](issues/10-prioritise-tracking.md) | 05 | Closed |
| [11: Source evidence](issues/11-carry-source-evidence.md) | 03, 10 | In progress |
| [12: Integrated verification](issues/12-verify-complete-watch-workflow.md) | 08, 09, 11 | Blocked |

## Authority and acceptance

Work is limited to source implementation and deterministic offline verification with isolated storage and controlled external edges. The buyer explicitly authorised local commits/merges for this continuation, overriding the older issue-level prohibition. No live collection, accounts, production database, activation, deployment, purchases, pushes or PRs are authorised.

Ticket 01 source was integrated on 2026-10-27 in merge `a0e5c1a612252c61a62eabc7b56ebc3b3297ed85`, preserving implementer HEAD `9312871f269137d7b98ba7155d9523350e41e62e`. The subsequent rendered-form preservation repair was integrated in merge `3243c8f00e3f9dd9efde79327b6905eb3d4354b2`, preserving implementer HEAD `534cecaece62e30f50c680b40af5b4c7f561b6e4`. Integration checks passed **15 isolated workflow tests**, **25 frontend tests** and the frontend build. The parent subsequently passed the rendered edit/save/reload/manual-check regression. See the dated resolution log below and the [repair integration receipt](issues/01-verify-existing-monitoring.md#preservation-repair-integration-receipt-2026-10-27).

Current frontier, 2026-10-27: tickets 01–10 are closed for their offline scope.
Ticket08's integrated behavior passed the 171-case suite and three independent
coupon probes; its contained type repair now passes uncached eight-file mypy and
23 assessment/tracking workflows. 11 retains its existing isolated implementation
claim. 12 remains blocked on 11.
Earlier dated entries describe their historical state.

Actual buyer walkthrough feedback, current source rights, live offer/history/cost proof, finite operating limits and named maintenance ownership cannot be fabricated by passing fixture tests. Keep these gates explicit in the final receipt.

## Resolution log

- 2026-10-27: 01 closed with 15 isolated application workflows, 25 frontend tests,
  successful build and [rendered browser preservation proof](../../docs/testing/monitoring-ui-verification.md).
  02 was claimed; the other blockers remain authoritative.
- 2026-10-27: 02 closed after conflict-free history-preserving merge
  `970bd255ab9f1caead2ed735be0f4ebe9e9ca4e6` of implementer `2b8325c` onto
  `15beae4`. The merger passed 20 isolated workflows (including all 15 legacy),
  25 frontend tests, build, focused Ruff/mypy and inspected retained desktop/narrow
  browser proof. See the [dated integration receipt](../../docs/testing/watch-discovery.md#merger-verification-2026-10-27).
  Existing ESLint configuration blockage and seven unchanged app/schema Ruff
  findings remain recorded. 03 claimed for the parent continuation; no 03
  implementation occurred. Collection remains staged and buyer/live acceptance
  remains open.
- 2026-10-27: 03 implementation `2b5a167` integrated without conflicts in
  history-preserving merge `b520fb8`. The merger passed 29 isolated workflows
  (including all 15 legacy), 25 frontend tests, build and focused Ruff/mypy, and
  inspected retained browser screenshots/receipt. Additional isolated API checks
  found false currency/context support and collapsed unresolved configuration
  subjects. **03 remains open; 04 remains blocked and unclaimed.** See the
  [merger findings and verification](../../docs/testing/watch-qualification.md#merger-verification-2026-10-27).
  No ticket04 implementation or source repair occurred; live/buyer gates remain open.

- 2026-10-27: 03 repair `dad3273` integrated without conflicts in history-preserving
  merge `bf0d3f9`, with parents `95f675e` and `dad3273`. Both original failures were
  independently reproduced before merging. The merged tree passed 34 isolated
  workflows (all 29 prior), focused Ruff, mypy on 12 files and diff checks.
  Fresh-process and reordered recapture retain separate definition/keyless
  subjects, multiple offers, stable IDs and evidence/revision lineage; an extra
  isolated check confirms historical rows unchanged and no foreign-key errors.
  Frontend 25-test/build results were retained from the source receipt and earlier
  browser proof inspected; no new frontend/browser run was needed. **03 closed
  for offline implementation; 04 claimed in progress for the parent continuation.**
  See the [repair merger receipt](../../docs/testing/watch-qualification.md#repair-merger-verification-2026-10-27).
  No 04 implementation occurred. Collection remains staged, totals unknown and
  source/live/buyer/retention/freshness/operating gates open.

- 2026-10-27: 04 source `af2ab0f` integrated without conflicts in history-preserving
  merge `ed1404b`, with parents `9c93d9f` and `af2ab0f`. The merger passed all
  46 documented isolated workflows, 25 frontend tests, build and focused
  Ruff/mypy; retained desktop/narrow browser artifacts were inspected.
  An additional isolated application probe found equivalent FX rounding quanta
  producing different persisted/public verified totals and different budget fit.
  **04 remains open for repair; 05/06/09 remain blocked and unclaimed.**
  See the [merger receipt and exact reproducer](../../docs/testing/watch-costs.md#merger-verification-2026-10-27).
  No later ticket implementation or source repair occurred. Fixture success
  establishes no legal/live/freshness/comparison/alert or activation acceptance.

- 2026-10-27: 04 FX repair `aa18c74` integrated without conflicts in
  history-preserving merge `8b6481d`, with parents `24a6943` and `aa18c74`.
  The original probe independently failed before merge and passed afterwards;
  equal numeric quanta now preserve persisted/public totals and budget fit.
  All **48 isolated workflows** (all 46 baseline plus two new regressions),
  focused Ruff, 14-source mypy and diff checks passed. Unchanged frontend's prior
  25 tests/build and retained browser proof were accepted; existing ESLint
  missing-config blocker remains recorded. **04 closed for offline scope;
  05/06/09 READY and unclaimed for parent dispatch.** No later ticket work was
  performed. See the [repair merger receipt](../../docs/testing/watch-costs.md#fx-repair-merger-acceptance-2026-10-27).
  Source/live/legal/retention/freshness/comparison/alert/buyer and activation
  gates remain separate; collection stays staged and original dirty parent is
  preserved.

- 2026-10-27: 06 source `e47d47a` integrated without conflicts in
  history-preserving merge `bd5a3fb`, with parents `375a4a4` and `e47d47a`.
  All **55 isolated workflows** passed, including all **48 baseline**, with
  focused Ruff and eight-source mypy. Unchanged merged frontend/browser code
  matched the source receipt; its 25 frontend tests/build were retained and
  actual desktop/narrow browser artifacts inspected. An extra guarded API probe
  reproduced a derived re-extraction being counted as a new supported observation
  despite naming the original capture in its lineage. **06 remains open for
  repair; 07 remains blocked by05/06.** Corrected07's stale ready status; no07
  work was claimed. **05/09 remain in progress and untouched.** See the
  [merger receipt and reproducer](../../docs/testing/watch-history.md#merger-verification--2026-10-27).
  No production repair or dependent implementation occurred. Collection stays
  staged; source/live/history/buyer/activation gates remain separate and open.

- 2026-10-27: 09 source `db08536` integrated without conflicts in
  history-preserving merge `2b4686b`, with parents `b97f37a` and `db08536`.
  All **65 isolated workflows** passed (48 baseline, seven history, ten coupon),
  plus 25 frontend tests, build and focused Ruff/mypy. Actual retained desktop/
  narrow browser proof was inspected. An additional guarded application probe
  found compatibility and eligibility evidence can each be reused as the whole
  application receipt provenance, exposing a reproduced GBP 45.10 payable with
  no checkout evidence. **09 remains open for repair; 12 remains blocked.**
  The no-coupon GBP 50.10 path is preserved; a changed-shipping control correctly
  reconciles GBP 47.20. See the [merger receipt and reproducer](../../docs/testing/watch-coupons.md#merger-verification--2026-10-27).
  Ticket06's separate lineage gap and active05/06 repair worktrees are untouched.
  Absent07 correction UI remains a later integration gate, including overlapping
  correction/acquisition. No production repair or later implementation occurred;
  collection stays staged, with live/buyer/activation gates open.

- 2026-10-27: Resumed interrupted 05 merger verification at clean merge
  `8facf4198d0f812f52cfb1dce055e5dd74d18e16`, preserving source
  `0cc5c47349b9e01e61188b116681f6dff4ac2ce6`. All 77 retained application
  cases passed (76 in the suite; one corrected-PATH rerun), as did six additional
  guarded per-channel withdrawal/expiry/failed-ack probes, focused Ruff,
  11-source mypy and the 43-file retained manifest comparison. Unchanged 25
  frontend tests/build and three browser-flow receipts were reused.
  **05 closed for offline scope; 10 READY and unclaimed.** See the
  [merger acceptance](../../docs/testing/watch-tracking.md#merger-acceptance-2026-10-27).
  No application-source repair, repeated merge, reset or later implementation
  occurred. **06/09 remain open with existing repair owners; 07 stays blocked
  on 06.** Collection remains staged; coupon-target integration and live/buyer/
  operating/activation gates remain separate and open.

- 2026-10-27: 06 repair source `238019d` integrated without conflicts in
  history-preserving merge `6b93262`, with parents `a69c4ee` and `238019d`.
  Implementation `a856c08` and interrupted receipt `39a0687` are retained.
  All **83 current isolated application workflows passed in one run** (77 prior
  plus six new lineage cases), as did the unchanged original merger probe,
  focused Ruff, four-source mypy and diff checks. Fresh temporal acquisition
  remains supported with reused definitions; derived/cached/unknown lineage
  cannot manufacture independence or refresh age, and original records survive.
  Fifteen unchanged frontend/browser/probe manifest entries match; prior 25
  frontend tests/build and browser receipts were reused. **06 closed for offline
  scope; 07 READY and unclaimed** because 05 is already closed. **09 remains open
  for receipt-provenance repair; 10 remains in progress.** Their active worktrees
  and the dirty original parent were untouched. The 09 acceptance probe was not
  run or treated as passing. See the [repair merger acceptance](../../docs/testing/watch-history.md#lineage-repair-merger-acceptance-2026-10-27).
  No application-source repair or dependent implementation occurred. Collection
  stays staged; source/live/history/calibration/buyer/operating/activation gates
  remain separate and open.

- 2026-10-27: 09 repair source `d2ab666` integrated without conflicts in
  history-preserving merge `5a3124e`, with parents `61ab075` and `d2ab666`.
  Both original unsupported substitutions independently failed before merge
  and withhold payable afterwards. All **85 combined isolated workflows passed
  in 72.80s**, as did the original probe, 23 receipt controls, focused Ruff/mypy
  and diff checks. Genuine GBP45.10, changed-shipping GBP47.20 and base GBP50.10
  remain; old stored role-less successes become historical only on restart and
  supersession. Prior unchanged frontend/build/browser evidence is reused.
  **09 closed for offline scope.** See the [repair merger acceptance](../../docs/testing/watch-coupons.md#receipt-provenance-repair-merger-acceptance--2026-10-27).
  Active07/10 worktrees and original dirty parent remain untouched. The 07
  correction append/invalidation transaction, UI and overlapping acquisition
  remain an explicit coupon integration gate until that slice lands. No later
  ticket was claimed or implemented; 12 remains blocked by its other gates.
  Collection stays staged; live coupon/source/rights/retention/freshness/buyer/
  operating/comparison/savings/activation acceptance remains unproven.

- 2026-10-27: 07 source `89ebd79` integrated without conflicts in history-preserving
  merge `233b3cc`, with parents `75f8a3a` and `89ebd79`. All **95 documented safe
  application workflows passed in 83.56s**, with focused Ruff/mypy and unchanged
  app/schema lint diagnostics. Inspected and reused the source's unchanged
  25 frontend tests/build and actual desktop/narrow correction proof. An extra
  guarded API/execution probe fails: correcting mint to salmon in a listing also
  containing blue prevents fresh salmon requalification and withdraws unrelated
  blue, persisting across restart. The single-configuration positive control
  passes. **07 remains open for repair; 08 remains blocked and unclaimed.**
  See the [merger disposition](../../docs/testing/watch-corrections.md#merger-disposition--2026-10-27).
  No application repair, later implementation or acceptance occurred. Source07,
  active10 and the dirty original parent were not edited. Collection stays staged;
  live/buyer/source-rights/freshness/operating/activation gates remain separate.


- 2026-10-27: 10 source `072a2f8` refreshed against `f561d76` in merge `fd02625`,
  preserving 07 publication/invalidation and 10 admission through four actual
  conflicts. Full refreshed history merged with `--no-ff` as `5cca859`, first
  parent `f561d76`. All **106 guarded application workflows**, **37 limiter/browser
  contracts**, focused Ruff/mypy, repeated **25 frontend tests**, build and actual
  collection/correction desktop/narrow UI checks pass. Three additional probes
  fail: independent API/scheduler contexts and a fresh process sharing the marked
  DB reach the controlled HTTP transport outside an exhausted active durable
  grant, with unchanged usage/attempts. No-grant legacy and redirect controls pass.
  **10 remains open for shared-admission repair; 11 remains blocked/unclaimed.**
  See the [dated merger disposition and reproducer](../../docs/testing/watch-collection.md#merger-disposition--2026-10-27).
  The 07 multi-configuration repair remains separate and untouched; no 11 work
  or production acceptance occurred. Browser/AI and physical disk/log/backup/
  retention prerequisites remain explicit; collection stays staged.

- 2026-10-27: 07 scope repair `430f4f0` merged without conflicts with `--no-ff`
  as `7fcc3ea`, first parent `f8ff7e5`; source/merged trees matched exactly.
  All **123 guarded workflows passed in 117.72s**; original multi/single probes,
  focused Ruff/mypy and an additional valid-sibling captured-crossing control
  pass. Unchanged frontend/build/browser proof is reused. A new guarded probe
  fails: after mint→blue and blue→red journals both requalify, recorrecting the
  first to gold rewrites both targets' intended dials to gold, surviving restart
  while the second journal remains red. **07 stays open; 08 stays blocked and
  unclaimed.** See the [scope repair merger review](../../docs/testing/watch-corrections.md#scope-repair-merger-review--2026-10-27).
  No application repair or 08 work occurred. Ticket10's context-bypass probes
  remain open for its owner, were not rerun and are not included as passed in
  the 123 suite. Source repair, active10 and original dirty parent were untouched.
  Collection stays staged; buyer/live/source/freshness/operating/activation gates
  remain separate and open.

- 2026-10-27:07 closed after the parent target-ownership repair and126 guarded
  workflows;08 claimed. See the [dated acceptance](issues/07-correct-identities.md#final-offline-acceptance--2026-10-27).
  10 remains open pending independent acceptance of its retained grant repair.

- 2026-10-27: 10 grant repair `2ac8eff` refreshed with `c84f1f1` as `f61bc3c`
  and merged without conflicts using `--no-ff` as `906ef0f`. The parent's 07
  source, three tests and receipts remain unchanged; 08's active worktree is
  untouched. All 148 guarded workflows, 37 contracts, focused types/lint and the
  original API/scheduler/fresh-process plus no-grant/redirect probes pass.
  Unchanged frontend/build/UI evidence is reused. Three additional acceptance
  cases fail: request exhaustion and zero-first elapsed/provider grants return
  completed/success and advance `last_check_at` despite no new send; rows and
  collection last-good evidence remain retained. Expired-policy control passes.
  **10 stays open; 11 stays blocked/unclaimed; 08 stays in progress.** See the
  [repair merger receipt](../../docs/testing/watch-collection.md#shared-grant-repair-merger-review--2026-10-27).
  No application repair, later-ticket implementation, live operation, activation,
  push or production acceptance occurred. Collection stays staged.

- 2026-10-27: Parent fixed the contained 10 denied Watch completion/timestamp
  finding on integration. **160 guarded workflows**, **37 contracts**, eight exact
  API/scheduler probes, focused types and zero-added-finding lint checks pass.
  **10 closed offline; 11 claimed for isolated implementation.** 08 remains active;
  12 remains blocked. Existing frontend/browser proof is reused and all 77 dirty
  parent files remain unchanged. See the [repair receipt](../../docs/testing/watch-collection.md#denied-watch-completion-repair-and-offline-acceptance--2026-10-27).
  Collection stays staged; live/source/physical-resource/operating/buyer gates
  remain separate.

- 2026-10-27: Sole ticket08 merger integrated the complete source history
  `81f18ab18d3417f17945ca46ec437e628689a892` without conflicts with `--no-ff`
  in `20728c299d2b8a8d217e80dd0dcd5fef6fa79ea1`. **171 guarded workflows**, **37
  contracts**, **25 frontend tests**, build and three independent coupon recovery/
  expiry probes pass. Ruff adds no findings; supplied evidence and the original
  77-file manifest match. Focused mypy independently fails on the new
  `TrackingPolicy.allowed_scenario_kinds` default factory. **08 remains open for
  the parent's small source repair; 11 continues with its existing owner; 12
  remains blocked.** No product source repair or later ticket work occurred.
  See the [review receipt](../../docs/testing/watch-assessments.md#sole-merger-review--2026-10-27).

- 2026-10-27: Parent fixed 08's sole merger type finding with an explicitly typed
  fresh no-coupon default factory. Uncached eight-file mypy and 23 focused
  workflows pass; 171-workflow/37-contract/frontend/build/browser merger proof is
  reused. All 77 original dirty-parent files remain unchanged. **08 closed offline;
  11 remains active; 12 blocked on 11.** See the [acceptance receipt](../../docs/testing/watch-assessments.md#parent-type-repair-and-offline-acceptance--2026-10-27).
