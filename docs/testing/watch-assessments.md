# Ticket08 scoped price assessments — offline receipt

Dated **2026-10-27**. Branch `t3/ticket08-price-assessments`, worktree
`/Users/jay/.t3/worktrees/pricerecon/t3-e29f7fa4`. The integration merger owns
acceptance and ticket closure. This is controlled implementation evidence, not
buyer acceptance, live merchant/history/coupon proof or production calibration.

Before edits the branch fast-forwarded to integration
`c84f1f166a3bd6688cbfbafc6fe350e7a80f987c`; ancestry was confirmed. The original
dirty parent, integration checkout and other workers were not edited. The
existing parent Python environment was reused with this checkout's `src` and root
on `PYTHONPATH`. Frontend dependencies are an ignored symlink to integration's
installed dependencies. Frontend was built before application imports.

## Implemented contract

- Migration **2.2** adds append-only scoped assessment revisions and the active
  supplied comparison-policy fingerprint. It leaves ticket10's **2.1** reservation
  and ticket07's captured-selection ownership repair intact.
- `core/comparisons.py` owns comparable cohorts and price claims. It reuses exact
  tracking's shared scenario qualification; comparison needs no target or invented
  estimator. SQLite assessments consume the retained history ledger, acquisition
  outcomes, exact dependencies and correction withdrawals in a transaction.
- `execute_discovery(..., comparison_policy=...)` accepts an explicit programmatic
  policy with evidence age, conditions, quantity, destination/payment eligibility,
  sources, retained dates and evidence-policy versions. HTTP writes cannot activate
  collection or supply execution policy. No production values are invented.
- Current best ranks qualified fresh available standalone buy-now payable totals
  within the declared checked scope. Cohorts preserve exact configuration values,
  condition/details, quantity, destination, dispatch/payment/currency context and
  ordinary public eligibility. Exact selected context and dependency revisions
  remain on each winning path. Used, auctions and other purchase commitments are
  separate. Unknown, conditional, invalidated, duplicate and contradictory paths
  cannot win. A disputed sibling cannot gate or certify another configuration.
- Dated low is the minimum of qualifying, nonduplicated retained temporal
  observations within supplied dates, clipped to assessment time. It discloses
  count, dates, coverage/gaps, source attempts, exclusions, synthetic status,
  method and policy versions. Recapture does not erase earlier direct receipts.
  Correction/policy withdrawal invalidates their use; expiration alone does not
  erase an honestly dated historical quote. No all-time/ordinary-price claim,
  first-capture saving, RRP saving, estimator or numerical window was added.
- Usual obtainable price, personal price and savings remain independently
  unavailable. Current/low output can qualify without those gates.
- `GET /api/discovery/assessments` and candidate `price_assessments` retain old
  versions. Read projections mark superseded, recaptured, stale, corrected or
  changed-policy results historical/invalidated without silently recomputing a
  new winner. Feed assessment projection shares its SQLite read snapshot.
- `TrackingPolicy.allowed_scenario_kinds` defaults to `public_no_coupon`. Explicit
  opt-in can select the coupon owner's independently reproduced `public_coupon`
  payable through the same exact-identity/context/freshness/withdrawal gates.
  No coupon arithmetic, collector, scheduler or parallel alert service was added.
  App-conditional, personal, payment, cashback, advertised and altered-receipt
  evidence cannot enter public comparison. The no-coupon base stays distinct.
- Coupon-target decisions retain coupon revision/full receipt fingerprint,
  resulting scenario and base scenario revision. Pending recovery and the existing
  atomic channel claim recheck these dependencies. Shared offer/buyer-context
  crossing and dedup state spans no-code/code alternatives and restart. Alerts
  explain the required public code and ordinary base; existing no-code behavior
  remains covered.
- Buyer details use one `PriceAssessments` component with scoped current/low,
  historical states, dates/counts, independent unavailable outputs and expandable
  provenance, cohort, exclusions and gaps. The main public price is explicitly
  labelled no coupon.

## TDD and reproducibility

Used `/Users/jay/.agents/skills/tdd/SKILL.md` at the already approved API plus
normal execution seam. `MonitoringHarness` controls acquisition/time, marked
temporary SQLite, paused automatic checks and captured notification transports;
its audit/transport guards block outgoing edges. New tests do not query private
storage to establish buyer behavior.

