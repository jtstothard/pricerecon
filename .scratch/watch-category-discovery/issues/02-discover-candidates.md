# 02: Discover candidates in an image-led feed

**What to build:** Discover wristwatch candidates independently of saved searches and display simultaneous illustrated candidates with editable preferences and honest uncertainty.

**Blocked by:** [01: Verify existing monitoring in isolation](01-verify-existing-monitoring.md)

**Status:** ready-for-agent

**Parent:** [Trustworthy UK watch discovery alongside existing monitoring](../../../docs/specs/watch-category-discovery.md)

- [ ] Run a deterministic category-discovery acquisition through existing connector/execution facilities and persist a candidate not named by any saved Watch, with discovery origin, timestamp and evidence lineage.
- [ ] Expose candidates through the application API and image-led feed, including attribution and permitted provenance for images or clearly labelled original placeholders.
- [ ] Persist editable compact/colourful/budget preferences, expose their interpretation, and distinguish hard constraints, soft preferences and unknown dimensions; example values do not become permanent personal defaults.
- [ ] Keep unresolved candidates visible with explicit missing-data labels; do not infer verified delivered prices, usual prices, savings or bargain alerts from leads.
- [ ] Verify preference changes and candidate persistence across reload through the accepted application seam and a focused UI check while legacy monitoring remains intact.

## Verification and authority

Use the buyer-approved API plus normal execution seam, controlled external edges and isolated storage; assert observable behavior. Include persistence/API/UI behavior for this slice and keep legacy Watch semantics compatible. Source implementation and offline verification only: no live collection, production DB operations, account connections, activation, deployment, purchase, commit or push is authorised by this ticket.
