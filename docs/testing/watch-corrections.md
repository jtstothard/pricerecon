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

## Merger disposition — 2026-10-27

**Ticket07 remains open for repair. Ticket08 remains blocked and unclaimed.**
The documented95 suite passes, but the additional application-seam probe below
demonstrates overbroad withdrawal and blocked requalification for a listing with
multiple exact configurations. No application repair was made by the merger.

### Identity, ancestry and review

Integration `/Users/jay/.t3/worktrees/pricerecon/watch-category-integration`,
branch `integration/watch-category-discovery`, was clean at requested
`75f8a3a778e901e79f5ce1a1b76a26692d42a343`. Source
`/Users/jay/.t3/worktrees/pricerecon/ticket07-corrections`, branch
`t3/ticket07-corrections`, was clean at requested
`89ebd79374a76c28c5cb5849a2f11a04c3085c91`, which already contained integration.
Explicit `git merge --no-ff --no-edit 89ebd79374a76c28c5cb5849a2f11a04c3085c91`
produced `233b3cc6d3f9c19eab8cd04c89309e0982a6a9b3`. Its first/second parents
are those exact integration/source commits. There were no conflicts; the merged
tree exactly matched source before merger evidence/tracker additions.

Read the spec/issue07, accepted identity/history/experience decisions, 05's
transaction/dispatch extension, 06's exact-revision/retained-capture repair,
and 09's accepted independent receipt/provenance repair. Reviewed source changes
through model, API, transaction, acquisition, projections, tracking, UI and guarded
workflows. The correction journal accepts only the nine category identity fields,
retains self-attributed actor/rationale and predecessor/revision history, and
compares expected correction/capture/configuration inputs under `BEGIN IMMEDIATE`.
Human intent does not edit acquired configuration, merchant, availability or cost
evidence. Historical rows retain their original identity/value associations.

The correction transaction uses the committed05 tracking invalidation and06 exact
history withdrawal owners. 09 coupon feed/history consumes those withdrawals and
rejects receipts predating a correction after base requalification. Correction UI
refreshes the history component using capture/correction revisions. Existing
comparison qualification/cohorts withdraw; this is not acceptance of future08
ranking/assessment capabilities or coupon-funded target alerts.

### Current verification and retained proof

Ran the exact cleared-environment eight-file pytest command in the implementation
verification section, from integration, using the existing parent Python and
installed dependencies: **95 passed in 83.56s**, with no skips/xfails. This includes
all85 current cases plus ten correction workflows. In particular, the in-flight
send returns409 with correction/history/target rollback; correction-first pending
send is withheld across restart; an overlapping stale acquisition retains its
outcome but withdraws current prices and cannot replay into eligibility. Fresh
independent evidence, descendant recorrection, numeric equivalence, coupon receipt
replay/fresh receipt and historical sent-record cases pass. Existing assertions
were not weakened or removed.

Focused Ruff passed the19 changed Python source/test files excluding app/schema;
mypy `--follow-imports=silent` passed13 source files with inherited unused-override
notes. Compared app/schema Ruff rule/message multisets against `75f8a3a`: exactly
the inherited five/two diagnostics, with no additions or suppressions. The new
merger probe also passes Ruff. `git diff --check` passes.

The source's **25 frontend tests**, TypeScript/Vite build and actual Chrome proof
are reused. Exact Git tree equality against `89ebd79` was confirmed for frontend,
correction browser driver, shared driver/server and retained browser artifacts.
Inspected all three actual desktop/narrow PNGs and their receipt; retained hashes
and focused/full results are in [the merger verification receipt](artifacts/watch-corrections/merger-verification.json).
No frontend tests, build or browser session were repeated. Existing ESLint10
missing-config blockage and large-chunk build warning remain as documented.
Agent-operated UI evidence is not buyer walkthrough acceptance.

### Reproduced gap: multi-configuration scope

Source review showed `compatible_fresh_candidate` requiring **every** configuration
in a candidate to match one correction's intended values, and `validate_publication`
withdrawing **every** configuration/binding/offer/cost in that candidate when it
fails. A legitimate listing can contain independently supported exact variants.
That was a concrete uncovered risk warranting this bounded probe.

