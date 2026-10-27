# 06: Show retained observations and acquisition gaps

**What to build:** Show auditable retained offer observations and explicit acquisition gaps rather than treating snapshots or alert events as price history.

**Blocked by:** [04: Show defensible UK delivered-cost scenarios](04-show-uk-delivered-cost.md)

**Status:** in-progress

**Assignee:** unclaimed

**Parent:** [Trustworthy UK watch discovery alongside existing monitoring](../../../docs/specs/watch-category-discovery.md)

- [ ] Persist acquisition outcomes separately from filters/alerts and retain initial, unchanged, rising and falling observations with capture identity, availability, condition, quantity, destination, monetary/eligibility basis and policy versions.
- [ ] Expose history and gaps through API and buyer history/evidence views, including partial/failing/cached sources and missing periods; last-good evidence retains its age and is not silently current.
- [ ] Keep independent capture identity and derivation lineage so duplicate leads do not count as independent market observations.
- [ ] Cold start shows limited history, unavailable usual price and no fabricated savings; synthetic fixture dates never become real retained longitudinal evidence.
- [ ] Verify isolated additive migration preserves legacy rules/data without treating existing snapshots or sparse events as qualified new observations.

## Verification and authority

Use the buyer-approved API plus normal execution seam, controlled external edges and isolated storage; assert observable behavior. Include persistence/API/UI behavior for this slice and keep legacy Watch semantics compatible. Source implementation and offline verification only: no live collection, production DB operations, account connections, activation, deployment, purchase, commit or push is authorised by this ticket.

## Dependency ready: 2026-10-27

Ticket04 is closed for its offline scope after the
[FX repair merger acceptance](../../../docs/testing/watch-costs.md#fx-repair-merger-acceptance-2026-10-27).
This ticket is **READY and unclaimed**, reserved for parent dispatch. No
implementation, verification or claim for this ticket occurred in that merger;
its own checklist and separate live/buyer/activation gates remain open.
