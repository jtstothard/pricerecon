# 08: Compare qualified offers and explain price claims

**What to build:** Compare qualified offers with scoped current-best and dated observed-low explanations while withholding unsupported usual-price and savings claims.

**Blocked by:** [07: Correct identities without transferring misleading prices](07-correct-identities.md)

**Status:** blocked — ticket07 merger repair required

**Assignee:** unclaimed

**Parent:** [Trustworthy UK watch discovery alongside existing monitoring](../../../docs/specs/watch-category-discovery.md)

- [ ] Persist/version assessments and expose their cohort, method, evidence, exclusions, coverage, date/window and eligibility in API/feed details.
- [ ] Separate new/used, quantity and destination/eligibility cohorts and exclude auction bids from buy-now comparisons; rank only currently qualified comparable costs within declared coverage.
- [ ] Dated observed low comes only from qualifying retained observations within the stated window, not global/all-time claims; show missing coverage and history gaps.
- [ ] Usual price, personal eligible price and current-best/observed-low gates remain independent. Defer numerical estimator/window/sufficiency calibration until accepted empirical evidence; show unavailable usual price and no invented savings in the meantime.
- [ ] Corrections, stale evidence and policy changes invalidate derived comparisons; verify contradictory, sparse and duplicate evidence and the corresponding UI explanations.

## Verification and authority

Use the buyer-approved API plus normal execution seam, controlled external edges and isolated storage; assert observable behavior. Include persistence/API/UI behavior for this slice and keep legacy Watch semantics compatible. Source implementation and offline verification only: no live collection, production DB operations, account connections, activation, deployment, purchase, commit or push is authorised by this ticket.
