# Ticket10 collection policy verification — 2026-10-27

Implementation branch: `t3/prioritise-tracking-policy`, isolated checkout
`/Users/jay/.t3/worktrees/pricerecon/t3-b6a21a65`.
Initial integration merge was a fast-forward to
`a69c4eedec3630769416bfac2a3af552705d993b`; ancestry was confirmed before edits.
The original dirty parent and ticket06/09 repair worktrees were not edited.
The parent's existing `t3-7260bb2e/.venv/bin/python` is reused with this checkout's
`src` and root on `PYTHONPATH`. `frontend/node_modules` links to integration's
existing dependencies. No installation, download, merchant network access,
credential/account action, production database, activation, deployment or push.

## Accepted seams and red/green evidence

Applied the TDD skill at the buyer-approved application API and normal execution
entry points, with the retained fresh-process `MonitoringHarness`, marked temp
SQLite, controlled clock, connector/HTTP edges and captured notification sends.
New workflows are in `tests/monitoring/collection_workflows.py`, invoked in fresh
children by `tests/test_collection_workflow.py`.

Observed red -> green tracers during this implementation:

| Tracer | Observed red | Result after implementation |
| --- | --- | --- |
| Missing operating policy | Reference labels admitted a search; expected blocked | `operating_policy_required`, zero connector calls, API gate |
| Shared priority | Third discovery search ran; expected capped | Discovery stops before tracking reserve; saved Watch intent unchanged |
| Storage exhaustion | Candidate persisted under zero storage grant | Evidence transaction rolls back; attempt capped; no send |
| Exact verification priority | Existing target query consumed discovery allowance | Reserved verification lane; baseline then crossing; one captured send |
| Legacy storage | Snapshot committed under zero storage grant | Snapshot/events transaction rejected before notification dispatch |
| Detail fallback | Fallback transport ran under zero fallback grant | Actual edge denied before send; page/detail/provider/global counters retained |
| Readback after storage rejection | Old target assessment remained above target | API withholds with `source_refresh_unavailable`; dated evidence retained |

Additional workflow checks cover actual eBay OAuth/search/401 retry through an
HTTPX `MockTransport`, concurrent sources, overlapping same-source runs, killed
process/restart, finite resumption, exhausted envelopes, changed-policy-label
bypass rejection, browser origin-accounting gate, absent AI policy and a real
one-second async execution deadline. These were added as green contract tracers
against the preceding vertical slices; no fabricated initial-red claim is made.
No xfails, suppressions, deleted workflows or reduced assertions were introduced.

The killed-process workflow exits at the controlled transport **after** durable
request debit. A fresh process observes its running lease, cannot immediately
retry, resumes once after supplied spacing, records the interrupted run, and
cannot refill the finite envelope or replay missed periods. Captured sends remain
zero in failure/recovery workflows. The verification-priority crossing captures
exactly one send through the existing notification owner.

## Implementation contract

`core/rate_limiter.py` now owns `DurableAdmission` alongside the legacy token
bucket. Migration **1.9** adds policy, usage and attempt tables in the existing
SQLite. `BEGIN IMMEDIATE` serializes shared reservations. No new scheduler,
queue, background worker, admission service, browser service or notification
owner was added. Existing APScheduler jobs, coalescing/time windows and Watch
execution are reused; a durable source lease and supplied spacing constrain their
actual acquisition edges, including startup/immediate jobs.

`operating_policy(...)` supplies a programmatic finite envelope. There is no HTTP
policy-writing or activation endpoint. It requires explicit owner, permission and
retention references, timezone-aware start/stop, run-time ceiling, recovery
spacing, global request/page/detail/retry/fallback/storage/time caps, per-provider
request caps and tracking reserves. These are caller-supplied values; there are no
production numerical budgets, freshness/cadence defaults or maintenance owner.
The retained test harness supplies a prominently synthetic policy so the original
workflows exercise the new boundary without granting live authority.

The envelope does not refill. Changing its version, values or references under
the same scope is rejected; a new scope is an explicit new grant. Reserving a
whole run-time ceiling is conservative and not refunded after a crash. Discovery
cannot consume tracking reserves. Persisted exact intent promotes only its
already-backed source/query to verification priority. Broader unmatched queries
remain discovery. Provider and global request costs commit atomically.

