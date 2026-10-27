# 07: Correct identities without transferring misleading prices

**What to build:** Let the buyer correct identity fields while retaining original evidence and tracking intent and withdrawing affected prices, history qualification and alerts.

**Blocked by:** [05: Track exact products and send qualified target alerts](05-track-exact-products.md), [06: Show retained observations and acquisition gaps](06-show-observation-history.md)

**Status:** ready-for-agent

**Parent:** [Trustworthy UK watch discovery alongside existing monitoring](../../../docs/specs/watch-category-discovery.md)

- [ ] Provide a persistent field/value correction interaction through the feed/API, with original evidence, attribution, correction lineage and current disputed/resolved state.
- [ ] Invalidate affected bindings, cohorts, cost scenarios, history qualification and pending alert eligibility; never transfer a wrong configuration’s historical prices to the corrected product.
- [ ] Retain tracking intent and explain what needs requalification; historical assessments remain clearly historical instead of displaying their old bargain claims as current.
- [ ] Exercise overlap between acquisition, correction and alert dispatch, plus restart; stale assessment/evidence versions cannot publish as current or trigger a qualifying alert.
- [ ] Establish observable invalidation behavior that subsequent comparison and coupon slices must extend to their derived assessments; verify the correction workflow in the browser.

## Verification and authority

Use the buyer-approved API plus normal execution seam, controlled external edges and isolated storage; assert observable behavior. Include persistence/API/UI behavior for this slice and keep legacy Watch semantics compatible. Source implementation and offline verification only: no live collection, production DB operations, account connections, activation, deployment, purchase, commit or push is authorised by this ticket.
