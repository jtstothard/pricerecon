# Ticket02: staged wristwatch discovery verification

2026-10-27. Branch `t3/implement-ticket02-discovery`; isolated checkout
`/Users/jay/.t3/worktrees/pricerecon/t3-5d95a049`. Started clean at `ef86af6`,
merged integration `f62364d` before edits and confirmed ancestry. Parent dirty
checkout was not edited or used for application execution. Only its existing Python
environment was reused, with this checkout's source on `PYTHONPATH`. Frontend
dependencies are symlinked to the integration checkout. No installs were performed.

Implementation commit: `9343548`. Before handoff, merged latest integration tip
`15beae4` in `c135131` and confirmed ancestry. That merge changes only the earlier
monitoring browser receipt; the tested application/test source is identical to the
implementation commit. No runtime rerun is needed for that documentation-only merge.

## Implemented boundary

`/discover` and desktop/mobile navigation expose illustrated leads, editable
preferences, explicit missing data, expandable evidence/lineage and dated coverage.
`GET /api/discovery/watches` returns candidates and acquisition receipts;
`GET/PUT /api/discovery/watches/preferences` persists values with revision conflict
checks. These routes use the application's existing authentication dependencies.

`execute_discovery` is the normal one-shot category execution entry point, independent
of saved Watches. Default admission records `not_attempted` without constructing
connectors. Deterministic execution requires explicit offline policy, permission and
activation references. There is no collection HTTP endpoint, live activation mode,
new scheduler job or acquisition service. Offline references are test receipts, not
production entitlement or budget enforcement.

`acquire_sources` extracts the existing Watch executor's registry/configuration,
initialization, search, health and cleanup lifecycle. Both execution entry points
use it. Watch filters, baseline/diff, scheduler and notifications retain their owners.
Dynamic connector configuration retains the existing legacy boundary; new discovery
contracts use concrete typed fields.

Additive SQLite init records migration `1.3`: independent preferences, captures and
capture-bound leads. Connector config/credentials are excluded from receipts.
Acquisition outcomes persist independently of preferences; source completeness is
explicitly unknown. Repeated extraction within one capture shares lineage; differing
claims remain unresolved. Legacy confidence, exact flags, stock or landed-cost
values do not establish configuration, merchant selection, availability or UK total.

Images are original generic SVG placeholders, labelled as illustrations rather than
product photographs. Merchant image URLs are never fetched. Width, dial colours and
delivered budget start unset. User-defined interpretations and hard/soft choices
persist; missing dimensions never satisfy a preference.

## Red / green receipts

Accepted seam: application API plus normal execution, controlled connector/time
edges, temporary SQLite and captured sends with the real dispatcher retained.
Fresh-process harness guards block real HTTP, native curl, browser backend and
process escapes. Unsafe legacy API fixtures and global/network tests were not run.

| Gate | Expected red observed | Green observed |
| --- | --- | --- |
| Independent discovery | `core.discovery` missing | Broad wristwatch acquisition finds AD2066 without a saved Watch; API retains origin/query/capture/field lineage after reload; no jobs or sends added |
| Actual query lineage | Legacy reported source ID loses raw query override in candidate origin | Shared acquisition retains executed source/query per lead, separately from the connector-reported source ID |
| Preferences | Preferences route 404 | `37.5` mm, `mint, salmon`, `120.25` GBP and hard/soft interpretations persist; stale revision 409, negative budget 422; three unknown fits remain visible |
| Coverage | Connector config exposed in receipt; parse error misclassified | Config omitted; success, successful-empty, failed, capped and disabled outcomes persist; default staged run searches nothing; five cohort leads retain original dates after failure; no alerts |
| Duplicate/restart | Duplicate result violates SQLite lead primary key | Repeated extraction shares lineage; absent price remains null; two leads and preferences survive a fresh OS process without reacquisition or sends |
| Actual feed | Pre-feature `/discover` has no heading/candidates; browser wait fails | Five illustrated rows, unknown totals, expandable evidence, keyboard save/reload, desktop and 375px without horizontal overflow, active/paused legacy queue navigation, no browser errors |
| Fixture identity | Browser driver rejects absent test-server marker before editing | Test-only marker confirms temporary storage and paused checks before any preference write; each browser run uses its own session |