HTTPX request hooks charge before every mapped transport send, including OAuth,
redirects, repeated requests and explicitly tagged detail fallback edges. Repeated
identical requests consume retry capacity. Unknown request classifications and
unmapped connector lanes fail closed under the supplied envelope. eBay's native
HTTP lane and AliExpress's HTTP client construction receive the shared hook;
AliExpress operations without a reviewed classification remain blocked. Ticket11
may extend mappings; these hooks do not activate or semantically qualify a route.
Admission is a control signal that adapter `except Exception` retry/fallback code
cannot swallow. Cleanup stays under the same context/deadline, and a governed
cleanup failure removes fresh results before legacy diff/alert processing.

Storage accounting measures actual SQLite btree payload growth, including index
payload, through `dbstat` inside the evidence transaction. Missing `dbstat` gates
that operation. Discovery evidence, legacy snapshot/events and exact-target
assessment/event writes are checked before commit. Failed persistence never
manufactures a refreshed target assessment or sends an alert. Existing control
receipts retain the cap outcome without an unaccounted fallback evidence write.

`GET /api/discovery/collection` exposes supplied/blocked/expired policy state,
staged activation, global/provider usage, individual query/purpose/outcome,
next eligibility and dated last-completed acquisition with age. Failed/capped
attempts remain unrefreshed. Last-completed acquisition is explicitly **not** a
semantic qualification assertion. The small collapsed coverage component carries
these states, strict readback validation and policy gates to the buyer UI.
Existing discovery capture coverage retains separate blocked/failed/empty states.

Legacy saved-search intent and its established unsupplied-policy execution remain
compatible. When the shared policy is supplied, both Watch execution and discovery
use it. New discovery requires the policy in addition to its existing staged
permission/activation references. Transport health does not reset evidence times.
A failed exact-query verification also withholds old assessments on readback and
invalidates pending target delivery without changing durable crossing history.

## Operating gates and limits

This is bounded offline implementation proof, **not** an accepted production
operating envelope. Live activation remains staged and explicitly unauthorized.
The accepted operating-envelope research/resolution still applies.

- No measured sustainable breadth, freshness SLA, cadence, money budget,
  representative resource costs, retention period or accepted maintenance owner.
- Browser origin subrequests, contexts and elapsed browser resources cannot yet be
  bounded by these HTTP RPC hooks. Governed browser navigation is blocked before
  any backend invocation. No alternative backend/account/proxy is tried.
- There is no required AI acquisition stage. Absent explicit AI resource grants,
  an attempted AI-resource debit is blocked before external work. No AI provider
  lane is mapped or activated here.
- SQLite retained-payload accounting is **not** a filesystem/disk quota. Allocated
  free pages, journals/WAL, control metadata, logs, backups, retention/deletion and
  restore qualification need their own measured finite controls before live
  activation. They are not represented as zero-cost resources.
- Runtime expiry and run deadlines gate requests; unsupported native/curl/browser
  transports are not admitted merely because a connector exists. Mapping new
  real lanes requires actual-attempt accounting evidence and permission review.
- Per-source spacing protects shared routes, not a new business cadence. A capped
  or missed run records a gap; there is no catch-up mechanism.
- Complete source qualification, real cohort history and production notification
  delivery remain unproven. All fixture identities/prices/permissions are
  original synthetic data, not merchant or buyer acceptance.

## Commands and receipts

Run from this checkout with the existing interpreter:

```sh
env -i PATH=/Users/jay/.nvm/versions/node/v24.14.1/bin:/usr/bin:/bin \
  PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PWD/src:$PWD" \
  /Users/jay/.t3/worktrees/pricerecon/t3-7260bb2e/.venv/bin/python -m pytest -q \
  tests/test_collection_workflow.py tests/test_monitoring_workflow.py \
  tests/test_discovery_workflow.py tests/test_qualification_workflow.py \
  tests/test_cost_workflow.py tests/test_history_workflow.py \
  tests/test_coupon_workflow.py tests/test_tracking_workflow.py
```

