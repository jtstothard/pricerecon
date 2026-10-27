# Final SPEC review supporting evidence

Reviewed existing clean integration checkout `/Users/jay/.t3/worktrees/pricerecon/watch-category-integration`, branch `integration/watch-category-discovery`, at `82afe34833ec4ade8e46d954291bee79dd4a6794`. Base and verified merge-base: `c294a48cb561e61678ce416ead320e89d1e95b70`. The source/frontend diff is nonempty. Observed `git log BASE..HEAD --oneline` exactly matches the supplied `final-review-commits.txt`; retained observed list is `final-spec-observed-commits.txt` beside this file.

Only the SPEC axis was reviewed. Inputs were the implementation spec, tracker README and all twelve issues, accepted proof protocol, relevant closed planning resolutions/contracts, substantive implementation/frontend/contracts and tests. Testing receipts served as evidence pointers. No other reviewer's report was read. Existing suite/build/browser results were not rerun or promoted to independent proof. The buyer fixture on port 8892 was not accessed.

## Probe isolation

Each case ran in a fresh child process using the existing interpreter only:

```sh
env -i PATH=/usr/bin:/bin PYTHONDONTWRITEBYTECODE=1 \
  PYTHONPATH=/Users/jay/.t3/worktrees/pricerecon/watch-category-integration/src:/Users/jay/.t3/worktrees/pricerecon/watch-category-integration \
  /Users/jay/.t3/worktrees/pricerecon/t3-7260bb2e/.venv/bin/python \
  /Users/jay/.scratch/watch-category-discovery-implementation/final-spec-coupon-probe.py valid-first
```

Both probe scripts create their own `pricerecon-offline-final-spec-*` directory with `.offline-monitoring` marker `ticket01-test-storage`, then enter `tests/monitoring/harness.py` with that storage root. The harness clears the environment, restricts SQLite to that temporary database, blocks external sockets/native curl/real HTTP/browser/subprocess edges, disables automatic scheduler work, controls time/connectors and captures notification transports. Original synthetic fixtures supply all amounts/dimensions/timestamps. Temporary databases are not retained. All six final runs exited zero; every receipt records `blocked_edges=[]`. Coupon cases sent nothing; only the expected tracking positive control had one captured send.

## 1. Same-selection coupon conflict discarded

Source: `src/pricerecon/core/acquisition.py:315-329`. The existing merge handles matching `(merchant_key, product_id, variation_id)` reports by copying the first report and extending costs and field claims. It does not extend `coupons`. Consequently downstream `source_conflicts` detection in `core/discovery.py` never receives coupons from subsequent reports.

Probe: [final-spec-coupon-probe.py](final-spec-coupon-probe.py). Uses retained original `reproduced_report` fixture and normal acquisition, persistence, discovery feed and coupon-history API. A second report for the identical merchant selection changes its same-key coupon terms to an exclusive expiry at the controlled current time, leaving both competing inputs available to acquisition.

- [valid-first](final-spec-coupon-valid-first.txt): two contradictory reports produce `reproduced_at_observation`, issues `[]`, zero source conflicts, verified resulting GBP45.10. Only the first terms survive in feed/history.
- [expired-first](final-spec-coupon-expired-first.txt): reversing only input order yields `invalidated`, no resulting payable.
- [expired-only](final-spec-coupon-expired-only.txt): invalidated, no payable.
- [same-report-conflict](final-spec-coupon-same-report-conflict.txt): putting the same two coupons in one report yields `invalidated`, `conflicting_coupon_inputs`, one retained source conflict and no payable.

All cases retain the ordinary no-coupon GBP50.10. This is observed evidence loss and order-dependent false verification, not a claim of an observed external coupon or alert. Spec lines 83-84 require conflict-free verified totals and separation/retention of terms, validity and reproduction. Issue09 also requires derived applications/totals to invalidate when their terms evidence changes.

## 2. Retained manufacturer definition suppresses fresh crossing

Source: `src/pricerecon/core/exact_tracking.py:284-295` and `332-334`. `evidence_time()` takes the minimum timestamp across all offer evidence, including manufacturer configuration claims, and `decide()` rejects a timestamp no later than the previous one. This conflates the oldest supporting definition with the acquisition time of changed price/availability/cost.

Probe: [final-spec-tracking-probe.py](final-spec-tracking-probe.py). Uses original direct-capture history fixture, normal acquisition, exact-tracking API, controlled explicit two-hour freshness policy and captured webhook configuration. Initial delivered GBP70.10 establishes the above-GBP60 baseline at 12:00. At 12:30, fresh independent selected-price, availability and complete-cost evidence yields GBP58.10. Only manufacturer configuration evidence is retained from 12:00, still valid under policy. No source failure, recovery, cache replay or correction occurs.

- [retained-definition](final-spec-tracking-retained-definition.txt): API assessment is `eligible` at GBP58.10 but reason is `duplicate_or_older_evidence`; zero events and zero captured sends. History independently exposes the new point as `supported_at_capture`, `decreased`.
- [all-fresh control](final-spec-tracking-all-fresh.txt): same prices, times, intent and policy, with manufacturer claims also freshly observed, produces `target_crossing`, one event and one captured send.

The timestamp used to order temporal offer observations must not be pinned by a reusable definition. Existing freshness/lineage gates still need to apply independently. Spec line88 requires an alert on a qualifying crossing and suppression of the same offer/price, not suppression of a new qualified price merely because its identity definition is unchanged.

## Preservation and limits

No repository edits, commits, integration changes, installs, downloads, production DB, live acquisition, credentials, browser activity, deployment, activation or cleanup of other worktrees occurred. `git status --porcelain=v1` remained empty after probes and HEAD remained pinned. Only new review files outside the repository were written. Protected original worktree was used solely for its existing Python interpreter. Findings do not reopen separately authorized buyer/live/source-rights/calibration/operating/activation gates or reclassify known ESLint, legacy Ruff/types, chunk or raw-log-whitespace limitations.