[The retained probe](../../tests/monitoring/correction_merger_probe.py) uses the
existing marked temporary SQLite harness, normal acquisition and application API;
no private correction methods or database inspection establish its outcomes.
Both variants initially have supported configuration/binding/offer evidence and
verified GBP50.10 cost. It corrects only mint to salmon, then acquires fresh
supported salmon and blue reports. The blue variant is unrelated to that correction.

- Immediately after correction, blue correctly remains supported.
- After the fresh multi-variant capture, **salmon and blue both become unresolved**,
  both costs expose `withdrawn=true`, `total=null`, original GBP50.10 historical
  totals, and the correction remains `requalification=required`.
- These states persist after application restart. The failing assertion is
  `Fresh supported salmon configuration cannot requalify alongside unrelated blue`.
  [Failure receipt](artifacts/watch-corrections/merger-multi-configuration.json).
- The same fixture and evidence construction restricted to the corrected variant
  passes: fresh salmon is supported, requalification is
  `supported_by_fresh_evidence`, and the GBP50.10 public total is usable at
  observation. [Positive control](artifacts/watch-corrections/merger-single-control.json).

Exact commands, from integration (first exits1; control exits0):

```sh
env -i PATH=/Users/jay/.nvm/versions/node/v24.14.1/bin:/usr/bin:/bin \
  PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PWD/src:$PWD" \
  /Users/jay/.t3/worktrees/pricerecon/t3-7260bb2e/.venv/bin/python \
  -m tests.monitoring.correction_merger_probe \
  "$PWD/docs/testing/artifacts/watch-corrections/merger-multi-configuration.json"

env -i PATH=/Users/jay/.nvm/versions/node/v24.14.1/bin:/usr/bin:/bin \
  PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PWD/src:$PWD" \
  /Users/jay/.t3/worktrees/pricerecon/t3-7260bb2e/.venv/bin/python \
  -m tests.monitoring.correction_merger_probe \
  "$PWD/docs/testing/artifacts/watch-corrections/merger-single-control.json" --single
```

Both receipts report temporary storage, `blocked_edges=[]`, `notifications_sent=0`
and staged collection. This gap is excessive withdrawal and inability to requalify;
it does not demonstrate a false current payable, transferred historical price or
stale alert. Repair must scope qualification/publication to the actual corrected
configuration descendants, preserve unrelated exact variations, and keep all
passing acquisition/dispatch/coupon/history protections. The invalidation checklist
item remains open; checked items retain bounded offline proof only.

### Scope and remaining gates

Only integration received the local history-preserving merge, diagnostic probe,
receipts and tracker disposition. Source07, separate active10 and the original
dirty parent were not edited. No08 implementation or claim occurred. No installs,
downloads, external network/live collection, credentials/accounts, production DB,
activation/deploy, push, PR, delegation or unrelated cleanup occurred.

Collection remains staged. Buyer task interpretation, live/source mapping and
independent capture/receipt proof, access/rights/retention, freshness/calibration,
comparison and complete-workflow acceptance, operating limits and activation
remain separate gates. The passing deterministic suite does not close07 while
the retained additional acceptance probe fails.

## Isolated multi-configuration scope repair — 2026-10-27

Implementation branch `t3/repair-multiconfig-acceptance`, worktree
`/Users/jay/.t3/worktrees/pricerecon/t3-77103083`. The supplied clean isolated
checkout fast-forwarded from `ef86af6` to requested integration
`f561d76d55bf037ddec705ad488ebbc403934306` before edits; ancestry was checked.
Local source commit `37c29d3` was followed by conflict-free integration merge
`45be8902e8f1bf7279ef542b89642f082a6286f0`, incorporating ticket10 and merger
tip `f8ff7e5024401991ca33b9bf08468476dc708227`. Both required ancestors are
present. Only this worktree was edited; the integration checkout, original dirty
parent and other workers' checkouts were not changed. The merger retains07
acceptance and closure ownership. This repair does not close07 or repair10's
separately documented shared-admission gap.

