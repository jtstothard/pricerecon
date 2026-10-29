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
previous missing-dependencies explanation is stale. The earlier API continuation did not
run a frontend build/test or drive rendered UI, so it makes no UI-behavior claim.
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

## UI edit preservation follow-up (2026-10-27)

The parent subsequently drove the rendered form against an isolated harness-backed
server and observed a real preservation defect: saving only a display-title change
reset notifications, timezone/window and nested spec exclusions. The saved `30m`
interval remained in the payload but the select displayed the first preset instead.
This follow-up repairs that defect; **post-fix browser acceptance is still pending**.

Implementation checkout: `/Users/jay/.t3/worktrees/pricerecon/t3-d036dfd5`, branch
`t3/preserve-watch-edit-intent`. Before edits, integration
`4df9cc094e945712b6fa5df98071411992180c27` was fast-forward merged and verified as
an ancestor. The original dirty parent checkout was not edited. Only its existing
Python environment was reused. This checkout's `frontend/node_modules` is a symlink
to the explicitly permitted integration dependency directory; no dependency,
lockfile, browser install or download was needed.

`WatchForm` now uses an edit payload that retains saved nested configuration and
applies changes only to fields the form owns. Notifications/destinations, schedule
timezone/window, source-specific config, disabled sources, spec rules, deduplication,
seller thresholds, floor/component settings and grouping survive unrelated edits.
Unchanged decimal values, null category and raw-query whitespace are retained.
Deselecting a source disables its retained config; selecting it again enables that
same config. New sources still receive normal defaults. New-watch defaults are
unchanged. Pause/resume in the list uses the same preservation path instead of its
own destructive defaults.

Intentional edits still update fallback/raw queries, synonym groups, exclusions,
price/condition filters, source selection and interval. Empty raw fields use fallback;
choosing simple mode clears raw overrides while retaining matching rules, as before.
Hidden nested spec exclusions/groups remain independent. Form arrays are copied so
editing a synonym term cannot mutate the saved Watch before submission. Existing
all-disabled source configurations permit unrelated edits without forcing a source
on. A custom saved interval now has a selected `Every 30m (saved)` option.

### Additional red/green receipts

- Title-only frontend tracer: **1 failed, 17 skipped**, demonstrating resets across
  source config/state, filters, grouping, notification destinations, timezone/window
  and null category. After the edit-payload repair: **18 passed**.
- Actual frontend payload through the accepted isolated API seam: **1 failed,
  14 deselected**, reporting `Watch 7 lost schedule`; after repair: **1 passed,
  14 deselected**. The test generates payloads with installed Node type stripping
  before the guarded child starts, then sends them to the real API. It checks both
  enabled and paused legacy Watches, every returned saved field except the intended
  title/timestamp, lifespan restart, query routing, parts exclusion, silent baseline
  and subsequent captured webhook/Telegram/Discord delivery. Application isolation
  guards remain unchanged and report no unexpected edges.
- React static-markup tracer for the custom interval: **1 failed, 18 skipped**, still
  red after initial form hydration alone; adding the matching option produced
  **1 passed, 18 skipped**. This is markup verification, not a browser walkthrough.
- Retaining untouched raw overrides during another query edit: **1 failed,
  19 skipped**, then **1 passed, 19 skipped**. An unchanged whitespace-only override
  for an unavailable source was initially dropped; only deliberately changed empty
  overrides are now removed.
- Editing a Watch whose sources are all disabled: **1 failed, 20 skipped** with
  `Select at least one source.`, then **1 passed, 20 skipped**. New-watch validation
  still requires a selected source.

Final checks in this checkout:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PWD/src" \
  /Users/jay/.t3/worktrees/pricerecon/t3-7260bb2e/.venv/bin/python \
  -m pytest tests/test_monitoring_workflow.py -q
