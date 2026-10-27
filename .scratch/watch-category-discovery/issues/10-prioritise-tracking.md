# 10: Prioritise tracking under shared collection limits

**What to build:** Keep monitoring and potential-alert verification useful under shared limits while degrading discovery visibly and recovering without bursts.

**Blocked by:** [05: Track exact products and send qualified target alerts](05-track-exact-products.md)

**Status:** open — denied Watch status/timestamp repair required 2026-10-27

**Assignee:** Codex implementer (isolated worktree)

**Parent:** [Trustworthy UK watch discovery alongside existing monitoring](../../../docs/specs/watch-category-discovery.md)

- [x] Reuse native scheduler, execution, health and notification facilities with shared admission accounting for provider calls, detail/page requests, retries/fallbacks and applicable browser/AI/storage resources. Unsupported lanes remain explicitly gated; physical resource controls remain live prerequisites.
- [ ] Under explicitly supplied test limits, prioritise existing tracking and potential-alert verification, reduce discovery breadth first, and expose capped/blocked/failed/empty outcomes separately through API and coverage UI.
- [ ] Preserve aged last-good evidence without certifying semantic freshness from transport health; withhold alerts when required evidence cannot be refreshed.
- [x] Exercise concurrent demand, exhaustion, partial failure, restart and resumption; no retry/fallback bypass or unbounded catch-up burst is allowed.
- [x] Missing required operating policy keeps collection/activation gated. Do not invent numerical budgets, freshness schedules or a maintenance owner; present unmet prerequisites visibly.

## Verification and authority

Use the buyer-approved API plus normal execution seam, controlled external edges and isolated storage; assert observable behavior. Include persistence/API/UI behavior for this slice and keep legacy Watch semantics compatible. Source implementation and offline verification only: no live collection, production DB operations, account connections, activation, deployment, purchase, commit or push is authorised by this ticket.

## Dependency ready: 2026-10-27

Ticket05 is closed for its bounded offline scope after the
[tracking merger acceptance](../../../docs/testing/watch-tracking.md#merger-acceptance-2026-10-27).
This ticket is **READY and unclaimed**, reserved for parent dispatch. No 10
implementation or verification occurred in that acceptance. Shared admission,
prioritisation and operating-policy requirements above remain this ticket's work;
05's synthetic tracking policy supplies no production collection defaults.


## Merger disposition — 2026-10-27

**10 remains open; 11 remains blocked and unclaimed.** Source `072a2f8` was
refreshed against clean integration `f561d76` in the existing source checkout,
resolving four actual conflicts while retaining 07 publication/invalidation and
10 admission wiring. Refresh merge `fd02625` was merged into integration with
`--no-ff` as `5cca859` (first parent `f561d76`). Full history is retained.

All **106 combined guarded workflows** pass, including all 96 source cases and
07's ten cases. The 37 limiter/browser contracts, focused Ruff/mypy, repeated
25 frontend tests/build and actual desktop/narrow collection/correction UI proof
pass. These checks do not establish complete shared admission.

Three additional controlled probes fail: after a one-request global/provider grant
is exhausted, an independent API context and registered scheduler callback each
send again without debiting it. A fresh process with the same marked temporary DB
also sends with no policy context despite the persisted active exhausted grant.
The outside caller's collection status reports `operating_policy_required` while
its controlled transport ran. Persisted usage and attempts remain unchanged.
No live transport, real credentials, escaped edges or notifications are involved.

`current_policy()` has only a ContextVar lookup; policy-less acquisition constructs
`budget=None`. This is optional per-context participation, not complete shared
admission. Repair must apply/resolve the applicable finite durable grant (or
withhold ambiguous callers before work) across API/scheduler/process entry points,
while preserving saved monitoring intent and the passing no-grant legacy control.
No architecture was rejected solely on inspection; actual transport/API probes
establish this acceptance gap. No repair was implemented by the merger.

See the [dated merger receipt, results, prerequisites and reproducer](../../../docs/testing/watch-collection.md#merger-disposition--2026-10-27).
The redirect control caps the second actual edge, and the retained suite proves
supplied-context accounting/priority/storage/withholding/recovery behavior. The
unchecked shared-admission and bypass requirements remain unmet. Unsupported
browser/AI lanes and physical disk/log/backup/retention controls remain prerequisites,
not zero-cost resources or production operating acceptance. 07's separate
multi-configuration gap remains open and was neither fixed nor used to excuse
these collection failures. No 11 work, live operation, activation or push occurred.

## Shared-grant repair merger review — 2026-10-27

The original three grant bypasses are repaired. Clean source `2ac8eff` was
refreshed with integration `c84f1f1` as `f61bc3c`, then merged with `--no-ff`
as `906ef0f` without conflicts. The parent's 07 repair, its three tests and
receipts are unchanged. All **148 guarded workflows** pass in one invocation,
as do **37 contracts**, focused types and zero-added-finding lint checks.
Independent API/scheduler/fresh-process probes and no-grant/redirect controls
pass. Concurrent processes, None/empty contexts, immutable scopes, first-denial
registration, expiry, damaged/ambiguous/removed payloads and migration are covered.

**10 remains open; 11 remains blocked and unclaimed.** A separate normal Watch
API probe advances the controlled clock after exhausting a one-request grant.
The next request sends nothing, preserves rows and records the correct capped,
unrefreshed attempt with the old last-good time. However, its API envelope says
`status=completed`, `success=true`, and advances `last_check_at` from 12:00 to 13:00.
Zero-first elapsed/provider grants also report completed/success and change a
null timestamp to 13:00 despite no acquisition. The expired-policy control returns
blocked and retains 12:00 correctly. These three failing acceptance cases are
retained as failures, outside the 148 passing workflows.

Acquisition denial is retained in `acquisition_outcomes`, but only a later
persistence denial sets the `collection_state` consumed by the new API response
branch. This leaves the API's normal completed path and both timestamp updates
reachable after these all-source caps. Repair must carry actual acquisition
denial through the Watch result and preserve the timestamp without weakening
legacy successful/empty/partial behavior or fabricating a refreshed assessment.
The merger made no application-source repair.

See the [repair merger receipt and exact reproducer](../../../docs/testing/watch-collection.md#shared-grant-repair-merger-review--2026-10-27).
The two unchecked checklist items retain this gap; live/browser/AI/physical
storage/retention/source-rights/buyer gates remain separate. Ticket08 stays with
its active owner; no 08 or 11 implementation occurred. Collection remains staged.
