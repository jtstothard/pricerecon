# 01: Verify existing monitoring in isolation

**What to build:** A repeatable offline monitoring workflow that preserves existing saved searches, matching, schedules and notification settings while providing the accepted application-level verification seam.

**Blocked by:** None (can start immediately)

**Status:** in-progress

**Assignee:** Codex implementer (isolated worktree)

**Parent:** [Trustworthy UK watch discovery alongside existing monitoring](../../../docs/specs/watch-category-discovery.md)

- [x] Use explicitly temporary SQLite storage, controlled connector results and time, and captured notification transports through the existing API and normal execution entry point; demonstrate that startup jobs and real network/notification transports cannot escape isolation.
- [x] Seed representative legacy Watches and verify display title, fallback and source queries, synonym groups, exclusions, targets, enabled/disabled state, schedules and notification settings through observable behavior.
- [x] Exercise a normal check, partial-source failure and restart; retain existing notification behavior and last-good evidence without introducing duplicate alerts.
- [x] Keep this prerequisite refactor small and behavior-preserving; reuse existing execution, scheduling and storage facilities. Do not introduce a second scheduler or change the accepted query/matching ADR.

## Verification and authority

Use the buyer-approved API plus normal execution seam, controlled external edges and isolated storage; assert observable behavior. Include persistence/API/UI behavior for this slice and keep legacy Watch semantics compatible. Source implementation and offline verification only: no live collection, production DB operations, account connections, activation, deployment, purchase, commit or push is authorised by this ticket.

## Implementation receipt (2026-10-27)

Source/API gates above are verified in the isolated ticket branch; see
[isolated-monitoring receipt](../../../docs/testing/isolated-monitoring.md) for
red/green results, reproducible command and limitations. Both original strict
xfails are resolved, with 14 passing isolated workflow tests.

- [ ] Rendered browser/UI saved-search walkthrough (not exercised by this slice).

Local commits/merges were explicitly authorized for the continuation. Pushes,
PRs and live work remain unauthorized. The separate merger was subsequently
authorized to integrate this branch locally, as recorded below.
Overall ticket acceptance remains open pending rendered-UI verification.

## Integration receipt (2026-10-27)

Source review covered the implementation diff and
[isolated-monitoring receipt](../../../docs/testing/isolated-monitoring.md).
Before merging, both worktrees were clean; implementer branch
`t3/verify-monitoring-isolation` was at the requested HEAD
`9312871f269137d7b98ba7155d9523350e41e62e` and contained current integration tip
`85ca66d171375edc9dcf2ed87a54754ff344ec52` in its ancestry.

Merged without squash into `integration/watch-category-discovery` in
`a0e5c1a612252c61a62eabc7b56ebc3b3297ed85`. No conflicts or source/test edits
were required; the implementer history and assertions are preserved.

From `/Users/jay/.t3/worktrees/pricerecon/watch-category-integration`:

```sh
PYTHONDONTWRITEBYTECODE=1 \
PYTHONPATH=/Users/jay/.t3/worktrees/pricerecon/watch-category-integration/src \
  /Users/jay/.t3/worktrees/pricerecon/t3-7260bb2e/.venv/bin/python \
  -m pytest tests/test_monitoring_workflow.py -q
```

Result: **14 passed in 14.67s**, no xfails. Only the targeted module was collected;
each workflow uses the retained fresh-process isolation. No installs, network,
live collection or broad fixture suite were used. The original parent checkout
was left untouched; only its existing Python interpreter was used.

**Rendered UI gate: PENDING.** The parent is checking the browser. This merge
does not claim UI acceptance or close ticket 01. Tickets 02–12 remain blocked.
