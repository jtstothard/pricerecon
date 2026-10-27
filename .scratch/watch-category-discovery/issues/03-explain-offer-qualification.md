# 03: Explain exact configuration and offer qualification

**What to build:** Explain which exact wristwatch configuration and merchant variation a candidate represents, and why its offer qualifies or remains unresolved.

**Blocked by:** [02: Discover candidates in an image-led feed](02-discover-candidates.md)

**Status:** in-progress

**Assignee:** Codex (parent continuation)

**Parent:** [Trustworthy UK watch discovery alongside existing monitoring](../../../docs/specs/watch-category-discovery.md)

- [ ] Persist and expose configuration identity, selected merchant-variation binding and comparison qualification separately, with field-level issuer/extractor provenance and shared derivation lineage.
- [ ] Apply category-owned reference, generation, movement, size, dial and strap rules; exercise near-reference, revision, accessory, first-SKU and generic-stock traps without promoting title equality or confidence to proof.
- [ ] Present seller, condition, quantity, availability and purchase mode; distinguish new/used and auction/buy-now without claiming photo-based authenticity or internal health.
- [ ] Show conflicting, missing and rejected evidence in expandable feed details; copied search leads and repeated AI extraction cannot become independent confirmation.
- [ ] Use the named five-case cohort for deterministic qualification/abstention examples, retaining missing Merkur/Militado evidence as missing rather than substituting a different product.

## Verification and authority

Claimed 2026-10-27 after ticket02's offline integration closure. Implementation
`2b5a167f9ae305b4dd088cf31e1dbd581d1d14cf` was integrated without conflicts in
history-preserving merge `b520fb8a978cbf94dfa611f9e35c621887a4ee1d` on 2026-10-27.
**Acceptance remains partial; this issue stays open and ticket04 stays blocked.**

The merger passed 29 isolated workflows (9 qualification, 5 discovery, all 15
legacy), 25 frontend tests, build, focused Ruff/mypy and diff checks, and inspected
the retained desktop/375px browser evidence. ESLint remains blocked by the missing
`eslint.config.*`. Two additional isolated API reproductions expose missing gates:

- A currency claim changed to USD while report/price context remains GBP leaves
  both the binding and merchant offer `supported`, without a qualification issue.
- Distinct mint/blue configuration subjects on two variations of one listing,
  both missing generation, collapse into one retained configuration. Both bindings
  name the first configuration, losing the second subject's resolved dimensions.

The first, second and fourth checklist items therefore cannot be accepted in full.
See the [merger receipt and reproduction details](../../../docs/testing/watch-qualification.md#merger-verification-2026-10-27).
No implementation repair or ticket04 work was performed by the merger. Rerun the
missing cases through the accepted seam after repair before closure or claiming04.

Use the buyer-approved API plus normal execution seam, controlled external edges and isolated storage; assert observable behavior. Include persistence/API/UI behavior for this slice and keep legacy Watch semantics compatible. Source implementation and offline verification only: no live collection, production DB operations, account connections, activation, deployment, purchase, commit or push is authorised by this ticket.