The browser driver initially matched nested summaries ambiguously; its final locator
targets the row's direct evidence summary. The restart driver sets `TMPDIR` to the
marked shared temporary root's parent, preserving the existing storage guard.

Final source gates:

- **Passed:** 5 discovery + all 15 isolated monitoring workflows: **20 passed**.
  Monitoring includes seeded legacy migration, active/paused intent, matching,
  schedules, notifications, failed-source preservation and fresh-process restart.
- **Passed:** 25 existing frontend Vitest tests; TypeScript + Vite build. Existing
  bundle-size warning remains (main JS approximately 625 kB before gzip).
- **Passed:** focused Ruff on new modules, extracted acquisition, Watch executor
  and workflow/browser harness files; `git diff --check`.
- **Passed:** focused mypy, `--follow-imports=silent`, on new discovery/category/
  acquisition/storage/API modules and touched app/schema/executor: 10 source files.
- **Unchanged baseline:** Ruff on app/schema still reports seven existing findings.
  Compared `HEAD` and working source through Ruff stdin: app `UP035:1, UP017:2,
  BLE001:2`; schema `BLE001:2`, identical before/after.
- **Blocked:** ESLint 10 cannot find an `eslint.config.*` file. No config,
  suppressions or thresholds were added to bypass this repository setup issue.

## Repeatable verification

Run from this isolated checkout. Never point this workflow at a production database.
The harness creates temporary storage and clears configuration/credentials before
application import.

```sh
MONITORING_PYTHON=/Users/jay/.t3/worktrees/pricerecon/t3-7260bb2e/.venv/bin/python
PYTHONPATH="$PWD/src:$PWD" "$MONITORING_PYTHON" -m pytest -q tests/test_discovery_workflow.py tests/test_monitoring_workflow.py
```

In `frontend`, run `npm test -- --run` and `npm run build` using the existing
linked dependencies. Then start the retained fixture from the checkout root:

```sh
PYTHONPATH="$PWD/src:$PWD" "$MONITORING_PYTHON" -m tests.monitoring.discovery_ui_server --port 8877
```

In another terminal, run the retained driver with installed agent-browser and Google
Chrome; no browser download is needed:

```sh
python3 -m tests.monitoring.discovery_browser_check --port 8877
```

The real built application runs on `127.0.0.1:8877`, temporary SQLite, controlled
connectors, paused scheduler and captured sends. The five named cohort leads are
**original fictional test data**, not live attribute evidence. One source attempt
fails deliberately. Browser uses an isolated session and empty config, restricted
to loopback navigation. The prior two T3 snapshot timeouts and explicit task
instruction authorise this fallback. Installed CLI lacks `skills get core`; its
installed `--help` supplied the command reference.

The fixture-only `/api/offline-verification` marker is registered by the test server,
not the application. The driver refuses to edit a server without that marker.

Driver outputs `desktop.png`, `narrow.png`, `receipt.json` under the system temporary
directory's `pricerecon-ticket02-browser`, or `--artifacts PATH`. Reviewed copies:
[desktop](artifacts/watch-discovery/desktop.png),
[375px](artifacts/watch-discovery/narrow.png),
[browser receipt](artifacts/watch-discovery/receipt.json).
Stop the fixture with Ctrl-C. It asserts zero blocked-edge escapes, zero sends and
retention of the one enabled legacy job. Final observed server receipt:
`blocked_edges=[], notifications_sent=0, searches=3, temporary_storage=true`.

## Merger verification: 2026-10-27

