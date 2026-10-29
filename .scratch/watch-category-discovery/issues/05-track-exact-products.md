# 05: Track exact products and send qualified target alerts

**What to build:** Let the buyer track an exact discovered product at a delivered-price target and receive only qualifying, deduplicated notifications.

**Blocked by:** [04: Show defensible UK delivered-cost scenarios](04-show-uk-delivered-cost.md)

**Status:** closed

**Assignee:** unclaimed

**Parent:** [Trustworthy UK watch discovery alongside existing monitoring](../../../docs/specs/watch-category-discovery.md)

- [x] Persist explicit exact-configuration tracking intent and an editable target through API/UI without silently rewriting legacy tracked-search behavior.
- [x] Alert once when a verified eligible UK delivered total crosses the target; suppress the same offer/price, allow a further qualifying drop, and allow a fresh crossing after rising above target.
- [x] Unknown totals, unresolved identities, stale/withdrawn evidence, preference mismatch and source recovery alone cannot trigger a verified bargain alert; explain eligible, above-target and withheld states in the feed.
- [x] Persist deduplication state across restart and duplicate acquisition routes; test interrupted delivery/recovery and report any transport guarantee limitations rather than claiming unsupported exactly-once delivery.
- [x] Verify the full discovery-to-target-to-captured-notification path with controlled time and qualification policies; do not invent production freshness or cadence defaults.

## Verification and authority

Use the buyer-approved API plus normal execution seam, controlled external edges and isolated storage; assert observable behavior. Include persistence/API/UI behavior for this slice and keep legacy Watch semantics compatible. Source implementation and offline verification only: no live collection, production DB operations, account connections, activation, deployment, purchase, commit or push is authorised by this ticket.

## Dependency ready: 2026-10-27

Ticket04 is closed for its offline scope after the
[FX repair merger acceptance](../../../docs/testing/watch-costs.md#fx-repair-merger-acceptance-2026-10-27).
This ticket is **READY and unclaimed**, reserved for parent dispatch. No
implementation, verification or claim for this ticket occurred in that merger;
its own checklist and separate live/buyer/activation gates remain open.

## Merger closure: 2026-10-27

**Closed for source implementation and deterministic offline verification.**
Resumed verification at clean history-preserving merge
`8facf4198d0f812f52cfb1dce055e5dd74d18e16`, retaining source
`0cc5c47349b9e01e61188b116681f6dff4ac2ce6`. No second merge, reset or
application-source repair was needed. All 77 retained application cases passed
across the suite invocation and one corrected-PATH rerun; six additional guarded
delivery probes passed. Focused Ruff (15 files), mypy (11 application files),
43-file retained source-manifest comparison and diff checks passed. Unchanged
25-test/build and three browser-flow receipts were retained without rerunning.

See the [dated merger acceptance receipt](../../../docs/testing/watch-tracking.md#merger-acceptance-2026-10-27)
for commands, checklist evidence, the initial Node PATH failure, transport
ambiguity and limitations. The first qualified observation establishes a baseline;
only verified standalone `public_no_coupon` totals feed target decisions. Coupon
integration must preserve identity, eligibility, revision and freshness gates.

Ticket10 is READY and unclaimed for parent dispatch. Ticket06's lineage failure
and 09's receipt-provenance failure remain open with their existing repair owners;
07 remains blocked on 06. No later ticket implementation or acceptance occurred.
Collection remains staged; live/buyer/operating/activation gates remain open.
