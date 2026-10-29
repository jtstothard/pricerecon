# 06: Show retained observations and acquisition gaps

**What to build:** Show auditable retained offer observations and explicit acquisition gaps rather than treating snapshots or alert events as price history.

**Blocked by:** [04: Show defensible UK delivered-cost scenarios](04-show-uk-delivered-cost.md)

**Status:** closed

**Assignee:** unclaimed

**Parent:** [Trustworthy UK watch discovery alongside existing monitoring](../../../docs/specs/watch-category-discovery.md)

- [x] Persist acquisition outcomes separately from filters/alerts and retain initial, unchanged, rising and falling observations with capture identity, availability, condition, quantity, destination, monetary/eligibility basis and policy versions.
- [x] Expose history and gaps through API and buyer history/evidence views, including partial/failing/cached sources and missing periods; last-good evidence retains its age and is not silently current.
- [x] Keep independent capture identity and derivation lineage so duplicate leads do not count as independent market observations.
- [x] Cold start shows limited history, unavailable usual price and no fabricated savings; synthetic fixture dates never become real retained longitudinal evidence.
- [x] Verify isolated additive migration preserves legacy rules/data without treating existing snapshots or sparse events as qualified new observations.

## Verification and authority

Use the buyer-approved API plus normal execution seam, controlled external edges and isolated storage; assert observable behavior. Include persistence/API/UI behavior for this slice and keep legacy Watch semantics compatible. Source implementation and offline verification only: no live collection, production DB operations, account connections, activation, deployment, purchase, commit or push is authorised by this ticket.

## Dependency ready: 2026-10-27

Ticket04 is closed for its offline scope after the
[FX repair merger acceptance](../../../docs/testing/watch-costs.md#fx-repair-merger-acceptance-2026-10-27).
This ticket is **READY and unclaimed**, reserved for parent dispatch. No
implementation, verification or claim for this ticket occurred in that merger;
its own checklist and separate live/buyer/activation gates remain open.

## Merger review — 2026-10-27: open for repair

Source `e47d47a` was merged without conflicts and with full history in
`bd5a3fb`. All **55 isolated workflows** passed, including the **48 baseline**;
focused Ruff/mypy passed and retained browser proof was inspected. Checked items
above reflect offline evidence only.

The independent-capture item remains unmet: a new extraction capture naming the
original capture in `derived_from` is still projected as `supported_at_capture`,
`unchanged`, with `duplicate_of: null`. The guarded application probe reproduces
this through normal acquisition plus the history API, without outgoing edges or
sends. See the [dated merger receipt and exact reproducer](../../../docs/testing/watch-history.md#merger-verification--2026-10-27).
No source repair occurred. Ticket06 stays open; ticket07 stays blocked by05/06.
Tickets05/09 remain parallel implementers. Collection stays staged and no real
longitudinal history, live or buyer acceptance is claimed.

## Lineage repair merger closure: 2026-10-27

**Closed for source implementation and deterministic offline verification.**
Repair source `238019d5f264c28f53b26557371bf0709af51b30` was merged with full
history and no conflicts in `6b93262cc11307d2ed78860add98924a3c8e7805`, onto
`a69c4eedec3630769416bfac2a3af552705d993b`. This preserves implementation
`a856c08` and interrupted-verification receipt `39a0687`; the earlier interrupted
combined run is not counted as acceptance.

All **83 current safe application workflows passed in one run**, including all
77 prior cases and six added lineage cases. The exact original merger probe,
unchanged, now passes: the derived copy is unqualified and names its original
owner, with the original offer and last-good age preserved. Direct/transitive,
unknown/cyclic/foreign, cached/replayed/cross-route, retained-cost-age and fresh
price/availability with reused definitions cases pass. Focused Ruff (seven files),
mypy (four source files) and diff checks pass. Unchanged frontend/browser/probe
files match 15 retained manifest entries; prior 25 frontend tests, production
build and browser receipts were reused without a new browser run.

See the [dated repair merger acceptance](../../../docs/testing/watch-history.md#lineage-repair-merger-acceptance-2026-10-27)
for commands, evidence and limits. Ticket05 is already closed, so **07 is READY
and unclaimed** for parent dispatch. Ticket09 remains separately open for its
receipt-provenance repair; its known failing acceptance probe was not run or
reclassified. Active 09/10 implementer worktrees and the original dirty parent
were not edited. No dependent implementation occurred. Collection remains staged;
source qualification, real longitudinal history/calibration, live/buyer,
operating and activation gates remain separate and open.
