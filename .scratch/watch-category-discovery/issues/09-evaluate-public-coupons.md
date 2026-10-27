# 09: Evaluate public coupons without assuming stacks

**What to build:** Show public coupon opportunities, terms, eligibility and reproduced application separately, preserving a useful no-coupon delivered-price path.

**Blocked by:** [04: Show defensible UK delivered-cost scenarios](04-show-uk-delivered-cost.md)

**Status:** closed — offline implementation accepted 2026-10-27

**Assignee:** unclaimed

**Parent:** [Trustworthy UK watch discovery alongside existing monitoring](../../../docs/specs/watch-category-discovery.md)

- [x] Persist exact selection/basket/destination terms and application evidence with eligibility, expiry, minimum spend, quantity and compatibility; expose status and explanations in API/feed.
- [x] Distinguish advertised opportunity, evidenced applicability and reproduced exact-basket application; advertised terms alone cannot reduce a verified total.
- [x] Exercise incompatible stacks, app/new-customer or membership restrictions, time boundaries and basket changes; absence of a prohibition does not establish compatibility.
- [x] Keep public, personal, payment and uncertain cashback scenarios separate. Do not build personal-benefit integrations or treat cashback as a guaranteed checkout reduction.
- [x] Invalidate derived applications/totals when their identity or terms evidence changes; if correction UI has landed, exercise it end to end. Fixture coupon success is not live proof, and no-coupon success does not close the coupon-success gate.

## Verification and authority

Use the buyer-approved API plus normal execution seam, controlled external edges and isolated storage; assert observable behavior. Include persistence/API/UI behavior for this slice and keep legacy Watch semantics compatible. Source implementation and offline verification only: no live collection, production DB operations, account connections, activation, deployment, purchase, commit or push is authorised by this ticket.

## Dependency ready: 2026-10-27

Ticket04 is closed for its offline scope after the
[FX repair merger acceptance](../../../docs/testing/watch-costs.md#fx-repair-merger-acceptance-2026-10-27).
This ticket is **READY and unclaimed**, reserved for parent dispatch. No
implementation, verification or claim for this ticket occurred in that merger;
its own checklist and separate live/buyer/activation gates remain open.

## Merger disposition — 2026-10-27

**09 stays open.** Source `db08536203eeba32cd7e462b28b977237492d955`
was integrated with history-preserving merge
`2b4686bc2c60ff397502c9ace2f10e225423199f` onto requested integration
`b97f37a44241bf29d5a252a191e93e8bc240cb0f`, without conflicts.
All **65 isolated workflows** passed (48 baseline, seven history, ten coupon),
as did 25 frontend tests, production build and focused Ruff/mypy.
Retained actual desktop/narrow browser artifacts were inspected.

The additional guarded API/execution probe reproduced **compatibility evidence
and eligibility evidence each being accepted as the entire application receipt
provenance**. No checkout evidence remains in either input, yet both feed and
coupon-history API expose `reproduced_at_observation`, no issues and a verified
GBP 45.10 result. This violates the unchecked second acceptance item. The normal
GBP 50.10 no-coupon path stays unchanged; no alert or savings claim is enabled.
A positive control with newly quoted GBP 4.20 shipping correctly reconciles
GBP 47.20 through the shared cost engine.

See the [dated merger receipt and exact reproducer](../../../docs/testing/watch-coupons.md#merger-verification--2026-10-27).
No production repair was attempted. Ticket06's separate parent-owned derived
capture gap remains open and was neither fixed nor used to explain this failure.
Ticket07 correction UI is absent: its future correction/invalidation transaction
and overlapping acquisition must still be integrated and exercised. Checked
identity/terms invalidation here applies only to the acquisition/revision seam.
No later ticket was claimed or implemented; collection remains staged, with
live coupon proof, buyer acceptance and activation gates unproven.

## Receipt-provenance repair merger acceptance — 2026-10-27

**09 closed for offline implementation.** Clean repair source
`d2ab666b9bc616c8172ebdd39b5194cf6aa2b623` already contained requested clean
integration `61ab075703e64b9589deb34b12f8acbacd929972`. Conflict-free
`--no-ff` merge `5a3124e9f059e87a3bf5cb4e7925f7a85fb43422` preserves both
parents and the complete repair history. The merged tree exactly matches source.

Before merging, the unchanged original probe independently reproduced both
unsupported GBP45.10 results. Afterwards, both entire-provenance substitutions
withhold payable with `application_receipt_missing`; genuine GBP45.10 and
changed-shipping GBP47.20 controls pass, and the GBP50.10 no-coupon path remains.
All **85 combined isolated workflows passed in 72.80s**, with focused Ruff/mypy,
the original probe and 23 receipt controls passing. A guarded database seeded by
the pre-repair normal workflow confirms old role-less successes are invalidated
on restart and supersession, preserving original evidence and GBP45.10 only as
historical. No assertion was removed or weakened; the shared cost engine remains
the payable/FX owner. Unchanged frontend/build/browser evidence is reused.

See the [dated repair merger receipt](../../../docs/testing/watch-coupons.md#receipt-provenance-repair-merger-acceptance--2026-10-27)
for commands, retained results and review boundaries.

**Retained integration gate:** 07 is active in its separate worktree and has not
landed here. Its correction append/invalidation transaction, UI and overlapping
correction/acquisition must still be connected and verified against coupon
lineage when that slice lands. Current proof covers acquisition/revision/policy
invalidation only. Ticket10 and the original dirty parent were untouched; no
07/10 implementation or later ticket claim occurred. Ticket12 stays blocked by
its other dependencies and its integrated proof requirements.

Collection remains staged. Live coupon application, source mapping/direct-capture
semantics, rights/retention, freshness, buyer acceptance, comparisons/savings,
operating limits and activation/deployment remain separate unproven gates.