### Scope and dependency rules

The first correction's observed capture fixes its actual selection membership.
Retained stable binding IDs connect those selections to later configuration
definitions. An unrelated selection whose values happen to match the intended
correction cannot qualify it or join its journal on recorrection. Selections
that had already left the definition before that capture are excluded.

Each qualification check now receives one exact configuration/binding/offer/cost
path. Publication and correction readback use the same freshness, acquisition
input, supported-selection, payable evidence and retained06 lineage checks.
Corrections made after acquisition began are checked per journal, rather than
using unrelated journals as a listing-wide veto. Partial acquisition, stale
retained cost roots and unsupported human merchant-selection claims still
withhold the affected path. Readback also checks exact dependency withdrawals,
including after restart.

Publication combines failures from all applicable journals before writing
withdrawals. Failed binding/offer/cost revisions withdraw together; a shared
configuration revision withdraws only when it has no surviving dependent offer.
The capture's existing `publication_state=withdrawn` remains an aggregate marker;
exact revision dependencies govern each surviving offer. A failed corrected
offer cannot poison an unrelated supported variation or a fresh independent
offer of the same definition.

Correction writes withdraw this candidate's actual historical original-identity
revisions and descendants. Other candidates' revisions of the global definition,
and different identities preceding the subject capture, remain intact. An
unrelated observed configuration cannot be attached to a journal: the API returns
409 without mutation. Dispute projection and coupon receipt correction boundaries
follow the same selection membership. Existing independent coupon receipt and
source-revision gates remain in place.

Tracking keeps its original subject, target, prices and accepted-send records.
Requalification can release intent created on either the original subject or an
actual descendant, provided the journal's intended values match. A successful
journal cannot release another journal's differently corrected target merely
because a descendant shares its original definition. The existing tracking
engine still separately qualifies observations and crossings. A current
assessment may acquire an additional withholding reason when its considered
offer withdraws; that does not rewrite the target or older identity observations.

### Observed red/green slices

Read the TDD skill and used the spec's already buyer-approved API plus normal
execution seams. The original ten correction workflows and every original95
assertion remain. Seventeen additional subprocess workflows use the existing
marked temporary-SQLite harness and controlled external edges.

| Slice | Observed red before its repair | Observed green |
| --- | --- | --- |
| Exact merger multi-configuration probe | Fresh salmon plus blue left correction `required`; both withdrew | Both supported; correction requalified across restart |
| Foreign observed descendant | Unrelated blue could enter mint's journal with201 |409, unchanged journal and blue evidence |
| Another candidate sharing a definition | Its exact configuration revision withdrew | Original history and supported revision survive restart |
| Converged definitions and recorrection | Shared-definition editor initially409; then unrelated blue descendant withdrew on next capture | Accepted actual descendant; unrelated selection stays supported through recorrection/restart |
| Unrelated coupon | Mint correction invalidated blue's reproduced receipt | Blue receipt/result unchanged across restart |
| Independent dispute | Blue dispute changed corrected mint to `conflicting` | Mint unresolved, blue conflicting |
| Target created on a descendant | Fresh recorrection left its invalidation reason set | Original descendant target preserved and released after qualification/restart |
| Independent journals sharing a definition | Successful mint-to-blue journal cleared blue-to-red target's invalidation | Only matching intent released; second remains withheld until its own evidence qualifies |
| Former definition member | Historical membership withdrew a selection already blue before the mint correction | Only current mint subject and its descendants affected |
| Earlier different identity on reused selection | Earlier blue observation invalidated by later mint correction | Blue history and target intent preserved |

The exact retained merger probe ran unmodified. Own dated
[red multi receipt](artifacts/watch-corrections/repair-scope-red-multi.json),
[green multi receipt](artifacts/watch-corrections/repair-scope-green-multi.json),
and [green single control](artifacts/watch-corrections/repair-scope-green-single.json)
retain its full API outcomes. The single control passed before and after repair.
Additional controls added after the initial scope fix pass for unrelated fresh
matching evidence versus stale corrected cost roots, same-definition multiple
offers with one stale payable dependency, multiple independent corrections and
target release across restart, partial acquisition, unsupported human selection
proof, and overlapping acquisition plus stale replay after restart. These are
reported as controls, not invented additional red observations.

