# 11: Carry source evidence and access limits through acquisition

**What to build:** Carry existing route-specific evidence and source capability limits through acquisition into the buyer feed without silently activating staged or unqualified routes.

**Blocked by:** [03: Explain exact configuration and offer qualification](03-explain-offer-qualification.md), [10: Prioritise tracking under shared collection limits](10-prioritise-tracking.md)

**Status:** open — merger blocker reproduced 2026-10-27

**Assignee:** Parent continuation for the contained source finding

**Parent:** [Trustworthy UK watch discovery alongside existing monitoring](../../../docs/specs/watch-category-discovery.md)

- [ ] Extend existing adapters only where needed to preserve selected variation, issuer/retrieval lineage, seller/condition/purchase mode, destination/availability, missing fields and acquisition outcomes through storage/API/UI.
- [x] Use retained or synthetic permitted fixtures for AliExpress browser-first and eBay Browse reviewed lead lanes and a contrasting retailer case; retrieval success alone cannot qualify selected SKU, stock, UK total or history rights.
- [x] Account visibly for mandatory AliExpress, eBay/second-hand, brand-direct, UK retail, UK-shipping international and search/aggregator/community families, retaining blocked/unqualified states and paging/capture limits.
- [x] Keep access/retention prerequisites explicit, route all attempts/retries/fallbacks through shared admission, and leave staged acquisition lanes inactive unless separately authorised.
- [ ] Contract tests exercise real adapter result shapes and failure states at the application boundary without new network calls, credentials, account operations or archived merchant content beyond permitted evidence.

## Verification and authority

Use the buyer-approved API plus normal execution seam, controlled external edges and isolated storage; assert observable behavior. Include persistence/API/UI behavior for this slice and keep legacy Watch semantics compatible. Source implementation and offline verification only: no live collection, production DB operations, account connections, activation, deployment, purchase, commit or push is authorised by this ticket.


## Dependency disposition — 2026-10-27

Ticket10 is merged but remains open after concrete API/scheduler/fresh-process
probes bypass its persisted finite grant outside the supplied context. See the
[10 merger disposition](../../../docs/testing/watch-collection.md#merger-disposition--2026-10-27).
This ticket remains blocked and unclaimed; no 11 implementation was performed.

### Dependency recheck — 2026-10-27

The shared-grant bypass repair is merged and its exact original probes pass.
Ticket10 remains open for reproduced denied Watch status/timestamp failures;
see the [repair merger review](../../../docs/testing/watch-collection.md#shared-grant-repair-merger-review--2026-10-27).
This ticket stays blocked and unclaimed. No 11 implementation occurred.

### Dependency accepted and claim — 2026-10-27

10 is closed after its denied Watch completion repair: 160 guarded workflows,
37 contracts and all eight retained API/scheduler denial probes pass. Both
blocking tickets are now closed for offline scope. This ticket is claimed for
one isolated implementer; no source11 implementation is asserted here. Shared
admission and staged activation constraints remain authoritative.

### Implementation handoff — 2026-10-27, parent acceptance pending

All five implementation checklist items have deterministic source proof in the
isolated `t3/carry-source-evidence` branch. Existing AliExpress browser, eBay Browse
and Shopify adapters feed native acquisition/storage/API/UI with original
synthetic external payloads. Six mandatory families / 16 routes, blocked signing
and source-use prerequisites, selected versus unbound prices, missing fields,
pagination/truncation and source failures remain explicit. No acquisition lane is
activated and no real Militado/Merkur evidence is promoted.

The implementation's required local commits and integration merges were explicitly
authorised by the current implement-spec task, overriding the older no-commit
wording above. The latest integration includes08 and its type-factory repair.
186 guarded workflows passed before that type-only refresh; 38 focused source /
assessment / tracking workflows and 17-file uncached mypy pass afterwards.
37 limiter/browser contracts, 25 frontend checks, build and actual merged desktop /
narrow source and assessment UI proof pass. Existing ESLint missing-config and
inherited Ruff diagnostics are retained separately. See the [dated source-evidence
receipt](../../../docs/testing/watch-source-evidence.md) for exact identities,
commands, hashes, red/green results and remaining gates.

**Status remains in-progress.** The parent merger owns independent acceptance and
closure; ticket12, buyer/live/rights/operating and activation gates remain separate.


### Sole merger review — 2026-10-27

Full source history was merged with `--no-ff` as
`8eb1d777ed7614a69712ea8f074af67fa0dd7550`, preserving source
`7fb56beb54f9b60a0555eee53df0c2b31e718e0c` and integration
`446ee9e649ad91406d66cb5b0c43990f3be590db` as its two parents.
**11 remains open; 12 remains blocked and unclaimed.**

The independent application/API probe adds one malformed-price Shopify variant
beside the two passing original synthetic variants. The legacy listing parser
raises before the new typed evidence parser, losing both valid siblings and
persisting zero-page/unknown limits despite two accounted sends. The unchanged
control passes. Reopened the adapter/failure-state checklist items for this
concrete boundary failure; other checked items describe observed offline scope.
The parent owns the small source repair; no repair or 12 work was performed here.
See the [merger disposition and exact reproducer](../../../docs/testing/watch-source-evidence.md#sole-merger-disposition--2026-10-27).