```

**15 passed in 16.13s**, no xfails; only the targeted isolated module was collected.
From `frontend`, `npm test -- --run`: **25 passed**. `npm run build`: **passed**
(TypeScript plus Vite; existing large-chunk advisory remains). Ruff and Black on
both changed Python files, plus `git diff --check`: **passed**. No assertions were
weakened, checks suppressed or untyped escape hatches added.

**Rendered UI gate: PENDING.** The parent must repeat the actual title edit and
saved-search walkthrough after local integration, including the selected custom
interval and retained enabled/disabled state. This implementation did not run a
post-fix browser session and does not claim UI acceptance. Separate merger owns
integration; ticket 01 stays open. No push/PR, live source access, credentials,
production database, deployment or activation occurred.

## Legacy fixture reconciliation — 2026-10-29 (causal claim corrected same day)

The CI quality gate's full-pytest step surfaced one full-suite failure on this
branch: `test_watch_executor_filters_by_spec_match_ram`. An earlier version of
this note attributed the failure to a fixture that had drifted from a
2026-07-23 contract. That causal claim was wrong. The verified facts, each
checked against `origin/main`:

- The fixture predates the matching model entirely — f78204e (2026-07-12)
  added the watch execution path it exercises.
- 26de71e (2026-07-23) added `legacy_query_match` as a function plus a unit
  test (`tests/test_title_matching.py`), but on `origin/main` it has **no
  callers in `src/`**. The watch path there (`execute_watch`) ran from
  `apply_post_normalization_filters` through the component-pattern and
  price-floor filters to `run_check` with **no query-term title gate at all**;
  the old fixture (laptop-less titles, query `"laptop"`) passes on `origin/main`.
- Watch-path enforcement of the all-query-terms fallback began with **this
  branch's commit 9312871** (2026-10-27), which wires `legacy_query_match`
  into `watch_executor` for watches without synonym groups. That enforcement —
  not a stale fixture — is why the test went red on this branch.

The fixture was then adapted in f50d273: both fixture titles now contain the
watch query term ("Laptop"), so the RAM(32) floor remains the discriminating
filter. The assertion was not edited, weakened, skipped or xfailed, and no
production code changed. After the fixture edit the module pair
(`tests/test_connectors.py` + `tests/test_source_queries_routing.py`) runs
**36 passed**.

What the fixture edit does not settle: **this branch changes matching behavior
for existing watches without `synonym_groups`.** A watch with query `"laptop"`
that previously surfaced `Lenovo ThinkPad T14 16GB RAM 512GB SSD` now returns
no such listing, because the title does not contain the word "laptop", and no
migration provisions synonym groups for existing watches. ADR-0001 both
mandates that fallback ("Watches without `synonym_groups` fall back to the
existing `_filter_listings_by_query` behavior") and states "Non-GLM watches
are unaffected" — an internal tension, since the "existing" behavior it cites
lived only in `connectors/reddit.py`, never in the watch executor. **The
product decision on how existing synonym-less watches should behave is made
separately in the follow-up; this note records the change and does not
adjudicate it.**

Environment preconditions for the recorded full-suite runs: the **842 passed,
10 skipped, 0 failed twice back-to-back** result was obtained with
`TMPDIR=/tmp` in effect (Linux CI and the normalized local shell agree there;
the recorded runs did not use a plain macOS shell). In a plain macOS shell
(`TMPDIR=/var/folders/…`), three fresh-process tests —
`test_cost_history_survives_restart_quantity_basket_changes_and_repeated_capture`,
`test_coupon_history_survives_restart_and_changed_evidence_invalidates_old_application`
and `test_adapter_evidence_and_limits_survive_fresh_process_without_refresh` —
would have failed because the parent's temp root and the env-scrubbed child's
`gettempdir()` resolve differently, tripping the harness's shared-storage
guard. That launch-env fragility has since been removed test-side: the child
env now carries the parent's resolved temporary root as `TMPDIR`, and the full
suite passes in a plain shell, under `TMPDIR=/tmp` and with `TMPDIR` unset, in
both project venvs (Python 3.14 and 3.13). Pinned Black and Ruff, mypy
(baseline unchanged) and `git diff --check` pass. No push occurred.
