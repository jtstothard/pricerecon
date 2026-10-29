# 02: Discover candidates in an image-led feed

**What to build:** Discover wristwatch candidates independently of saved searches and display simultaneous illustrated candidates with editable preferences and honest uncertainty.

**Blocked by:** [01: Verify existing monitoring in isolation](01-verify-existing-monitoring.md)

**Status:** closed

**Assignee:** Codex merger (integration worktree)

**Parent:** [Trustworthy UK watch discovery alongside existing monitoring](../../../docs/specs/watch-category-discovery.md)

- [x] Run a deterministic category-discovery acquisition through existing connector/execution facilities and persist a candidate not named by any saved Watch, with discovery origin, timestamp and evidence lineage.
- [x] Expose candidates through the application API and image-led feed, including attribution and permitted provenance for images or clearly labelled original placeholders.
- [x] Persist editable compact/colourful/budget preferences, expose their interpretation, and distinguish hard constraints, soft preferences and unknown dimensions; example values do not become permanent personal defaults.
- [x] Keep unresolved candidates visible with explicit missing-data labels; do not infer verified delivered prices, usual prices, savings or bargain alerts from leads.
- [x] Verify preference changes and candidate persistence across reload through the accepted application seam and a focused UI check while legacy monitoring remains intact.

## Verification and authority

Implementation handoff (2026-10-27): source implementation and offline checks are
complete on isolated `t3/implement-ticket02-discovery`, pending the separate parent
merger's verification. See [the verification receipt](../../../docs/testing/watch-discovery.md)
for red/green gates, 20 workflows including all 15 legacy monitoring workflows,
25 frontend tests, build/type checks and actual desktop/narrow browser proof.
The user separately authorised local commits and integration merges. Acceptance
checkboxes and ticket closure were reserved for the parent merger and are resolved
by the dated receipt below; no activation or buyer acceptance is claimed.

## Resolution: 2026-10-27

Closed for this ticket's deterministic offline acceptance. Integration merge
`970bd255ab9f1caead2ed735be0f4ebe9e9ca4e6` preserves implementer HEAD
`2b8325c027566e945fd70287b1fc8953a2bd5939` and prior integration `15beae4`
as its two parents; no conflicts or application changes were needed.

The merger reran **20 isolated workflows** (5 discovery and all 15 legacy),
**25 frontend tests**, TypeScript/Vite build, focused Ruff and mypy on 10 source
files. All passed. The existing seven app/schema Ruff findings are unchanged;
ESLint remains blocked by the absent flat config. No checks were weakened.

Checklist evidence: independent acquisition/API persistence and query lineage;
editable unset-by-default hard/soft preferences, revision checks and unknown fits;
unresolved lead/cost/history/alert contracts; fresh-process persistence; and the
retained actual-browser keyboard/save/reload, five illustrated candidates,
expandable evidence, 375px no-overflow and legacy queue navigation proof. The
merger inspected both stored screenshots and the browser receipt/driver. The
merged tree is identical to the implementer's tree, with no substantive concern
requiring another browser run. See the [integration receipt](../../../docs/testing/watch-discovery.md#merger-verification-2026-10-27)
and its linked artifacts for details and limits.

Collection stays staged. Buyer acceptance, live rights/retention/cost/history,
operating limits and activation remain open. Ticket03 is claimed for the parent
continuation only; this merger did not implement it.

Use the buyer-approved API plus normal execution seam, controlled external edges and isolated storage; assert observable behavior. Include persistence/API/UI behavior for this slice and keep legacy Watch semantics compatible. Source implementation and offline verification only: no live collection, production DB operations, account connections, activation, deployment, purchase, commit or push is authorised by this ticket.