### Verification commands and limits

From this worktree, `venv` temporarily symlinked the existing parent `.venv`;
`frontend/node_modules` symlinked integration's existing dependencies. No install
or download occurred. Exact final guarded combined command:

```sh
env -i PATH=/Users/jay/.nvm/versions/node/v24.14.1/bin:/usr/bin:/bin \
  PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PWD/src:$PWD" \
  /Users/jay/.t3/worktrees/pricerecon/t3-7260bb2e/.venv/bin/python -m pytest -q \
  tests/test_collection_workflow.py tests/test_monitoring_workflow.py \
  tests/test_discovery_workflow.py tests/test_qualification_workflow.py \
  tests/test_cost_workflow.py tests/test_history_workflow.py \
  tests/test_coupon_workflow.py tests/test_tracking_workflow.py \
  tests/test_correction_workflow.py
```

The first full run omitted Node from PATH: **122 passed, one failed in121.55s**.
The sole failure was the existing form-payload test raising
`FileNotFoundError: 'node'`; its retained
[failure log](artifacts/watch-corrections/repair-scope-path-failure.txt) is not
counted as green. The unchanged suite was rerun using the documented PATH above.

Final combined result on `45be890`: **123 passed in119.11s**, no skips/xfails.
This is every original95 workflow, ticket10's11 workflows and17 new correction
scope workflows. [Full green log](artifacts/watch-corrections/repair-scope-green-suite.txt)
and [verification manifest](artifacts/watch-corrections/repair-scope-verification.json)
bind the result to the tested source. Final `git merge --no-edit
integration/watch-category-discovery` reported `Already up to date`; ancestry
of both `f561d76` and latest `f8ff7e5` was rechecked. Focused Ruff, four-file mypy
and `git diff --check` pass. The local Python symlink was removed after checks;
the shared environment itself was not altered.

The exact probe commands use that same environment and Python executable:

```sh
python -m tests.monitoring.correction_merger_probe /tmp/ticket07-repair-green-multi.json
python -m tests.monitoring.correction_merger_probe /tmp/ticket07-repair-green-single.json --single
```

Focused Ruff checks the four touched source files and both test files; focused
mypy `--follow-imports=silent` checks those four source files, retaining inherited
unused-override notes. No new scheduler, queue, platform, migration, API or UI
shape was added. Ticket10's admitted-policy implementation and its separate
unaccepted shared-admission probes were preserved, not weakened or relabelled.

Frontend and retained browser-driver source exactly match merged integration.
Reuse the merger's25 frontend tests, build and actual desktop/narrow collection
and correction proof from `f8ff7e5`; no frontend/build/browser run was repeated.
The new scope behavior is proven at the API/execution seam, not by a new browser
walkthrough. The local unbuilt frontend warning is expected in API-only harness
processes; it does not supply UI evidence.

Collection stays staged. This is local offline source and deterministic evidence,
not merger acceptance, buyer walkthrough, live source/offer/history/receipt
qualification, calibrated freshness, complete source coverage or operating
activation. No external network/live collection, credentials/accounts, production
DB, activation/deploy, push, PR or delegation occurred. Existing09 receipt gates,
claimed-send rollback, pending-send withdrawal, immutable original facts and
history, and no stale-alert protections remain required by the combined suite.

## Scope repair merger review — 2026-10-27

**Ticket07 remains open for independent-target intent repair. Ticket08 remains
blocked and unclaimed.** The original multi-configuration defect is repaired,
but recorrection can overwrite a different journal's retained target intent.
The merger made no application repair and performed no 08 implementation.

### Identity, ancestry and review

