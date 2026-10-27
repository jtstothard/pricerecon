# 07: Correct identities without transferring misleading prices

**What to build:** Let the buyer correct identity fields while retaining original evidence and tracking intent and withdrawing affected prices, history qualification and alerts.

**Blocked by:** [05: Track exact products and send qualified target alerts](05-track-exact-products.md), [06: Show retained observations and acquisition gaps](06-show-observation-history.md)

**Status:** closed

**Assignee:** Codex (integration repair)

**Parent:** [Trustworthy UK watch discovery alongside existing monitoring](../../../docs/specs/watch-category-discovery.md)

- [x] Provide a persistent field/value correction interaction through the feed/API, with original evidence, attribution, correction lineage and current disputed/resolved state.
- [x] Invalidate affected bindings, cohorts, cost scenarios, history qualification and pending alert eligibility; never transfer a wrong configuration’s historical prices to the corrected product.
- [x] Retain tracking intent and explain what needs requalification; historical assessments remain clearly historical instead of displaying their old bargain claims as current.
- [x] Exercise overlap between acquisition, correction and alert dispatch, plus restart; stale assessment/evidence versions cannot publish as current or trigger a qualifying alert.
- [x] Establish observable invalidation behavior that subsequent comparison and coupon slices must extend to their derived assessments; verify the correction workflow in the browser.

## Verification and authority

Use the buyer-approved API plus normal execution seam, controlled external edges and isolated storage; assert observable behavior. Include persistence/API/UI behavior for this slice and keep legacy Watch semantics compatible. Source implementation and offline verification only: no live collection, production DB operations, account connections, activation, deployment, purchase, commit or push is authorised by this ticket.

## Dependencies ready: 2026-10-27

Ticket05 is closed for its offline scope and ticket06's lineage repair is now
accepted in the [dated merger receipt](../../../docs/testing/watch-history.md#lineage-repair-merger-acceptance-2026-10-27).
This ticket is **READY and unclaimed**, reserved for parent dispatch. No 07
implementation, verification or claim occurred in that merger. Its checklist,
browser correction workflow and separate live/buyer/activation gates remain open.

## Isolated implementation handoff — 2026-10-27

Implementation and offline verification are recorded in
[the dated correction receipt](../../../docs/testing/watch-corrections.md), on
`t3/ticket07-corrections` at
`/Users/jay/.t3/worktrees/pricerecon/ticket07-corrections`.
All original 83 workflows remain green; the merged safe suite has 95 passes,
including committed 09 repair checks and ten correction workflows. Actual guarded
Chrome correction proof is retained with the receipt. Parent merger acceptance
and closure remain pending; this worker does not close 07 or sibling tickets.

## Merger disposition — 2026-10-27

**07 stays open for repair; 08 stays blocked and unclaimed.** Clean source
`89ebd79374a76c28c5cb5849a2f11a04c3085c91` was merged without conflicts using
`--no-ff` in `233b3cc6d3f9c19eab8cd04c89309e0982a6a9b3`, preserving requested
integration `75f8a3a778e901e79f5ce1a1b76a26692d42a343` as first parent.
All **95 documented safe workflows passed in 83.56s**, with focused Ruff/mypy
and no new app/schema lint diagnostics. Source's unchanged 25 frontend tests,
build and actual desktop/narrow browser evidence were inspected and reused.

The additional guarded API/execution probe reproduces a scope failure. One
listing initially has independently supported **mint and blue** configurations
and verified GBP50.10 costs. Correct only mint to salmon: blue initially remains
supported. Acquire fresh supported **salmon and blue** evidence: both configurations
become unresolved and both costs withdrawn; the correction remains `required`,
including after restart. The same fixture with only mint/salmon passes fresh
requalification. The unchecked invalidation item therefore remains unmet for
multi-configuration listings. This is excessive withdrawal and blocked
requalification, not a demonstrated false payable or stale send.

See the [dated merger receipt and exact reproducer](../../../docs/testing/watch-corrections.md#merger-disposition--2026-10-27).
Repair must scope requalification and publication withdrawal to the corrected
configuration's actual descendants, preserve unrelated supported variations,
and retain the passing race/lineage/coupon protections. No application repair,
08 implementation or acceptance, or 10 work was performed by the merger.
Collection remains staged; live/buyer/source-rights/freshness/activation gates
remain open. Checked items record bounded offline evidence, not full07 acceptance.

## Scope repair merger disposition — 2026-10-27

**07 remains open for independent-target intent repair; 08 remains blocked and
unclaimed.** Clean source `430f4f07f6e591b90f9dfb233a33d9fdf86ac775` was merged
without conflicts using `--no-ff` as `7fcc3ea27e815ccd0922c3c4c1fe08c3d3724bc9`,
with requested integration `f8ff7e5024401991ca33b9bf08468476dc708227` as first
parent. All **123 documented guarded workflows passed in 117.72s**, including
95 original, 11 collection and 17 scope workflows. The unchanged original
multi-configuration probe and single control now pass. A further control proves
a valid blue sibling can send one captured qualifying crossing while the
corrected stale offer remains withdrawn and its target withheld across restart.
Focused Ruff/mypy and diff checks pass; unchanged frontend/browser proof is reused.

An additional API/execution probe finds a remaining failure. Create separate £60
targets for mint and blue, correct mint→blue and blue→red in independent journals,
then acquire fresh blue/red evidence so both journals requalify. Recorrect only
the first journal's actual blue descendant to gold. **Both targets' intended
dials become gold**, although the second journal still says red; the mismatch
persists after restart. Original subject IDs and £60 amounts remain, and this
probe sends nothing. The tracking-intent item is unchecked because independent
intent was overwritten. Passing the existing suite does not close this gap or
prove the resulting altered target safe for later sends.

The write scopes target invalidation/reassignment by the journal's historical
configuration IDs, which include blue after convergence; that also selects the
independent blue→red target. Target ownership must remain tied to its actual
correction intent, rather than every target whose original definition appears
among another journal's descendants. Merger made no application repair.

See [the dated scope repair review and exact reproducer](../../../docs/testing/watch-corrections.md#scope-repair-merger-review--2026-10-27).
Ticket10's existing shared-admission failures remain open for its owner and were
neither rerun nor reclassified. No 08 implementation or claim occurred. Collection
stays staged; live, buyer, source-rights, freshness and activation gates stay open.

## Final offline acceptance — 2026-10-27

The parent repaired the independent-target intent finding by binding target updates
to original captured selection revisions. All126 guarded workflows pass, including
all123 retained cases, original/reverse journal orders, descendant targets, older
identity reuse and restart. The valid-sibling alert control also passes.
See [the final repair receipt](../../../docs/testing/watch-corrections.md#parent-target-ownership-repair-and-acceptance--2026-10-27).
Previous open dispositions above remain historical; this resolution closes07 for
offline scope only and releases08. Buyer/live/operating gates remain separate.
