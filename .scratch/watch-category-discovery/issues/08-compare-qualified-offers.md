# 08: Compare qualified offers and explain price claims

**What to build:** Compare qualified offers with scoped current-best and dated observed-low explanations while withholding unsupported usual-price and savings claims.

**Blocked by:** [07: Correct identities without transferring misleading prices](07-correct-identities.md)

**Status:** in-progress — offline merger acceptance pending one type-check repair (2026-10-27)

**Assignee:** Codex implementer (isolated worktree)

**Parent:** [Trustworthy UK watch discovery alongside existing monitoring](../../../docs/specs/watch-category-discovery.md)

- [ ] Persist/version assessments and expose their cohort, method, evidence, exclusions, coverage, date/window and eligibility in API/feed details.
- [ ] Separate new/used, quantity and destination/eligibility cohorts and exclude auction bids from buy-now comparisons; rank only currently qualified comparable costs within declared coverage.
- [ ] Dated observed low comes only from qualifying retained observations within the stated window, not global/all-time claims; show missing coverage and history gaps.
- [ ] Usual price, personal eligible price and current-best/observed-low gates remain independent. Defer numerical estimator/window/sufficiency calibration until accepted empirical evidence; show unavailable usual price and no invented savings in the meantime.
- [ ] Corrections, stale evidence and policy changes invalidate derived comparisons; verify contradictory, sparse and duplicate evidence and the corresponding UI explanations.

## Verification and authority

Use the buyer-approved API plus normal execution seam, controlled external edges and isolated storage; assert observable behavior. Include persistence/API/UI behavior for this slice and keep legacy Watch semantics compatible. Source implementation and offline verification only: no live collection, production DB operations, account connections, activation, deployment, purchase, commit or push is authorised by this ticket.

## Merger review — 2026-10-27

Full source `81f18ab18d3417f17945ca46ec437e628689a892` was integrated with
`--no-ff` in `20728c299d2b8a8d217e80dd0dcd5fef6fa79ea1`, first parent
`52104eb3de8e4b7c6ff615763d8ecc3572e4e34d`. Source already contained that
integration tip; the merge was conflict-free and its tree matched source.

All **171 guarded workflows**, **37 contracts**, **25 frontend tests**, build,
13-file focused Ruff and three new external-edge coupon recovery/channel probes
pass. Changed-file Ruff has ten inherited diagnostics and zero added. Supplied
source/receipt hashes and all 77 original dirty-worktree hashes match. Actual
unchanged desktop/narrow/withdrawn screenshots were inspected and hash-verified.

**Remain open:** focused mypy fails on the new literal-list default factory at
`src/pricerecon/models/tracking.py:101`; the exact one-file, no-incremental
reproducer also fails. The parent owns this contained source repair. No product
source or existing assertions were changed by this review. See the
[merger receipt and retained failure](../../../docs/testing/watch-assessments.md#sole-merger-review--2026-10-27).
11 retains its existing owner; 12 remains blocked. Local commit/merge authority
is governed by the tracker README's later authorisation, superseding the older
issue-level no-commit sentence. Live/buyer/calibration/activation gates remain open.
