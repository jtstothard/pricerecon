# 04: Show defensible UK delivered-cost scenarios

**What to build:** Show exact-offer UK delivered costs as verified, conditional or unknown, with understandable components and assumptions.

**Blocked by:** [03: Explain exact configuration and offer qualification](03-explain-offer-qualification.md)

**Status:** in-progress

**Assignee:** Codex (parent continuation)

**Parent:** [Trustworthy UK watch discovery alongside existing monitoring](../../../docs/specs/watch-category-discovery.md)

- [ ] Persist versioned cost scenarios bound to configuration/selection, seller/condition/purchase mode, quantity, destination, dispatch, basket/consignment and payment context; expose them through API and expandable feed details.
- [ ] Use precise monetary arithmetic and distinguish item, shipping, merchant-collected tax, additional import/carrier/payment liabilities and applicable FX context; included VAT is counted once.
- [ ] Every verified component is evidenced or supported as inapplicable; missing price, currency or charges cannot become zero or GBP by default. Conditional assumptions accompany amounts; unbounded missing components yield unknown total and known subtotal.
- [ ] Exercise included VAT, quantity/threshold changes, international GBP display, unknown shipping/fees and conflicting evidence using dated or explicitly synthetic fixtures, without implementing speculative legal rates.
- [ ] Item-price prefilters do not establish a delivered budget; show a valid no-coupon public scenario and keep personal/payment/cashback scenarios distinct.

## Verification and authority

Use the buyer-approved API plus normal execution seam, controlled external edges and isolated storage; assert observable behavior. Include persistence/API/UI behavior for this slice and keep legacy Watch semantics compatible. Source implementation and offline verification only: no live collection, production DB operations, account connections, activation, deployment, purchase, commit or push is authorised by this ticket.

## Claim: 2026-10-27

Claimed after ticket03's offline repair acceptance and history-preserving merge
`bf0d3f90164bad7ac3efe657a309d141a9dff6fd`. See the
[repair merger receipt](../../../docs/testing/watch-qualification.md#repair-merger-verification-2026-10-27).
No ticket04 implementation or cost verification was performed by the merger.
All checklist items remain open. Collection stays staged and totals remain
unknown; live/source/buyer and activation gates remain separate.

## Implementation handoff: 2026-10-27

Source implementation and deterministic verification are ready for merger review
on `t3/ticket04-offer-cost-evidence`. See the [dated cost receipt](../../../docs/testing/watch-costs.md)
for checklist coverage, application red/green, retained desktop/narrow browser
proof, commands and remaining gates. Checklist acceptance and ticket closure are
left to the merger. Collection remains staged; observation-time cost verification
does not establish current freshness, comparison acceptance or a live offer.

## Merger review: 2026-10-27 — remains open

Integrated source `af2ab0f8ed031d91a0f1e5af36e93a6fcbfdb8b9` in history-preserving
merge `ed1404b20d810371c07489044952552ab4d07452`. The 46 documented isolated
workflows, 25 frontend tests, build and focused Ruff/mypy passed; retained browser
artifacts were inspected. Existing ESLint configuration failure remains recorded.

The precise-money/FX acceptance item is **not met**: equivalent rounding quanta
`0.01`/`0.010` and `1E+1`/`10`/`10.0` produce different persisted API and public
totals, all labelled `verified_at_observation`. The latter group also changes
budget fit. See the [dated merger receipt](../../../docs/testing/watch-costs.md#merger-verification-2026-10-27)
and retained isolated application probe. Canonicalize the quantum exactly or
reject unsupported representations, then verify the repaired application behavior
without regressing the near-power rejection. Merger made no implementation repair.

Checklist closure is withheld. Tickets 05/06/09 stay blocked; parent owns future
claims/dispatch. All source/live/legal/freshness/comparison/alert and activation
gates remain separate.