Retained red traces: missing assessment contract, staleness left current,
missing coupon policy opt-in, and contradictory duplicate routes selecting a
winner. Each corresponding workflow passed after implementation. The initial
combined safe suite passed **130** (all **126** retained workflows plus the first
four new workflows). Later checks add independent sibling paths, contradictions,
restricted coupons, changed receipt/terms pending invalidation, cohort separation,
fresh-process restart/dedup, and duplicate/failed acquisition coverage.

Commands run from this worktree, with no installation:

```sh
PATH=/Users/jay/.nvm/versions/node/v24.14.1/bin:$PATH npm --prefix frontend run build
PATH=/Users/jay/.nvm/versions/node/v24.14.1/bin:$PATH npm --prefix frontend test -- --run

env -i PATH=/Users/jay/.nvm/versions/node/v24.14.1/bin:/usr/bin:/bin \
  PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PWD/src:$PWD" \
  /Users/jay/.t3/worktrees/pricerecon/t3-7260bb2e/.venv/bin/python -m pytest -q \
  tests/test_monitoring_workflow.py tests/test_discovery_workflow.py \
  tests/test_qualification_workflow.py tests/test_cost_workflow.py \
  tests/test_tracking_workflow.py tests/test_history_workflow.py \
  tests/test_coupon_workflow.py tests/test_collection_workflow.py \
  tests/test_correction_workflow.py tests/test_correction_target_ownership.py \
  tests/test_shared_grant_workflow.py tests/test_assessment_workflow.py
```

The same interpreter ran focused Ruff, Black and mypy checks. Full repository
pytest is outside the retained safe boundary: legacy fixtures can open configured
storage or live edges. No assertion was weakened, suppressed, skipped or xfailed.

Actual browser proof uses the existing guarded fixture/driver, unique loopback
port **8918**, an independent agent-browser session and installed Chrome. The
agent-browser skill was read; installed CLI lacks `skills get core` (reported
`Unknown command: skills`), so its installed `--help` and retained driver were
used. No browser installation or preview tool was used.

```sh
# Server: cleared environment and the same PYTHONPATH/Python as above.
python -m tests.monitoring.discovery_ui_server --assessments --port 8918
# Driver PATH additionally includes /Users/jay/Library/pnpm.
python -m tests.monitoring.discovery_browser_check --assessments --port 8918 \
  --artifacts "$PWD/docs/testing/artifacts/watch-assessments/browser"
```

Desktop **1280×900** and narrow **375×812** checks passed: scoped £45.10 coupon
payable against separate £50.10 base, dated low, historical revision, unchecked
source, unavailable usual/personal/savings, expandable evidence, reload, no
horizontal overflow and no browser errors. The fixture initially failed honestly
because its clock was past coupon expiry, then because other retained paths had
advanced the configuration revision. The fixture was corrected to name its true
captured revision and run within its existing explicit validity period. One
driver locator was corrected to expand the price evidence rather than the cohort
panel. No product gate or expected amount was relaxed. Every driver closes its
session; fixture shutdown reports zero outgoing edges and zero notifications.

## Boundaries

Synthetic dates establish no empirical history or calibration. Source rights,
retention, production adapter/receipt semantics, operating affordability, live
coupon success and notification delivery, buyer acceptance and activation/deploy
remain unproven. Personal/basket commitments outside the supported standalone
public scenario remain unavailable for rankings/targets. No installs/downloads,
external network/live acquisition, credentials/accounts, production DB,
activation, deployment, push, PR, delegation or original-parent cleanup occurred.
Only local commits/merges are authorized; the integration merger owns closure.

Final integration refresh, checks and source manifest are recorded below and in
[artifacts/watch-assessments](artifacts/watch-assessments).


## Final integration refresh and verification

Merged the latest integration **52104eb3de8e4b7c6ff615763d8ecc3572e4e34d** in local
merge **feeb3496db72ea27b2c40b3692e5440b6cb1de5c**. Both the requested initial
`c84f1f1` and this latest tip are ancestors. This includes the committed shared
grant resolver, schema **2.1**, denied-Watch timestamp repair and their positive
controls. No incoming policy gate or ticket07 ownership code was weakened.

The merge exposed a transaction interaction: the durable policy resolver now
opens a write transaction when no connection is passed. Calling it from inside
assessment persistence's existing transaction caused `database is locked`. The
first combined run was stopped after **6 failed, 15 passed**; its red log is
retained. Assessment persistence now passes its transaction to `current_policy`,
and discovery uses its already resolved admission outcome. The affected discovery
plus assessment suite passed **16 in 14.22s**. The full final cleared-environment
suite then passed **171 in 157.33s**: latest integration's **160** (including all
original126) plus **11** assessment workflows, no skips or xfails.