Browser fixture and retained driver (fresh session; own loopback port 8896):

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PWD/src:$PWD" \
  /Users/jay/.t3/worktrees/pricerecon/t3-7260bb2e/.venv/bin/python \
  -m tests.monitoring.collection_ui_server --port 8896
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PWD/src:$PWD" \
  /Users/jay/.t3/worktrees/pricerecon/t3-7260bb2e/.venv/bin/python \
  -m tests.monitoring.collection_browser_check --port 8896 \
  --artifacts "$PWD/docs/testing/artifacts/watch-collection"
```

Uses installed Chrome and existing `agent-browser`; no preview tools. The installed
CLI reports `Unknown command: skills` for the skill stub's newer `skills get core`
command; retained driver and installed `--help` were used. Initial shell PATH also
omitted the existing `~/Library/pnpm/agent-browser`; the normal PATH resolved it.
Browser checks verify the temporary-fixture marker before inspection, keyboard
Enter, five retained candidates, capped/blocked/failed/empty states, aged evidence
after healthy transport, and no horizontal overflow at 1280x900 and 375x812.
Screenshots and API/snapshot receipt are under
[artifacts/watch-collection](artifacts/watch-collection/receipt.json). Each driver
closes its own fresh browser session; the fixture is stopped after verification.

Final combined verification and integration refresh are recorded below before
handoff. Ticket10 is not integrated into the parent branch or closed by this worker.

## Final merged-tree verification — 2026-10-27

Implementation commits `c4c5b31` and `b14500b`; local history-preserving merge
`b7f4be03bd53987e25b03f62d7e5567f0f4b2ce8` includes integration
`75f8a3a778e901e79f5ce1a1b76a26692d42a343`. Integration ancestry was confirmed
again before the final test run. Both 06/09 committed repairs were consumed,
without editing their worktrees, implementing their fixes, or changing their
acceptance records.

Final cleared-environment application suite: **96 passed in 85.25s**. This includes
all 85 retained legacy/discovery/qualification/cost/history/coupon/tracking
workflows and the 11 new collection workflows. Separate native limiter and
external-browser contract suite: **37 passed in 0.19s**, with 10 existing Pydantic
deprecation warnings. No real acquisition or transport was used.

An initial merged run passed 93 and failed three checks. Two were the retained
restart harness refusing macOS-parent `/var/folders/...` temp roots from children
whose cleared environment resolves `/tmp`; the documented `env -i` invocation
resolved these without changing the guard. One exposed this worker's readback
projection replacing the existing `acquisition_partial_or_reused` reason. The
projection now preserves existing withholding reasons when adding a collection
refresh gap. The three targeted checks then passed in 3.58s before the final
96-case rerun. An earlier development run overlapped model edits with child
imports and produced transient missing-policy-field failures; no such run is
presented as acceptance.

**25 frontend tests pass**. TypeScript/Vite production build passes, **640 modules**;
the retained large-chunk warning remains. Focused Ruff passes all new and
previously-clean touched files (16 source/workflow files). The retained
[baseline comparison](artifacts/watch-collection/ruff-baseline.json) shows no added
Ruff findings in the other touched legacy files; the native limiter's import
finding was removed. Focused `mypy --follow-imports=silent` passes all **13** touched
application source files checked, with only pre-existing unused-override notes.
Frontend lint still exits 2 because ESLint10 cannot find `eslint.config.*`; no
suppression/config workaround was introduced. Full-repository pytest was not run
because retained legacy fixtures may touch their configured DB/live edges; this
receipt uses the guarded application suite and controlled contract tests.

Final Chrome verification on source `b14500b` used isolated session
`ticket10-collection-abae9f24`, own loopback port **8896**, desktop **1280x900** and
narrow **375x812**. It passed all retained checks and closed that session. The
fixture stopped afterward; final guard receipt: `blocked_edges: []`,
`notifications_sent: 0`, `temporary_storage: true`. The process exits 130 on the
intentional Ctrl-C after printing that receipt; no fixture server remains running.
[UI receipt](artifacts/watch-collection/receipt.json) and
[source manifest](artifacts/watch-collection/source-manifest.json) bind the proof
to the tested application/fixture source and integration ancestor. Documentation
and receipt commits afterward do not change those source hashes.

No budget, freshness window, cadence, owner or production activation was inferred
from these results. Ticket10 remains for parent review/integration/acceptance;
this worker has not closed it or merged its branch back into integration.