Integration `/Users/jay/.t3/worktrees/pricerecon/watch-category-integration`,
branch `integration/watch-category-discovery`, was clean at requested
`f8ff7e5024401991ca33b9bf08468476dc708227`. Repair source
`/Users/jay/.t3/worktrees/pricerecon/t3-77103083`, branch
`t3/repair-multiconfig-acceptance`, was clean at requested
`430f4f07f6e591b90f9dfb233a33d9fdf86ac775`. Integration was already an ancestor
of source. Explicit `git merge --no-ff --no-edit 430f4f07f6e591b90f9dfb233a33d9fdf86ac775`
produced `7fcc3ea27e815ccd0922c3c4c1fe08c3d3724bc9`, with those exact
integration/source commits as first/second parents. No conflicts occurred;
the merge tree exactly matched source before these diagnostic/tracker additions.

Read the full 07 issue/spec, original merger finding, complete repair section,
committed 05 transaction/dispatch extension, 06 exact-revision/capture lineage and 09
independent checkout receipt/provenance contracts. Reviewed all four changed
application files and both changed test files against the integration tip.

- Frozen selection membership comes from the first correction's observed capture.
  Stable binding IDs connect actual descendants across configuration definitions;
  unrelated definitions that happen to match intended values cannot certify the
  journal or enter it as observed descendants. Earlier different identities and
  selections that had already left the subject definition remain separate.
- Publication checks exact configuration revision, binding revision, offer and
  its own payable evidence, correction-input revision, fresh corrected-field
  claims, acquisition completeness and retained 06 temporal/cost roots. Readback
  uses the same path checks plus dependency withdrawals. This is not an
  `all()`→`any()` substitution over the full listing. Failed offers withdraw
  independently; a shared definition survives when another dependent offer
  survives. Coupon boundaries follow retained selection membership; old receipts
  remain historical, not reusable current checkout proof.
- Pending-send exact revisions and claimed-send rollback still use 05's owners.
  The 123 suite retains the original overlap/replay, dispatch, coupon/history,
  multiple-correction and same-definition multiple-offer assertions. No existing
  assertion was removed, weakened, skipped or marked xfail.

### Passing current verification

The exact cleared-environment nine-file command in the repair section above ran
on the merged integration tree using existing dependencies: **123 passed in
117.72s**, no skips/xfails. This includes all 95 original workflows, 11 collection
workflows and 17 scope workflows. [Full log](artifacts/watch-corrections/repair-merger-suite.txt).

Both unmodified original merger commands now exit0, retaining
[multi-configuration](artifacts/watch-corrections/repair-merger-multi.json) and
[single-control](artifacts/watch-corrections/repair-merger-single.json) receipts.
Fresh supported salmon and unrelated blue remain supported across restart, and
the correction is `supported_by_fresh_evidence`. Their guards report temporary
storage, no blocked edges, no sends and staged collection.

A further [guarded sibling control](artifacts/watch-corrections/repair-merger-sibling-control.json)
starts separate mint/blue targets above £60, corrects mint to salmon, then
captures stale corrected cost lineage alongside a genuinely fresh blue price
crossing. The capture has aggregate `publication_state=withdrawn`; only the
corrected offer/cost withdraws. Blue sends exactly one captured webhook for its
own tracking/configuration ID at **£58.10**. Corrected intent stays withheld and
its journal stays `required` across restart; no corrected-offer send occurs.
This establishes that the aggregate marker does not suppress this valid sibling.

Focused Ruff passes the four changed application files, the two changed test
files and both merger probe modules (eight files). Focused mypy
`--follow-imports=silent` passes the four application files, with inherited
unused-override notes only. The new probe is formatted; `git diff --check` passes.

The repair changes no frontend, browser driver/server or browser artifacts.
Exact Git comparisons against `f8ff7e5` confirm equality for the frontend tree,
retained correction workflow/probe and browser inputs. Frontend tree remains
`fdcd941bb28fda22b7a8e2d9e7d606a6f9a7f7ec`. Reuse the existing 25 frontend
tests, production build and actual collection/correction desktop/narrow browser
proof retained in the [10 merger manifest](artifacts/watch-collection/merger-verification.json)
and [earlier 07 manifest](artifacts/watch-corrections/merger-verification.json).
No frontend/build/browser run or preview tool was used here. Existing ESLint10
missing-config blockage and large-chunk build warning remain documented.
This API-level repair review supplies no new buyer walkthrough acceptance.

