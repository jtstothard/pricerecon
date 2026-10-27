# Isolated existing-monitoring verification (ticket 01)

Baseline: `ef86af6d41fbb3cac8982f43997068e906477025`.
Implementation checkout: `/Users/jay/.t3/worktrees/pricerecon/t3-91a7577d`.
All changes remain uncommitted. Parent source/planning files and ticket status
were not changed. This receipt covers ticket 01 only.

## Run the workflow

From this checkout, using the existing parent environment without installing anything:

```sh
PYTHONPATH="$PWD/src" /Users/jay/.t3/worktrees/pricerecon/t3-7260bb2e/.venv/bin/python \
  -m pytest tests/test_monitoring_workflow.py -q -rx
```

Only this test module is collected. Do not substitute the legacy API fixtures or
the global suite: some existing fixtures unlink their configured database and
other modules perform live source work.

The two unmet requirements are strict expected failures, **not passed gates**.
To reproduce them as ordinary failing tests:

```sh
PYTHONPATH="$PWD/src" /Users/jay/.t3/worktrees/pricerecon/t3-7260bb2e/.venv/bin/python \
  -m pytest tests/test_monitoring_workflow.py --runxfail \
  -k 'partial_source or simple_saved' -q
```

## Isolation seam

`tests/monitoring/harness.py` supplies the accepted application boundary: real
FastAPI lifespan and API routes, normal execution through the API check endpoint
and scheduler callback, real SQLite, diff engine, health storage, scheduler and
notification dispatch/logging. Only connector discovery/outcomes, wall time and
the three outbound notification transports are controlled external edges.
Assertions read API responses, public scheduler registrations and captured
deliveries. SQL is used to seed legacy input, not to assert behavior.

Each scenario runs in a fresh Python process, with an explicit source-tree
`PYTHONPATH` and an environment whitelist. Before importing the application the
harness changes to a new temporary directory and clears the environment. Thus
the relative database path, `.env`, `config.yml` and `config.local.yml` cannot
resolve to workspace/production files. Connector discovery is replaced before
database initialization can instantiate source plugins. No real credentials are
provided. The cold-process restart scenario shares only a marked temporary
directory, validates its temporary location, and removes it after both child
processes exit.

An audit guard rejects SQLite connections outside the one temporary database,
Python socket connections/DNS/datagrams and subprocess/system/spawn calls.
Real sync/async HTTPX transports also fail closed. Guard failures inherit from
`BaseException` so the application's broad `except Exception` handlers cannot
turn an isolation breach into a successful workflow. The isolation scenario
deliberately probes an outside database, DNS, subprocess launch and a real HTTPX
transport; all are rejected before the requested operation. Unexpected guarded
edges fail every normal scenario. These are Python workflow guards, not an OS
sandbox for running arbitrary native connector code: real plugin discovery is
excluded entirely.

The real scheduler is registered but starts paused in the default harness
session. `WatchScheduler(automatic_checks=False)` also suppresses its separate
immediate background checks. A normal API check still executes deliberately.
Separate guarded scenarios use the unchanged constructor default to prove
automatic startup and saved time-window behavior. The controlled clock covers
application/notification/health timestamps, schedule-window decisions and
SQLite `CURRENT_TIMESTAMP`; APScheduler's interval timer remains real and is
paused for explicit-check scenarios.

## Observed gates

- **Passed:** API create/check and real lifespan startup remain inside temporary
  storage; neither immediate nor one-second interval jobs run in explicit mode.
- **Passed:** seeded pre-migration saved-search rows retain display title,
  fallback query, exact raw source query, synonym groups, exclusions, price
  ceiling, enabled/disabled state, interval/timezone/window and notification
  events/channel destinations through API reads and lifespan restart.
- **Passed:** source queries reach the controlled connectors untouched; a
  missing source override uses the fallback query. Synonym OR/AND matching,
  complete-token model distinctions, exclusions and price ceiling reject the
  supplied traps. Disabled sources are not collected.
- **Passed:** initial baseline is silent; a normal scheduler callback records
  one price-drop event and delivers the configured webhook, Telegram and
  Discord notifications. An edit omitting notifications retains them. A later
  new-listing event is stored without delivery when only price drops are enabled.
- **Passed:** a new scheduler/lifespan and a separate cold Python process retain
  saved state and the current snapshot; checking the unchanged offer emits no
  duplicate notification. Saved time windows use the controlled clock; normal
  constructor defaults still execute enabled searches automatically.
- **Failed:** partial-source failure retains health degradation but deletes
  that source's last-good listing, records `listing_gone`, then treats the same
  recovered listing as new and sends a duplicate new-listing notification.
  The deterministic receipt is:
  `Failed source lost its last-good listing; Partial failure emitted events
  ['listing_gone', 'price_drop']; Recovery treated 1 retained listing as new;
  Recovery caused duplicate notification: ['price_drop', 'new_listing']`.
- **Failed:** a simple saved search with no synonym groups sends its fallback
  query to the connector but does not apply the ADR's fallback title filter.
  `Casio blue` admits both `matching` and `unrelated` listing IDs; the independent
  exclusion rule still removes the `parts` listing.
- **Unproven:** browser/UI walkthrough. This checkout has no frontend build or
  installed frontend dependencies, and no installation was authorized. The
  tests cover UI-consumed API data and an API edit, not rendered UI behavior.
- **Out of scope:** live collection, account/credential access, production DB
  operations, deployment, activation and the later discovery/history tickets.

The two failed requirements are baseline defects in execution/diff behavior.
Repairing them would exceed this task's behavior-preserving source-change
authority. Their tests use a distinct `MonitoringRequirementGap`; unrelated
test/harness errors cannot satisfy the expected-failure marker. Strict XPASS
also fails the suite so fixing a defect requires removing/updating its marker.
Ticket 01 acceptance remains blocked by these failures and the UI gate.

The existing price-history API is also empty after these monitoring checks;
the workflow asserts only retained snapshot/events and does not claim that a
longitudinal observation ledger exists.

## Red/green and quality evidence

The first scheduler tracer failed with
`Startup/interval jobs ran without an explicit check`: pausing APScheduler alone
did not suppress its separately created startup task. The minimal scheduler
option made the tracer pass. The saved-window tracer then timed out waiting for
the controlled in-window run because schedule evaluation re-imported wall time.
Using the existing module-level datetime import made it pass with unchanged
production time semantics.

The legacy-storage and cold-process tracers first failed because their harness
storage helpers were absent, then passed after adding those helpers. The two
acceptance failures above were each observed unmarked before being recorded as
strict expected failures. No execution/diff behavior was changed to hide them.

Final verification uses the parent Python environment and this checkout's source:

- Targeted workflow: **5 passed, 2 xfailed**. The strict requirement replay:
  **2 failed, 5 deselected** (expected; details above).
- Ruff on `tests/monitoring` and `tests/test_monitoring_workflow.py`: passed.
- Black on the added Python files: passed.
- Mypy on the two changed source files with `--follow-imports=silent`: passed.
- Ruff on changed source files retains the exact baseline findings: 5 in
  `schedule.py`, 12 in `scheduler.py`, zero added findings (compared by code and
  message against `git show HEAD:<path>`). No unrelated lint cleanup was made.
- `git diff --check`: passed. No full-suite, live or unsafe API-fixture run.

Source changes are limited to the opt-in scheduler execution mode (default
unchanged) and the equivalent datetime lookup needed for deterministic schedule
time. There is no second scheduler, schema migration or new monitoring engine.