After that full run, the two interrupted-send workflows were tightened to fail
at the external notification-configuration I/O boundary before channel claim.
The real evaluator and dispatcher are no longer replaced in those tests. The
terms-change case uses normal evidence-only recapture without target policy,
then normal pending recovery. All **11** final assessment workflows passed again
in **10.72s**. No product behavior or assertion was relaxed by this test refinement.

Other results:

- **25 frontend tests pass** and production build passes (**644 modules**).
  The existing large-chunk warning remains; no threshold was raised.
- **37 limiter/external-browser contracts pass**, ten inherited deprecation
  warnings. **Eight focused application files pass mypy**, with existing
  unused-override notes.
- **13 clean Python files pass Ruff**; the complete changed-file comparison
  against `52104eb` has **10 inherited diagnostics, zero added**. Ten focused
  files pass Black; diff whitespace check passes. No suppression was added.
  Inherited full-repo lint/type debt and ESLint10's retained missing-config
  blocker were not repaired or presented as green.
- Final actual browser proof also submits a synthetic identity correction.
  Current-best and observed-low both become explicitly invalidated historical
  results in narrow buyer details, with no overflow. Updated desktop/narrow and
  withdrawn-state PNGs plus browser receipt are retained. Session closes and
  fixture shutdown records **zero escaped edges, zero notifications**.

Raw red/green logs, final safe-suite/focused/contract/build/frontend outputs,
Ruff baseline comparison and screenshots are in `artifacts/watch-assessments`.
The source manifest binds the checked files and receipts; the handoff reply gives
the final local commit. Final merge/readback remains local and merger-owned
integration/closure remains separate.

## Sole merger review — 2026-10-27

**Disposition: 08 remains open for one added type-check failure.** No product
source repair was attempted. The parent owns the contained repair; 11 retains
its existing independent owner and 12 remains blocked. This review provides
offline evidence only. Collection remains staged. Buyer walkthrough acceptance,
live offer/history/coupon proof, empirical calibration, source rights/access,
retention/deletion/backup, finite operating/physical-resource prerequisites,
maintenance ownership and activation/deployment remain unproven.

### Identity, ancestry and preservation

- Integration began clean on `integration/watch-category-discovery` at
  `52104eb3de8e4b7c6ff615763d8ecc3572e4e34d` in the existing
  `/Users/jay/.t3/worktrees/pricerecon/watch-category-integration` checkout.
- Source was clean on `t3/ticket08-price-assessments` at
  `81f18ab18d3417f17945ca46ec437e628689a892` in the existing `t3-e29f7fa4`
  checkout. `git merge-base --is-ancestor 52104eb 81f18ab` succeeded. No source
  refresh was necessary because integration had not moved.
- `git merge --no-ff 81f18ab18d3417f17945ca46ec437e628689a892` produced
  **`20728c299d2b8a8d217e80dd0dcd5fef6fa79ea1`**, with exact parents
  `52104eb3de8e4b7c6ff615763d8ecc3572e4e34d` and
  `81f18ab18d3417f17945ca46ec437e628689a892`. No conflicts occurred. A full
  `git diff --exit-code 81f18ab 20728c2` passed; all four source-side commits,
  including its integration merge and transaction repair, are ancestors.
- The supplied manifest's **23 source hashes and 22 receipt hashes all match**
  in integration, including red traces, final tests and browser PNGs/receipt.
  `source-receipt-hashes.json` records every expected/actual digest. The source
  receipt's critical 07 correction owners and 10 collection-policy/rate-limiter
  owners have no source diff against `52104eb`; schema 2.2 adds assessments
  alongside durable grant schema 2.1. The assessment transaction passes its
  connection to `current_policy`; the retained 6-failed/15-passed lock trace is
  preserved, and the final combined run below passes.
- All **77 files** in the original parent's initial manifest match byte count
  and SHA-256 (`original-77-hashes.json`). No edits, cleanups, app imports or
  tests were run in that dirty checkout; only its existing interpreter was used.
  Source remains unchanged. Review changes are confined to this integration's
  receipt, review artifacts and tracker disposition. No 11 source/claim edits,
  12 claim, checkout creation, reset/rebase/squash/cherry-pick, push or PR occurred.

### Standards finding and exact reproducer

