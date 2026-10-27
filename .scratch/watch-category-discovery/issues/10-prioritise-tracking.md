# 10: Prioritise tracking under shared collection limits

**What to build:** Keep monitoring and potential-alert verification useful under shared limits while degrading discovery visibly and recovering without bursts.

**Blocked by:** [05: Track exact products and send qualified target alerts](05-track-exact-products.md)

**Status:** in-progress

**Assignee:** Codex implementer (isolated worktree)

**Parent:** [Trustworthy UK watch discovery alongside existing monitoring](../../../docs/specs/watch-category-discovery.md)

- [ ] Reuse native scheduler, execution, health and notification facilities with shared admission accounting for provider calls, detail/page requests, retries/fallbacks and applicable browser/AI/storage resources.
- [ ] Under explicitly supplied test limits, prioritise existing tracking and potential-alert verification, reduce discovery breadth first, and expose capped/blocked/failed/empty outcomes separately through API and coverage UI.
- [ ] Preserve aged last-good evidence without certifying semantic freshness from transport health; withhold alerts when required evidence cannot be refreshed.
- [ ] Exercise concurrent demand, exhaustion, partial failure, restart and resumption; no retry/fallback bypass or unbounded catch-up burst is allowed.
- [ ] Missing required operating policy keeps collection/activation gated. Do not invent numerical budgets, freshness schedules or a maintenance owner; present unmet prerequisites visibly.

## Verification and authority

Use the buyer-approved API plus normal execution seam, controlled external edges and isolated storage; assert observable behavior. Include persistence/API/UI behavior for this slice and keep legacy Watch semantics compatible. Source implementation and offline verification only: no live collection, production DB operations, account connections, activation, deployment, purchase, commit or push is authorised by this ticket.

## Dependency ready: 2026-10-27

Ticket05 is closed for its bounded offline scope after the
[tracking merger acceptance](../../../docs/testing/watch-tracking.md#merger-acceptance-2026-10-27).
This ticket is **READY and unclaimed**, reserved for parent dispatch. No 10
implementation or verification occurred in that acceptance. Shared admission,
prioritisation and operating-policy requirements above remain this ticket's work;
05's synthetic tracking policy supplies no production collection defaults.
