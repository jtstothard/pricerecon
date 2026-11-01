# 09: Evaluate public coupons without assuming stacks

**What to build:** Show public coupon opportunities, terms, eligibility and reproduced application separately, preserving a useful no-coupon delivered-price path.

**Blocked by:** [04: Show defensible UK delivered-cost scenarios](04-show-uk-delivered-cost.md)

**Status:** ready-for-agent

**Parent:** [Trustworthy UK watch discovery alongside existing monitoring](../../../docs/specs/watch-category-discovery.md)

- [ ] Persist exact selection/basket/destination terms and application evidence with eligibility, expiry, minimum spend, quantity and compatibility; expose status and explanations in API/feed.
- [ ] Distinguish advertised opportunity, evidenced applicability and reproduced exact-basket application; advertised terms alone cannot reduce a verified total.
- [ ] Exercise incompatible stacks, app/new-customer or membership restrictions, time boundaries and basket changes; absence of a prohibition does not establish compatibility.
- [ ] Keep public, personal, payment and uncertain cashback scenarios separate. Do not build personal-benefit integrations or treat cashback as a guaranteed checkout reduction.
- [ ] Invalidate derived applications/totals when their identity or terms evidence changes; if correction UI has landed, exercise it end to end. Fixture coupon success is not live proof, and no-coupon success does not close the coupon-success gate.

## Verification and authority

Use the buyer-approved API plus normal execution seam, controlled external edges and isolated storage; assert observable behavior. Include persistence/API/UI behavior for this slice and keep legacy Watch semantics compatible. Source implementation and offline verification only: no live collection, production DB operations, account connections, activation, deployment, purchase, commit or push is authorised by this ticket.
