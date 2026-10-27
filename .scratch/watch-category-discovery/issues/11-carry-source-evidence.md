# 11: Carry source evidence and access limits through acquisition

**What to build:** Carry existing route-specific evidence and source capability limits through acquisition into the buyer feed without silently activating staged or unqualified routes.

**Blocked by:** [03: Explain exact configuration and offer qualification](03-explain-offer-qualification.md), [10: Prioritise tracking under shared collection limits](10-prioritise-tracking.md)

**Status:** blocked — ticket10 shared-admission repair required

**Assignee:** unclaimed

**Parent:** [Trustworthy UK watch discovery alongside existing monitoring](../../../docs/specs/watch-category-discovery.md)

- [ ] Extend existing adapters only where needed to preserve selected variation, issuer/retrieval lineage, seller/condition/purchase mode, destination/availability, missing fields and acquisition outcomes through storage/API/UI.
- [ ] Use retained or synthetic permitted fixtures for AliExpress browser-first and eBay Browse reviewed lead lanes and a contrasting retailer case; retrieval success alone cannot qualify selected SKU, stock, UK total or history rights.
- [ ] Account visibly for mandatory AliExpress, eBay/second-hand, brand-direct, UK retail, UK-shipping international and search/aggregator/community families, retaining blocked/unqualified states and paging/capture limits.
- [ ] Keep access/retention prerequisites explicit, route all attempts/retries/fallbacks through shared admission, and leave staged acquisition lanes inactive unless separately authorised.
- [ ] Contract tests exercise real adapter result shapes and failure states at the application boundary without new network calls, credentials, account operations or archived merchant content beyond permitted evidence.

## Verification and authority

Use the buyer-approved API plus normal execution seam, controlled external edges and isolated storage; assert observable behavior. Include persistence/API/UI behavior for this slice and keep legacy Watch semantics compatible. Source implementation and offline verification only: no live collection, production DB operations, account connections, activation, deployment, purchase, commit or push is authorised by this ticket.


## Dependency disposition — 2026-10-27

Ticket10 is merged but remains open after concrete API/scheduler/fresh-process
probes bypass its persisted finite grant outside the supplied context. See the
[10 merger disposition](../../../docs/testing/watch-collection.md#merger-disposition--2026-10-27).
This ticket remains blocked and unclaimed; no 11 implementation was performed.
