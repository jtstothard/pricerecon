# 05: Track exact products and send qualified target alerts

**What to build:** Let the buyer track an exact discovered product at a delivered-price target and receive only qualifying, deduplicated notifications.

**Blocked by:** [04: Show defensible UK delivered-cost scenarios](04-show-uk-delivered-cost.md)

**Status:** ready-for-agent

**Assignee:** unclaimed

**Parent:** [Trustworthy UK watch discovery alongside existing monitoring](../../../docs/specs/watch-category-discovery.md)

- [ ] Persist explicit exact-configuration tracking intent and an editable target through API/UI without silently rewriting legacy tracked-search behavior.
- [ ] Alert once when a verified eligible UK delivered total crosses the target; suppress the same offer/price, allow a further qualifying drop, and allow a fresh crossing after rising above target.
- [ ] Unknown totals, unresolved identities, stale/withdrawn evidence, preference mismatch and source recovery alone cannot trigger a verified bargain alert; explain eligible, above-target and withheld states in the feed.
- [ ] Persist deduplication state across restart and duplicate acquisition routes; test interrupted delivery/recovery and report any transport guarantee limitations rather than claiming unsupported exactly-once delivery.
- [ ] Verify the full discovery-to-target-to-captured-notification path with controlled time and qualification policies; do not invent production freshness or cadence defaults.

## Verification and authority

Use the buyer-approved API plus normal execution seam, controlled external edges and isolated storage; assert observable behavior. Include persistence/API/UI behavior for this slice and keep legacy Watch semantics compatible. Source implementation and offline verification only: no live collection, production DB operations, account connections, activation, deployment, purchase, commit or push is authorised by this ticket.

## Dependency ready: 2026-10-27

Ticket04 is closed for its offline scope after the
[FX repair merger acceptance](../../../docs/testing/watch-costs.md#fx-repair-merger-acceptance-2026-10-27).
This ticket is **READY and unclaimed**, reserved for parent dispatch. No
implementation, verification or claim for this ticket occurred in that merger;
its own checklist and separate live/buyer/activation gates remain open.
