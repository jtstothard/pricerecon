# 03: Explain exact configuration and offer qualification

**What to build:** Explain which exact wristwatch configuration and merchant variation a candidate represents, and why its offer qualifies or remains unresolved.

**Blocked by:** [02: Discover candidates in an image-led feed](02-discover-candidates.md)

**Status:** closed

**Assignee:** Codex (merger verification)

**Parent:** [Trustworthy UK watch discovery alongside existing monitoring](../../../docs/specs/watch-category-discovery.md)

- [x] Persist and expose configuration identity, selected merchant-variation binding and comparison qualification separately, with field-level issuer/extractor provenance and shared derivation lineage.
- [x] Apply category-owned reference, generation, movement, size, dial and strap rules; exercise near-reference, revision, accessory, first-SKU and generic-stock traps without promoting title equality or confidence to proof.
- [x] Present seller, condition, quantity, availability and purchase mode; distinguish new/used and auction/buy-now without claiming photo-based authenticity or internal health.
- [x] Show conflicting, missing and rejected evidence in expandable feed details; copied search leads and repeated AI extraction cannot become independent confirmation.
- [x] Use the named five-case cohort for deterministic qualification/abstention examples, retaining missing Merkur/Militado evidence as missing rather than substituting a different product.

## Verification and authority

Claimed 2026-10-27 after ticket02's offline integration closure. Implementation
`2b5a167f9ae305b4dd088cf31e1dbd581d1d14cf` was integrated without conflicts in
history-preserving merge `b520fb8a978cbf94dfa611f9e35c621887a4ee1d` on 2026-10-27.
**Historical first-merger result:** acceptance was partial; this issue stayed open
and ticket04 stayed blocked. The repair acceptance below supersedes that result.

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
No implementation repair or ticket04 work was performed in that first merger
round. The required repair reproduction and acceptance are recorded below.

Use the buyer-approved API plus normal execution seam, controlled external edges and isolated storage; assert observable behavior. Include persistence/API/UI behavior for this slice and keep legacy Watch semantics compatible. Source implementation and offline verification only: no live collection, production DB operations, account connections, activation, deployment, purchase, commit or push is authorised by this ticket.

## Repair integration and closure: 2026-10-27

Repair `dad3273a3100b0aa920e24d2ea8abc990fab7d44` was integrated without conflicts
in history-preserving merge `bf0d3f90164bad7ac3efe657a309d141a9dff6fd`, preserving
parents `95f675e` and `dad3273`. Both original failures were independently
reproduced against `95f675e` before merging and pass on the merged tree.

**All five checklist items are accepted for deterministic offline scope.** The
merger passed 34 isolated workflows (all 29 previous workflows), focused Ruff,
mypy on 12 source files and diff checks. The five-subject fresh-process/reordered
recapture checks retain definition and keyless fallback IDs, dimensions,
evidence/derivation lineage and configuration/binding revisions. Multiple offers
remain distinct. An additional isolated API/SQLite probe confirmed stable offer
IDs, revision links, unchanged historical rows and no foreign-key errors, with
zero blocked external edges and zero notifications.

Frontend code and artifacts did not change. The source's 25-test/build receipt
was retained and earlier desktop/375px browser proof inspected; neither is claimed
as a fresh browser run. The documented missing ESLint configuration remains.
See the [full repair merger receipt](../../../docs/testing/watch-qualification.md#repair-merger-verification-2026-10-27).

Ticket03 is closed and ticket04 is claimed in progress for the parent
continuation. No ticket04 implementation occurred. Collection stays staged;
delivered totals, usual price, savings and alert eligibility remain withheld.
Historical collapsed records are not reconstructed. Real-source evidence,
retention, buyer walkthrough, UK costs, freshness and operating/activation gates
remain open; this closure does not establish live or release acceptance.
