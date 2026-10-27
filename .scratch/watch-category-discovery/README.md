# Watch category discovery implementation

Spec: [Trustworthy UK watch discovery](../../docs/specs/watch-category-discovery.md).

Integration branch: `integration/watch-category-discovery`. Base: `ef86af6d41fbb3cac8982f43997068e906477025`.

This is the implementation tracker. The planning decisions under `docs/product/category-discovery/tickets/` remain their own closed investigation graph. Named **Blocked by** links in these implementation issues define the frontier. Claim ready issues before starting; close them only with dated evidence against their checklists. Record partial, blocked and unproven acceptance explicitly.

| Ticket | Requires | State |
| --- | --- | --- |
| [01: Existing monitoring](issues/01-verify-existing-monitoring.md) | None | In progress |
| [02: Candidate discovery](issues/02-discover-candidates.md) | 01 | Blocked |
| [03: Qualification](issues/03-explain-offer-qualification.md) | 02 | Blocked |
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

Work is limited to source implementation and deterministic offline verification with isolated storage and controlled external edges. Local commit/merge authority was requested separately because each issue excludes commits. No live collection, accounts, production database, activation, deployment, purchases or pushes are authorised.

Actual buyer walkthrough feedback, current source rights, live offer/history/cost proof, finite operating limits and named maintenance ownership cannot be fabricated by passing fixture tests. Keep these gates explicit in the final receipt.
