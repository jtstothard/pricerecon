# Ticket07 correction implementation receipt — 2026-10-27

Offline implementation in `/Users/jay/.t3/worktrees/pricerecon/ticket07-corrections`,
branch `t3/ticket07-corrections`. The merger owns integration acceptance and
closure. This receipt establishes deterministic application/browser behaviour;
it grants no live, buyer, account, deployment or activation acceptance.

## Integration and isolation

Before source edits, fast-forwarded the isolated checkout to
`61ab075` on `integration/watch-category-discovery`. Confirmed ancestry of both
closed06 `fc328a995bded5c679d96bd1a8136d129147b6e4` and parent07's claim.
The original dirty parent was never edited; no sibling dirty source was read or
imported. Only its existing Python executable was used, with this worktree's
`src` and root on `PYTHONPATH`. Frontend dependencies are a symlink to integration's
existing `frontend/node_modules`; nothing was installed or downloaded.

During implementation, integration advanced to
`75f8a3a778e901e79f5ce1a1b76a26692d42a343`, including the parent's accepted09
provenance repair. Merged that committed tip with Git's temporary autostash of
this worker's tracked edits; it reapplied without conflicts or a retained stash.
No 09 provenance implementation or closure was performed by this worker. Its
committed receipt-proof checks remain intact. Ticket10 and migration 1.9 are
untouched. Final refresh confirmed this tip is included; the handoff reply records the completed source HEAD.

All application imports followed a frontend build. Every application workflow
uses the retained guarded harness: marked temporary SQLite, paused automatic
checks, controlled connector acquisition/time, captured notification transport,
blocked network/native curl/browser backend/subprocess edges. The actual UI
runs on unique loopback fixture port 8897 with an independent Chrome session and
loopback-only navigation. No production DB, network acquisition, credential,
account, activation, deployment, push, PR, install or delegation occurred.

## Implemented behaviour

`models/db/core/api/corrections.py` own the typed correction input, append-only
lineage, transactional withdrawal and read projections. The additive 2.0 migration
creates only the correction journal. Existing history, cost, coupon, tracking,
acquisition and dispatch owners remain in use.

GET/POST `/api/discovery/candidates/{candidate_id}/corrections/{configuration_id}`
expose original acquired configuration/evidence, cumulative intended values,
self-attributed actor/rationale, original/previous values, predecessor IDs,
timestamps, correction revision, corrected/disputed state and requalification
requirements. Writes compare expected correction revision, latest candidate
capture and observed configuration ID/revision under `BEGIN IMMEDIATE`.
Only the nine category identity fields are writable; numeric/categorical values,
empty attribution/rationale and unexpected fields are rejected. These records
are human intent, never acquired merchant, stock, price or cost proof.

The same transaction appends exact revision withdrawals using
`append_history_invalidation(connection, invalidation)` and calls
`invalidate_configuration_tracking(connection, configuration_id, reason)`.
Original source rows, observations, targets and accepted delivery records remain.
Configuration/binding/offer/comparison/cohort/cost/history/coupon and pending
alert eligibility withdraw together. A claimed or interrupted send raises an
understandable409 and rolls back the inserted correction and every dependent
change. Messages already accepted externally cannot be retracted.

Feed projections withhold public totals, selected bindings and comparison
cohorts. Cost API/feed responses explicitly mark `withdrawn`, remove usable
`total` and retain `historical_total`; original components remain inspectable.
History retains original configuration/value facts with exact withdrawal
references, without relabelling wrong-product prices. Coupon feed/history
consume the same withdrawals, retaining `historical_resulting_cost` separately.
After fresh base requalification, an older checkout receipt remains invalidated
with `receipt_predates_correction`; a new independently supported receipt can
qualify through 09's existing receipt/revision/policy checks.

Acquisition records its correction input revision before collection. Publication
rechecks it inside the acquisition's existing immediate transaction. Conflicting
captures are retained with `publication_state=withdrawn` and exact withdrawals,
so restart or replay cannot promote them. Requalification requires supported
compatible configuration and merchant selection, fresh corrected-field claims,
fresh direct temporal/cost evidence and 06's retained capture lineage. A new
extraction pointing to pre-correction capture roots remains withdrawn. No manual
edit manufactures any of this proof.

Targets retain their original subject and amount plus explicit intended values.
Fresh compatible evidence can assess that intent against a different exact
configuration, using category numeric/text equivalence. A new configuration gets
its own historical series and target baseline; correction/recovery alone sends
nothing. Later qualifying crossing and duplicate suppression use existing 05
logic. New alert payloads carry the actual newly qualified configuration ID.
A second correction withdraws both the original and observed descendant revisions.

The feed's focused `IdentityCorrection` component supplies field/value,
corrected/disputed state, actor and rationale controls. It shows original
acquired facts separately from intended values, lineage, retained targets and
what requires requalification. Old lead/cost results are labelled historical.

## Dated red/green evidence

Tests were added as successive vertical slices at the approved API and normal
execution seams. No internal correction method assertions, database inspection,
xfails, skipped assertions or weakened tests establish the outcomes.