### Remaining failure: recorrection overwrites independent target intent

[The retained probe](../../tests/monitoring/correction_repair_merger_probe.py)
uses only the existing guarded application API and normal acquisition seam.
It does not inspect the database or assert private correction functions.

1. Acquire independently supported mint (`a`) and blue (`b`) variants and create
   a separate £60 exact target for each.
2. Correct mint→blue in journal A and blue→red in journal B.
3. Acquire fresh supported blue/red evidence. Both journals requalify; API target
   intended values are `[blue, red]`.
4. Recorrect only journal A's actual blue descendant to gold, using A's original
   mint root, its current observed blue configuration/revision and expected
   correction revision 1. POST returns 201.
5. Read both targets, then restart the application and read them again.

**Expected:** target A follows gold; independent target B retains red, matching
its unchanged blue→red journal. **Observed:** intended dials become `[gold, gold]`
immediately and after restart, while journal B still says red. Both original
configuration IDs and £60 target amounts survive, but B's identity intent is
silently rewritten. [Full API receipt](artifacts/watch-corrections/repair-merger-independent-recorrection.json)
and [failing log](artifacts/watch-corrections/repair-merger-independent-recorrection.txt).

`db/corrections.py` lines 200–209 collect all historical descendant configuration
IDs, invalidate matching targets and replace every matching target's intended
values. Journal A's descendant IDs include blue, so the write also selects B's
original blue target. The publication-side intended-values check does not undo
this write. Target intent needs its own correct journal/selection association;
definition overlap alone cannot authorise reassignment. The probe exits1 with:

`Recorrecting mint->blue to gold rewrites independent blue->red target intent`

Its guards report temporary storage, `blocked_edges=[]`, `notifications_sent=0`
and staged collection. This directly demonstrates intent corruption. It does
not demonstrate an incorrect send or establish that later sends from the altered
target are safe. The passing 123 suite and sibling control do not close this gap.
The tracking-intent checklist item is therefore unchecked again; 07 stays open.

Exact additional commands, using the same cleared environment/Python as the
full suite (first exits1, control exits0):

```sh
env -i PATH=/Users/jay/.nvm/versions/node/v24.14.1/bin:/usr/bin:/bin \
  PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PWD/src:$PWD" \
  /Users/jay/.t3/worktrees/pricerecon/t3-7260bb2e/.venv/bin/python \
  -m tests.monitoring.correction_repair_merger_probe \
  "$PWD/docs/testing/artifacts/watch-corrections/repair-merger-independent-recorrection.json"

env -i PATH=/Users/jay/.nvm/versions/node/v24.14.1/bin:/usr/bin:/bin \
  PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PWD/src:$PWD" \
  /Users/jay/.t3/worktrees/pricerecon/t3-7260bb2e/.venv/bin/python \
  -m tests.monitoring.correction_repair_merger_probe \
  "$PWD/docs/testing/artifacts/watch-corrections/repair-merger-sibling-control.json" --sibling-control
```

### Scope and outstanding gates

[The merger manifest](artifacts/watch-corrections/repair-merger-verification.json)
binds the tested merge, exact outcomes and retained source hashes. Only
integration received the local history-preserving merge, diagnostic probe,
receipts and tracker disposition. Source repair, active10 and the original
dirty parent were not edited. No installs, downloads, external network/live
collection, credentials/accounts, production DB, activation/deploy, push, PR,
delegation or unrelated cleanup occurred.

Ticket10's existing independent-context/process shared-admission bypass probes
remain open for its owner. They were not run, repaired or reported passed; the 11
retained collection workflows in the 123 suite are not those additional probes.
Ticket08 remains blocked/unclaimed and was not implemented. Collection remains
staged. Buyer interpretation/walkthrough, live source/offer/history/cost/receipt
proof, source rights/retention, freshness/calibration, operating limits,
comparison/complete-workflow acceptance and activation remain separate gates.