**P2 / acceptance repair required:**
[`src/pricerecon/models/tracking.py:101`](../../src/pricerecon/models/tracking.py#L101)
adds `default_factory=lambda: ["public_no_coupon"]` to a
`list[Literal["public_no_coupon", "public_coupon"]]` field. The existing mypy
infers the factory return as `list[str]` and rejects the argument (`arg-type`).
This is newly introduced by ticket08, not an inherited diagnostic. A separate
temporary copy of the baseline `52104eb` model passes the same no-incremental
type check; the current model fails independently of incremental cache state.
No ignore, cast, suppression or feature repair was added. The small fix must
preserve the default opt-out and explicit coupon opt-in contract.

From integration, use the cleared environment below, then:

```sh
"$PY" -m mypy --no-incremental --follow-imports=silent src/pricerecon/models/tracking.py
```

Expected/observed: exit 1 with the single factory `arg-type` error at line 101.
Retained exact output: `merger/mypy-reproducer.txt`; focused eight-file failure:
`merger/mypy.txt`; baseline control: `merger/mypy-baseline.txt`. The implementer's
eight-file green receipt did not establish this added model's type correctness.

No additional behavioral acceptance defect was reproduced. Spec review checked
the versioned exact cohorts/current/low paths, supplied policy/freshness and
evidence versions, retained coverage/attempts/gaps/exclusions, new/used/quantity/
destination/dispatch/payment/purchase-mode separation, correction/policy/stale
withdrawal, unresolved sibling isolation, duplicate/contradictory evidence and
the independently unavailable usual/personal/savings gates. Coupon paths reuse
the coupon owner's reproduced payable and shared exact evaluator/dispatcher;
there is no added arithmetic, collector, scheduler or queue. The separate base
price and required code remain in coupon details and dispatched messages.
Restricted, conditional and advertised benefits are excluded from public ranking.
This source/fixture review cannot certify real offer semantics or buyer usability.

Existing workflow assertions were not removed or weakened by this source diff.
The final interrupted-send tests replace only external configuration I/O; they
retain the real evaluator, dispatcher and atomic channel claim. All earlier 160
guarded cases remain in the combined run; no skip/xfail or suppression was added.

### Repeated checks and independent behavior challenge

All commands ran from integration. Frontend dependencies were already installed;
the production build completed **before any application import/test/probe**.
There was no install/download, network acquisition, account/credential use,
production storage, activation, deployment or purchase. No full repository pytest
or unsafe `tests/test_api.py` was run. Runtime probes use fresh child imports,
`MonitoringHarness`, marked temporary SQLite, controlled clock/acquisition and
captured external sends. No probe writes private application storage or replaces
the evaluator/dispatcher. Each probe terminates and its temporary storage closes;
this review started no fixture server or browser session.

Cleared environment for Python commands (the code below shows the equivalent
shell setup; actual calls used `env -i` with these values):

```sh
PY=/Users/jay/.t3/worktrees/pricerecon/t3-7260bb2e/.venv/bin/python
export PATH=/Users/jay/.nvm/versions/node/v24.14.1/bin:/usr/bin:/bin
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="$PWD/src:$PWD"

npm --prefix frontend run build
npm --prefix frontend test -- --run
npm --prefix frontend run lint

"$PY" -m pytest -q tests/test_collection_workflow.py tests/test_monitoring_workflow.py \
  tests/test_discovery_workflow.py tests/test_qualification_workflow.py \
  tests/test_cost_workflow.py tests/test_history_workflow.py tests/test_coupon_workflow.py \
  tests/test_tracking_workflow.py tests/test_correction_workflow.py \
  tests/test_correction_target_ownership.py tests/test_shared_grant_workflow.py \
  tests/test_assessment_workflow.py
"$PY" -m pytest -q tests/test_rate_limiter.py tests/test_external_browser.py

"$PY" -m mypy --follow-imports=silent src/pricerecon/core/comparisons.py \
  src/pricerecon/core/coupons.py src/pricerecon/core/exact_tracking.py \
  src/pricerecon/core/notifications.py src/pricerecon/db/assessments.py \
  src/pricerecon/models/assessments.py src/pricerecon/models/tracking.py \
  src/pricerecon/api/discovery.py

"$PY" docs/testing/artifacts/watch-assessments/merger/independent-probe.py opt_out
"$PY" docs/testing/artifacts/watch-assessments/merger/independent-probe.py recovery
"$PY" docs/testing/artifacts/watch-assessments/merger/independent-probe.py channel_expiry
"$PY" docs/testing/artifacts/watch-assessments/merger/verify-static.py
```

| Check | Observed result / raw evidence under `artifacts/watch-assessments/merger/` |
| --- | --- |
| Complete guarded workflow suite | **171 passed in 162.01s**, no failures/skips/xfails; `safe-suite.txt` |
| Limiter/external-browser contracts | **37 passed**, ten inherited deprecation warnings; `contracts.txt` |
| Frontend | **25 passed**; `frontend-tests.txt` |
| Production build | **Passed**, 644 modules; existing >500kB chunk warning retained; `build.txt` |
| ESLint | **Blocked**, missing `eslint.config.*` under installed ESLint 10.12.0, same existing prerequisite; `eslint.txt` |
| Focused mypy / one-file uncached control | **Failed**, one added model error described above |
| Focused Ruff | **13 files passed**; `ruff-clean.txt` |
| Changed-file Ruff vs `52104eb` | **10 baseline, 10 current, zero added**, no added suppressions; `ruff-comparison.json` and raw JSON |
| Source/non-artifact diff whitespace | **Passed**, `diff-source.txt` is empty |
| Whole diff whitespace | **Failed only in retained raw logs**, exact diagnostics in `diff-all.txt`; preserved, not rewritten |
| Source/receipt and original manifest | **45/45 and 77/77 match**, full per-file hashes retained |

`verify-static.py` retains the complete 18-file Ruff comparison command and
per-file diagnostics. It checks temporary baseline file copies, not another
checkout. Both sides explicitly set `lint.isort.known-first-party=["pricerecon"]`
so that the temporary directory cannot change import classification. The initial
review helper hit macOS `/tmp` versus `/private/tmp` path normalization; the
helper now resolves the temporary path. This was a review-helper error with no
application impact. Raw source artifacts are unchanged.

Three bounded independent cases extend the supplied eleven assessment workflows:

1. **Same-label opt-out during pending recovery:** create a real GBP45.10
   coupon crossing from a GBP50.10 no-coupon baseline. Interrupt the external
   notification-config I/O after event reservation and before channel claim.
   Recover with the original same-version default no-coupon policy. Expected and
   observed: pending becomes withheld, zero sends, zero escaped edges. This
   challenges full policy fingerprint invalidation rather than version equality.
2. **Unchanged positive recovery:** identical reservation/interruption, recover
   with unchanged opt-in policy. Expected and observed: exactly one captured
   webhook, GBP45.10 payable, required `TEN` code and distinct GBP50.10 base in
   payload/message, no escaped edges. This checks that interruption itself does
   not make the first negative case pass by breaking all recovery.
3. **Coupon expiry between channel claims:** reserve the same genuine fixture
   crossing for webhook and Discord. The captured first webhook succeeds and
   advances the controlled clock to the coupon's explicit exclusive expiry.
   Expected and observed: webhook `sent`, Discord `withheld`, exactly one send,
   zero escaped edges. No internal dispatcher or channel-claim mock is used.

The exact script and complete before/after API delivery records, payloads,
assertions and captured-edge results are retained in `independent-probe.py` and
`probe-opt-out.txt`, `probe-recovery.txt`, `probe-channel-expiry.txt`. All three
fresh processes exited 0. These are synthetic behavior controls, not live coupon
success, delivery reliability or empirical market evidence.

### Retained browser identity and limits

Inspected the actual unchanged `browser/desktop-assessments.png` (1280×900),
`browser/narrow-assessments.png` and `browser/narrow-withdrawn.png` (375×812),
plus `browser/receipt.json` and the driver assertions. They show the scoped
GBP45.10 public-coupon claim, dated low and correction invalidation with narrow
wrapping; the existing driver's overflow/error/reload controls remain retained.
There was no substantive UI change or evidence gap requiring a repeat browser
session. This review reuses those source-bound screenshots/receipt specifically,
not an imagined new walkthrough. Buyer feedback was not manufactured.

PNG SHA-256 identities, verified against the source manifest:

- Desktop: `171cfd06b6e7b50f7169a2e44e93cf837ea8d92529be21a7683f06b66a2e0b83`
- Narrow: `55a4b24d26fe895dfb0083dd5a9475f47d6d5e85b9b8bd5cf70d492b252910f8`
- Withdrawn: `828f34c70cc1f97900bd361e5e8f829f084fcfa9fc7564ff72ef5d20e60b4c39`

The review artifact manifest binds the new raw checks/scripts. The subsequent
local review commit records this disposition; its full HEAD is in the handoff.
08's checklist is not closed while its added mypy diagnostic remains. No 12
workflow or 11 implementation acceptance is claimed.