| Slice | Observed red | Observed green |
| --- | --- | --- |
| Persistence and withdrawal | Correction POST returned 405 | Original evidence/target retained; feed/cost/history/coupon withdrawals survive application restart |
| Acquisition overlap | Pre-correction acquisition still exposed its old delivered amount | Transactional input revision withdraws capture; replay after restart remains withheld |
| Fresh requalification | Fresh configuration still reported requalification required | New supported history/assessment; old observations retain original identity and invalidated state |
| Repeat correction | Fresh descendant ID input rejected 422 | Original stable lineage accepts current observed ID/revision and withdraws descendants |
| Re-extraction | New extraction derived from old capture exposed old price | Retained lineage rejects pre-correction roots |
| Coupon boundary after 09 merge | Old receipt with advanced revision numbers returned `reproduced_at_observation`, no issues | Explicit correction withdrawal; fresh receipt positive control passes |
| Numeric identity | 36.0mm intent against 36mm evidence left target withheld | Category equivalence requalifies without rewriting human input |
| Alert subject | Fresh corrected price sent with original configuration ID | Captured payload names actual newly qualified configuration |
| Dispatch boundaries | New guarded workflows establish both boundary outcomes | Pending send withheld after correction/restart; claimed send returns 409 with unchanged history/cost/target/correction journal; accepted send retained |

The first broader pass exposed a regression in the new feed projection: an
unrelated pre-existing conflicting identity became unresolved. Restricted that
projection to withdrawn configurations. The existing shared-definition conflict
workflow passed again, then the full combined suite passed. An early in-flight
fixture omitted05's required above-target baseline and timed out; the fixture now
creates that baseline and has bounded barrier waits. No product bypass was added.

## Verification

Final combined guarded suite: **95 passed in 82.07s**. This includes every original
**83 application workflow**, **two committed 09 repair workflows** and **ten 07
correction workflows**. Frontend **25 tests passed**; TypeScript/Vite production
build passed, retaining the inherited chunk-size warning.

```sh
PATH=/Users/jay/.nvm/versions/node/v24.14.1/bin:/usr/bin:/bin npm --prefix frontend run build

env -i PATH=/Users/jay/.nvm/versions/node/v24.14.1/bin:/usr/bin:/bin \
  PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PWD/src:$PWD" \
  /Users/jay/.t3/worktrees/pricerecon/t3-7260bb2e/.venv/bin/python -m pytest -q \
  tests/test_cost_workflow.py tests/test_qualification_workflow.py \
  tests/test_discovery_workflow.py tests/test_monitoring_workflow.py \
  tests/test_history_workflow.py tests/test_coupon_workflow.py \
  tests/test_tracking_workflow.py tests/test_correction_workflow.py
```

Focused Ruff passed 19 Python source/test files. Focused mypy
`--follow-imports=silent` passed 13 source files, with inherited unused-override
notes only. `git diff --check` passed. Changed app/schema wiring files retain
exactly their base's five/two Ruff diagnostics respectively (compared by rule
and message), with no new diagnostics or suppressions. Frontend lint remains
blocked by inherited ESLint 10.12.0 missing `eslint.config.*`; no configuration or
dependencies were changed to hide it. Full repository pytest is outside the safe
suite because legacy fixtures can target configured DB/live edges.

Actual Chrome correction driver passed on the merged tree: fixture identity
before writes; keyboard target and correction submission; original mint versus
intended salmon; attribution/rationale/lineage; retained £60 intent; historical
cost/coupon/history withdrawals; reload persistence; stale editor 409; dispute and
resolution; 1280×900 and 375×812 with no horizontal overflow; unchanged legacy
intent/navigation; no browser errors. This is agent-operated UI proof, **not buyer
walkthrough acceptance**. Retained [receipt](artifacts/watch-corrections/receipt.json),
[desktop correction](artifacts/watch-corrections/desktop-correction.png),
[withdrawn history](artifacts/watch-corrections/desktop-history-withdrawn.png) and
[narrow correction](artifacts/watch-corrections/narrow-correction.png).

```sh
env -i PATH=/Users/jay/.nvm/versions/node/v24.14.1/bin:/usr/bin:/bin \
  PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PWD/src:$PWD" \
  /Users/jay/.t3/worktrees/pricerecon/t3-7260bb2e/.venv/bin/python \
  -m tests.monitoring.discovery_ui_server --corrections --port 8897

PATH=/Users/jay/.nvm/versions/node/v24.14.1/bin:$PATH \
  /Users/jay/.t3/worktrees/pricerecon/t3-7260bb2e/.venv/bin/python \
  -m tests.monitoring.discovery_browser_check --corrections --port 8897 \
  --artifacts /tmp/pricerecon-ticket07-browser-handoff
```

The installed agent-browser skill stub's `skills get core` command returns
`Unknown command: skills`; the retained compatible driver/installed Chrome worked
without installation. No preview tools were used for this edit. Owned fixture
servers and browser sessions were closed; each final server receipt reported
`blocked_edges=[]`, `notifications_sent=0`, `searches=3`, temporary storage true.
Captured-send workflows separately prove both positive and withheld sends.

## Remaining gates

Parent merger review/closure, buyer task interpretation, live source/offer/cost/
receipt evidence, source rights/retention, freshness/calibration, later 08 comparison
capabilities and 10 admission work remain separate. Existing comparisons and
coupons already consume correction withdrawals; this slice creates neither a
second comparison service nor a scheduler/queue/evidence platform. Migration 2.0
was exercised on temporary fresh/seeded legacy storage only. No production
migration, full-source coverage, empirical history, savings or live delivery
qualification is claimed.