Merger checkout: `/Users/jay/.t3/worktrees/pricerecon/watch-category-integration`,
branch `integration/watch-category-discovery`. Both this checkout at `15beae4`
and the implementer checkout at `2b8325c027566e945fd70287b1fc8953a2bd5939`
were clean before the merge. `15beae4` was the merge base and an ancestor of
the implementer HEAD. The reviewed 26-file diff contains discovery, the shared
acquisition extraction, additive schema/API/navigation changes, tests and receipts.

`git merge --no-ff 2b8325c027566e945fd70287b1fc8953a2bd5939` produced merge
`970bd255ab9f1caead2ed735be0f4ebe9e9ca4e6` with parents `15beae4` and
`2b8325c`, preserving history without conflicts. `git diff --exit-code 2b8325c HEAD`
then confirmed an identical tree. The following checks were rerun from integration
using the existing Python environment and integration frontend dependencies:

- **Passed:** the documented isolated pytest command: **20 passed in 23.47s**,
  comprising 5 discovery and all 15 legacy monitoring workflows. Temporary SQLite,
  controlled acquisition and captured deliveries remained behind the harness guards.
- **Passed:** `npm test -- --run`: **25 passed**.
- **Passed:** `npm run build`: TypeScript plus Vite, 633 modules; main JS
  624.84 kB before gzip. Existing greater-than-500-kB chunk warning remains.
- **Passed:** `python -m ruff check` on discovery API/category/model/storage/core,
  extracted acquisition, Watch executor and the discovery workflow/browser/harness
  files. `git diff --check 15beae4..HEAD` also passed.
- **Passed:** `python -m mypy --follow-imports=silent` on discovery API,
  category `__init__`/rules, acquisition, discovery core, Watch executor,
  discovery storage/model, app and schema: **10 source files**. Existing unused
  override notes remain.
- **Unchanged baseline:** compared Ruff code/message counts using `git show`
  plus Ruff stdin at `15beae4` and merged HEAD: app `UP035:1, UP017:2, BLE001:2`;
  schema `BLE001:2`. An initial comparison command could not find `ruff` on PATH;
  rerunning through the existing environment's `python -m ruff` passed.
- **Blocked:** `npm run lint`, exit 2: ESLint 10.12.0 cannot find an
  `eslint.config.*` file. No install, configuration change or suppression was made.
- **Reviewed retained browser proof:** both linked screenshots, receipt, fixture
  identity guard and driver assertions cover illustrated simultaneous candidates,
  keyboard save/reload, uncertainty/evidence, narrow overflow and legacy queue
  navigation. No substantive concern or source difference justified repeating it.
  This is inspection of prior browser evidence, not a new browser execution.

All five ticket02 checklist items are evidenced within the accepted offline seam;
the local issue is closed. Ticket03 was read and claimed for the parent continuation,
with its implementation checklist untouched. Only tracker/receipt documentation
was changed after the merge. The dirty original parent was not edited or used for
application execution; only its existing Python environment was reused. No broad
legacy API/global/live suite, credentials, accounts, production DB, install, push,
PR, deployment or activation was used. Collection remains staged, with no new
collection HTTP action or scheduler job.

Preservation readback: implementer remains clean at `2b8325c`; original parent
status is unchanged, with no staged diff and the same tracked-diff SHA-256 before
and after verification:
`38ab9795757655e9119022af759fe392bfb901bce1ce8175038fc6c0b73e8914`.

## Remaining gates

Ticket02 is **closed for deterministic offline acceptance after merger verification**.
This is agent-observed offline implementation proof, not buyer acceptance. Exact identity/
selection qualification is ticket03; public UK costs ticket04. Every current lead
has unresolved identity, unknown delivered total, unavailable usual price, null
savings and `alert_eligible=false`. Titles/artwork establish no size or colour fit.
Full observation history and richer adapter/partial/cache reports remain later
slices; these receipts are not an accepted longitudinal ledger or freshness policy.
Tracking and correction controls belong to their dependent tickets and are not
simulated here. Source permissions/retention, operating caps, live activation and
buyer walkthrough remain open. No live acquisition, credentials, accounts,
production DB, deployment, push or PR was used.
