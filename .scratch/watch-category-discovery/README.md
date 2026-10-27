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
| [05: Exact tracking](issues/05-track-exact-products.md) | 04 | In progress |
| [06: Observation history](issues/06-show-observation-history.md) | 04 | Open — repair required |
| [07: Corrections](issues/07-correct-identities.md) | 05, 06 | Blocked |
| [08: Comparisons](issues/08-compare-qualified-offers.md) | 07 | Blocked |
| [09: Public coupons](issues/09-evaluate-public-coupons.md) | 04 | In progress |
| [10: Shared limits](issues/10-prioritise-tracking.md) | 05 | Blocked |
| [11: Source evidence](issues/11-carry-source-evidence.md) | 03, 10 | Blocked |
| [12: Integrated verification](issues/12-verify-complete-watch-workflow.md) | 08, 09, 11 | Blocked |

## Authority and acceptance

Work is limited to source implementation and deterministic offline verification with isolated storage and controlled external edges. The buyer explicitly authorised local commits/merges for this continuation, overriding the older issue-level prohibition. No live collection, accounts, production database, activation, deployment, purchases, pushes or PRs are authorised.

Ticket 01 source was integrated on 2026-10-27 in merge `a0e5c1a612252c61a62eabc7b56ebc3b3297ed85`, preserving implementer HEAD `9312871f269137d7b98ba7155d9523350e41e62e`. The subsequent rendered-form preservation repair was integrated in merge `3243c8f00e3f9dd9efde79327b6905eb3d4354b2`, preserving implementer HEAD `534cecaece62e30f50c680b40af5b4c7f561b6e4`. Integration checks passed **15 isolated workflow tests**, **25 frontend tests** and the frontend build. The parent subsequently passed the rendered edit/save/reload/manual-check regression. Tickets 01–04 are now closed for their offline scope. Tickets05/09 remain in progress; ticket06 remains open for the derived-capture repair documented below. Ticket07 remains blocked by05/06. See the dated resolution log below and the [repair integration receipt](issues/01-verify-existing-monitoring.md#preservation-repair-integration-receipt-2026-10-27).

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
