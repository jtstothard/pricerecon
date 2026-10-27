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
