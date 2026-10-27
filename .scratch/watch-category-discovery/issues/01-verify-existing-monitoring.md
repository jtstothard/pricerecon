# 01: Verify existing monitoring in isolation

**What to build:** A repeatable offline monitoring workflow that preserves existing saved searches, matching, schedules and notification settings while providing the accepted application-level verification seam.

**Blocked by:** None (can start immediately)

**Status:** in-progress

**Assignee:** Codex implementer (isolated worktree)

**Parent:** [Trustworthy UK watch discovery alongside existing monitoring](../../../docs/specs/watch-category-discovery.md)

- [ ] Use explicitly temporary SQLite storage, controlled connector results and time, and captured notification transports through the existing API and normal execution entry point; demonstrate that startup jobs and real network/notification transports cannot escape isolation.
- [ ] Seed representative legacy Watches and verify display title, fallback and source queries, synonym groups, exclusions, targets, enabled/disabled state, schedules and notification settings through observable behavior.
- [ ] Exercise a normal check, partial-source failure and restart; retain existing notification behavior and last-good evidence without introducing duplicate alerts.
- [ ] Keep this prerequisite refactor small and behavior-preserving; reuse existing execution, scheduling and storage facilities. Do not introduce a second scheduler or change the accepted query/matching ADR.

## Verification and authority

Use the buyer-approved API plus normal execution seam, controlled external edges and isolated storage; assert observable behavior. Include persistence/API/UI behavior for this slice and keep legacy Watch semantics compatible. Source implementation and offline verification only: no live collection, production DB operations, account connections, activation, deployment, purchase, commit or push is authorised by this ticket.
