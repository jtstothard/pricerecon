# Final watch discovery review and repairs

Dated 2026-10-27. Independent reviews examined the reviewed source snapshot
`c294a48cb561e61678ce416ead320e89d1e95b70` through technical delivery
`82afe34833ec4ade8e46d954291bee79dd4a6794`. Both refs and merge-base resolved,
the source diff was nonempty, and the exact 105-commit list was retained outside
the repository. The two reviewers worked independently; neither read the other's
report. Parent aggregated both axes and repaired the four contained findings.

## Standards

The [original Standards report](artifacts/watch-final-review/review-inputs/final-review-standards.md)
contains **two reproduced P2 documented-standard breaches**, with no additional
actionable Fowler smell judgement:

1. **Item isolation.** Complete claim/listing/report validation in Shopify and
   Browse escaped the per-item handler. A valid sibling was lost on an oversized
   numeric claim or dial text. The engineering standard requires isolation to the
   smallest failing unit. The handler now covers complete construction and commits
   the listing/report pair together only after both validate. Invalid items retain
   explicit receipt issues and partial coverage, without orphan listings.
2. **Credential links.** Exact query-name matching omitted client-secret and signed
   provider credential forms. Synthetic values survived persistence/API readback,
   contrary to the downstream-contamination boundary. Normalized OAuth/client,
   AWS/Google signature/credential/token and related known query forms are now
   rejected, including blank forms. Ordinary SKU/variant selectors remain usable;
   fragments remain stripped. This is a recognized URL-query boundary, not a
   universal secret scanner for arbitrary text.

Both are **fixed and regression-verified by the parent**. The original review is
preserved as a finding report; it was not rewritten as an independent post-fix pass.

## Spec

The [original Spec report](artifacts/watch-final-review/review-inputs/final-review-spec.md)
contains **one P1 and one P2**; no additional scope-creep finding:

1. **P1: lost conflicting coupon terms.** Same-selection acquisition merged claims
   and cost scenarios while dropping later coupon inputs. A valid-first report
   incorrectly produced GBP45.10 despite contradictory expired terms. Acquisition
   now retains distinct coupons for the existing coupon owner's conflict detection.
   Both report orders and a same-report conflict withhold the coupon payable;
   valid-only/identical controls retain GBP45.10 and the separate GBP50.10 base.
2. **P2: suppressed qualifying crossing.** Ordering used the oldest identity claim,
   so a reused still-valid manufacturer definition made a fresh GBP70.10→58.10
   crossing appear old. Ordering now uses qualified temporal price/availability
   plus existing payable-cost evidence. Definition/selection freshness remains a
   separate prerequisite. Fresh and reused-valid definitions each yield one target
   crossing; replay yields none extra, and stale/untimed definitions withhold.

Both are **fixed and regression-verified by the parent**. No synthetic price,
source report or history receipt establishes a live market fact.

Standards: **2 findings, worst P2, 2 fixed**. Spec: **2 findings, worst P1, 2 fixed**.
The axes remain separate; no cross-axis reranking was performed.

## Verification and preservation

The approved seam remains real API plus normal execution in fresh guarded children,
marked temporary SQLite, controlled HTTP/adapters/time and captured notification
transport. New adapter regressions use the real Shopify/Browse parsers and shared
HTTP admission; URL regressions assert persisted feed/claim pointers, and target/
coupon cases retain the real evaluators/dispatcher. No prior assertion was removed,
weakened, skipped or suppressed.

- Four red traces retain the original coupon, tracking, adapter and pointer failures.
- **24 focused regressions passed**: five coupon conflict/control cases; four fresh/
  reused/stale/untimed definition cases with replay; seven real-adapter numeric/text/
  final-report-bound/control cases; eight credential-query/SKU cases.
- Full cleared-environment suite: **215 passed in 198.98s**, all 191 retained plus 24
  regressions, no skips/xfails. Add `tests/test_final_review_workflow.py` to the
  fourteen-module command in [the workflow receipt](watch-workflow.md).
- **37 limiter/browser contracts passed**, ten inherited warnings. Uncached mypy
  passes the five changed application modules. Focused Ruff passes those five and
  both new test modules with **zero findings** against the same zero-finding baseline.
  Six formatted files pass Black; the acquisition hunk follows its existing style.
- All **seven original reviewer script runs** were repeated, with retained raw
  outputs and repaired expectations checked: valid siblings survive, credential
  pointers disappear, contradictory coupons withhold, and both crossing controls
  send exactly once. Every guarded receipt has zero escaped edges. Original red
  reports/scripts/results are preserved as review inputs, distinct from the new
  application/test checks.
- Frontend tree remains `08aa2e1fe99d9702e09ae087f8fcc1925452b547`. Prior 25 frontend
  tests/build and 19 inspected desktop/narrow screenshots are reused; no UI/response
  schema change. Existing ESLint missing-config, bundle and raw-log whitespace
  limitations remain recorded; no global lint/type claim is made.
- All **77** original dirty files retain their initial bytes and lengths. No live
  acquisition, credentials/accounts, production DB, install/download, push/PR,
  migration approval or activation occurred. Local commits remain authorized.

[Verification and hashes](artifacts/watch-final-review/verification.json) bind source,
new tests, original reports and raw red/green results. The buyer's already running
synthetic fixture is separate from these probes and was not mutated by reviewers
or regression tests. Its presented backend is `82afe34`, with the unchanged frontend
above; automated repair checks use the changed backend source.

**Technical review and its four repairs are complete. Actual buyer walkthrough
feedback remains pending; ticket12 stays open.** Live source/rights/retention,
Militado/Merkur evidence, real history/coupon/delivery, empirical calibration,
finite operating/physical-resource limits, maintenance ownership and activation
remain separate and unproven.

## Implementation checkout cleanup — 2026-10-27

After the repaired source committed as `73d7cd9`, removed all **19** isolated
implementation worktrees with Git. Each checkout was clean, its exact HEAD was an
integration ancestor, and ignored contents were limited to inspected build,
dependency and tool/Python cache paths. No branch reference or committed history
was deleted. The main checkout, original dirty checkout and integration checkout
remain; integration dependencies and the original interpreter remain available.
[Cleanup receipt](artifacts/watch-final-review/cleanup.json) records each identity.
All 77 original file hashes/lengths remain unchanged after cleanup.

The existing buyer fixture remains on 127.0.0.1:8892 with the same run identity,
temporary storage, paused automatic checks and zero escaped edges.
[Session receipt](artifacts/watch-final-review/buyer-session.json) records its
presented backend/frontend identity and explicitly pending feedback. No buyer
response has been received or invented. The buyer guide uses the retained
integration path. Ticket12 stays open solely for actual walkthrough feedback;
no autonomous source/review/cleanup work remains outstanding at this checkpoint.
