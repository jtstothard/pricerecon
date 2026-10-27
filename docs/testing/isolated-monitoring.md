# Isolated existing-monitoring verification (ticket 01)

Source/API verification: **passed**. Rendered-UI acceptance: **pending**.
No resolved defect remains xfailed. This receipt does not close the ticket's UI
acceptance requirement or establish live readiness.

## Checkout and retained baseline

Implementation checkout: `/Users/jay/.t3/worktrees/pricerecon/t3-91a7577d`, branch
`t3/verify-monitoring-isolation`. The prior implementer's uncommitted work was
retained in local commit `7db24a7`, then integration tip
`85ca66d` was merged in `841afd1` before repairs. Original source baseline:
`ef86af6d41fbb3cac8982f43997068e906477025`.

The buyer explicitly authorized local commits/merges for this continuation,
overriding the original ticket's older commit prohibition. Changes belong only
to this isolated checkout. No push, PR, live collection, production database,
account access, deployment or activation is part of this receipt. Integration
into the shared branch belongs to the separate merger.

## Reproduce safely

From the implementation checkout, use the existing environment without installs:

```sh
PYTHONPATH="$PWD/src" /Users/jay/.t3/worktrees/pricerecon/t3-7260bb2e/.venv/bin/python \
  -m pytest tests/test_monitoring_workflow.py -q
```

Only this module is collected. Do not substitute the broad suite or legacy API
fixtures: some fixtures unlink their configured database and other modules
perform live source work.

## Agreed seam and isolation

`tests/monitoring/harness.py` supplies the accepted application boundary: real
FastAPI lifespan/routes, normal API checks and scheduler callback, SQLite,
diff engine, connector health and notification dispatch/logging. Deterministic
connector discovery/outcomes, wall time and outbound send transports are the
controlled external edges. Assertions use API responses, public scheduler
registrations and captured deliveries; SQL seeds legacy input only.

Each scenario runs in a fresh child Python process. Before application import,
the harness changes into a new temporary directory and clears the environment.
The relative SQLite path, `.env`, `config.yml` and `config.local.yml` therefore
cannot resolve to workspace/production files. Discovery is replaced before
source seeding can instantiate real plugins. No real credentials are supplied.
A cold-process scenario shares only a marked temporary directory, validates its
location and removes it after both processes exit.

Audit guards reject SQLite outside the temporary database, socket connections,
DNS/datagrams and subprocess/system/spawn calls. Real sync/async HTTPX transports
are blocked. Native curl is blocked at sync/async request and transfer entry
points, because libcurl can bypass Python socket auditing. Browser startup is
blocked explicitly. Guard failures inherit from `BaseException`, so broad
application exception handlers cannot swallow them. The isolation scenario
probes an outside database, DNS, process launch, both HTTPX transports, curl
sync/async/native transfer and browser startup, all rejected before I/O.
Unexpected guarded edges fail every normal scenario. This is a controlled Python
workflow, not an OS sandbox for arbitrary native code; real plugin discovery is
excluded entirely.

`WatchScheduler(automatic_checks=False)` uses the existing scheduler, starts its
interval timer paused and suppresses immediate startup checks. Explicit checks
still execute normally. Separate scenarios use the unchanged default to prove
automatic startup and saved time-window behavior. Controlled time covers
application/notification/health timestamps, schedule decisions and SQLite
`CURRENT_TIMESTAMP`. APScheduler's interval timer remains real; limiter refill,
real-time coalescing and long-running concurrent checks are not simulated.

## Repairs and compatibility

The executor distinguishes failed/skipped sources from successful results,
including successful empty results. `run_check` receives a failure set, excludes
those sources from disappearance events and preserves their stored rows in place.
Original observation timestamps and payloads survive; retained evidence is not
counted as freshly found. Successful sources still replace their snapshots and
emit normal changes. A successful empty source removes its old rows and emits
`listing_gone`. Disabling/removing a source retains the pre-existing replacement
semantics; failure preservation is limited to enabled failed/skipped acquisition.
No schema, second scheduler, history engine or notification service was added.

