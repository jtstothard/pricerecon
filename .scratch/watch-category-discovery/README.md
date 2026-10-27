# Watch category discovery implementation

Spec: [Trustworthy UK watch discovery](../../docs/specs/watch-category-discovery.md).

Integration branch: `integration/watch-category-discovery`. Base: `ef86af6d41fbb3cac8982f43997068e906477025`.

This is the implementation tracker. The planning decisions under `docs/product/category-discovery/tickets/` remain their own closed investigation graph. Named **Blocked by** links in these implementation issues define the frontier. Claim ready issues before starting; close them only with dated evidence against their checklists. Record partial, blocked and unproven acceptance explicitly.

| Ticket | Requires | State |
| --- | --- | --- |
| [01: Existing monitoring](issues/01-verify-existing-monitoring.md) | None | Closed |
| [02: Candidate discovery](issues/02-discover-candidates.md) | 01 | Closed |
| [03: Qualification](issues/03-explain-offer-qualification.md) | 02 | In progress |
| [04: UK delivered cost](issues/04-show-uk-delivered-cost.md) | 03 | Blocked |
| [05: Exact tracking](issues/05-track-exact-products.md) | 04 | Blocked |
| [06: Observation history](issues/06-show-observation-history.md) | 04 | Blocked |
| [07: Corrections](issues/07-correct-identities.md) | 05, 06 | Blocked |
| [08: Comparisons](issues/08-compare-qualified-offers.md) | 07 | Blocked |
| [09: Public coupons](issues/09-evaluate-public-coupons.md) | 04 | Blocked |
| [10: Shared limits](issues/10-prioritise-tracking.md) | 05 | Blocked |
| [11: Source evidence](issues/11-carry-source-evidence.md) | 03, 10 | Blocked |
| [12: Integrated verification](issues/12-verify-complete-watch-workflow.md) | 08, 09, 11 | Blocked |

## Authority and acceptance

Work is limited to source implementation and deterministic offline verification with isolated storage and controlled external edges. The buyer explicitly authorised local commits/merges for this continuation, overriding the older issue-level prohibition. No live collection, accounts, production database, activation, deployment, purchases, pushes or PRs are authorised.

Ticket 01 source was integrated on 2026-10-27 in merge `a0e5c1a612252c61a62eabc7b56ebc3b3297ed85`, preserving implementer HEAD `9312871f269137d7b98ba7155d9523350e41e62e`. The subsequent rendered-form preservation repair was integrated in merge `3243c8f00e3f9dd9efde79327b6905eb3d4354b2`, preserving implementer HEAD `534cecaece62e30f50c680b40af5b4c7f561b6e4`. Integration checks passed **15 isolated workflow tests**, **25 frontend tests** and the frontend build. The parent subsequently passed the rendered edit/save/reload/manual-check regression. Tickets 01 and 02 are now closed for their offline scope, and ticket 03 is claimed for the parent continuation. See the dated resolution log below and the [repair integration receipt](issues/01-verify-existing-monitoring.md#preservation-repair-integration-receipt-2026-10-27).

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
