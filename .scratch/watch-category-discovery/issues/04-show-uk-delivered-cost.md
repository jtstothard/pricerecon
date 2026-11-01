# 04: Show defensible UK delivered-cost scenarios

**What to build:** Show exact-offer UK delivered costs as verified, conditional or unknown, with understandable components and assumptions.

**Blocked by:** [03: Explain exact configuration and offer qualification](03-explain-offer-qualification.md)

**Status:** ready-for-agent

**Parent:** [Trustworthy UK watch discovery alongside existing monitoring](../../../docs/specs/watch-category-discovery.md)

- [ ] Persist versioned cost scenarios bound to configuration/selection, seller/condition/purchase mode, quantity, destination, dispatch, basket/consignment and payment context; expose them through API and expandable feed details.
- [ ] Use precise monetary arithmetic and distinguish item, shipping, merchant-collected tax, additional import/carrier/payment liabilities and applicable FX context; included VAT is counted once.
- [ ] Every verified component is evidenced or supported as inapplicable; missing price, currency or charges cannot become zero or GBP by default. Conditional assumptions accompany amounts; unbounded missing components yield unknown total and known subtotal.
- [ ] Exercise included VAT, quantity/threshold changes, international GBP display, unknown shipping/fees and conflicting evidence using dated or explicitly synthetic fixtures, without implementing speculative legal rates.
- [ ] Item-price prefilters do not establish a delivered budget; show a valid no-coupon public scenario and keep personal/payment/cashback scenarios distinct.

## Verification and authority

Use the buyer-approved API plus normal execution seam, controlled external edges and isolated storage; assert observable behavior. Include persistence/API/UI behavior for this slice and keep legacy Watch semantics compatible. Source implementation and offline verification only: no live collection, production DB operations, account connections, activation, deployment, purchase, commit or push is authorised by this ticket.