Simple Watches use the existing `legacy_query_match`: every fallback-query term
must appear in the title. Raw source overrides pass to connectors unchanged and
do not replace the title filter. Watch-level synonym groups, or existing nested
spec groups, replace fallback-query matching with existing token/phrase rules.
Exclusions and the other filters remain active. Display titles do not affect
matching. This implements ADR 0001 without a new DSL or hardcoded category routes.

## Red/green evidence

After the baseline merge, removing the two strict xfail markers reproduced
**2 failed, 5 deselected**. The partial-failure replay reported:

- Failed source lost its last-good listing.
- Partial failure emitted `listing_gone` and `price_drop`.
- Recovery treated one retained listing as new and delivered a duplicate alert.

The simple-query replay returned both `matching` and `unrelated` for `Casio blue`.
The independent exclusion already removed the parts listing.

The snapshot repair then passed the partial-failure tracer (**1 passed,
6 deselected**). Restoring the ADR fallback passed the original suite
(**7 passed**). Expanded failure/empty/restart scenarios passed (**10 passed**).
Final matching and total-failure coverage passed **14 tests, no xfails**.
The original scheduler startup and controlled-window red/green tracers are
retained in `7db24a7`: pausing APScheduler alone initially allowed the separately
created immediate task; the opt-in mode fixed it. Schedule evaluation originally
re-imported wall time; using its existing module-level datetime enabled control
without changing production time semantics.

## Verified behavior

- API create/check and real lifespan remain inside temporary storage; immediate
  and one-second interval checks stay paused in explicit mode.
- Legacy display title, fallback/raw queries, groups, exclusions, price ceiling,
  enabled/disabled state, interval/timezone/window and notification destinations
  survive migration, API edits and restart.
- Raw per-source syntax/whitespace is untouched; missing overrides use fallback.
  Simple matching requires all fallback terms regardless of order/case. Advanced
  matching covers OR/AND groups, contiguous phrases, complete model/size tokens,
  preserved `+`, exclusions and default/nested group compatibility.
- Initial baseline is silent. A scheduler callback stores a price drop and
  captures webhook, Telegram and Discord sends. Omitting notifications during
  edit retains them; deselected new-listing events are stored without delivery.
- Timeout, unexpected error and auth degradation preserve last-good evidence;
  fresh auth failure skips source collection without erasing evidence. Other
  sources still alert for price drops. Unchanged recovery after lifespan restart
  is silent; a later genuine drop alerts normally.
- A successful empty source removes old evidence; total-source failure retains
  the existing baseline. A separate cold Python process recovers a failed source
  without repeating the earlier price-drop notification.

## Quality checks and remaining acceptance

- Targeted isolated workflow: **14 passed**, zero xfails.
- Ruff on added test/harness files: passed.
- Black on changed Python files: passed.
- Mypy on `schedule.py`, `scheduler.py`, `diff_engine.py` and `watch_executor.py`
  with `--follow-imports=silent`: passed (existing unused-override note only).
- Source Ruff findings compared by code/message against integration `85ca66d`:
  no added findings. Existing findings are retained, not suppressed.
- `git diff --check`: passed. No broad/unsafe fixture or live suite was run.

**Remaining acceptance:** a rendered browser/UI walkthrough of the saved-search
workflow. The frontend tooling baseline in integration has been repaired; the
previous missing-dependencies explanation is stale. This continuation has not
run a frontend build/test or driven rendered UI, so it makes no UI-behavior claim.
The tests verify UI-consumed API data and an API edit only. A frontend build or
helper-test result alone would not establish browser acceptance.

Last-good rows retain observation age, and `/api/health` retains source failure
state; this does not add per-run coverage history or certify current availability.
The existing `/history` remains empty in these checks; replacement snapshots and
events are not a longitudinal observation ledger. First-run semantics for an
otherwise genuinely empty successful snapshot remain unchanged. Transport sends
are captured deterministic successes; production delivery/retry/crash ambiguity,
concurrent manual checks and later discovery qualification remain outside this
slice. Source completion is ready for merger review; overall ticket acceptance
stays open for the UI gate.
