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

## Merger disposition — 2026-10-27

**10 remains open for shared-admission repair; 11 remains blocked and unclaimed.**
The retained suite passes, but the additional acceptance probes demonstrate that
an applicable finite grant does not govern callers outside its ContextVar. This
is independent of 07's retained multi-configuration defect. No 07 repair or 11
implementation was performed, and no collection failure was excused as a 07 gap.

### Integration and conflict resolution

Confirmed clean integration `f561d76d55bf037ddec705ad488ebbc403934306` and clean
source `072a2f873b5c0ac071401d2eabc6a912d0e5aaa4`, on the named branches/checkouts.
Both contain `75f8a3a`; source lacked integration's correction source `89ebd79`.
Read the spec, issue10, accepted operating-envelope decision/research, source
receipt/manifest, engineering standard and current 07 merger disposition.

Refreshed the existing source checkout with a history-preserving merge of
`f561d76` into source, producing `fd026255bf98dd7c66a58d06afc31c297bb47731`.
Four actual conflicts were resolved:

- Discovery page imports both CollectionCoverage and IdentityCorrection; both
  components remain connected to their existing page flows.
- Schema initialization calls both collection and correction migrations (1.9
  and 2.0); neither table owner was replaced.
- Discovery persistence runs 07 publication validation inside the transaction
  **before** 10's retained-payload growth debit. Publication/invalidation writes
  therefore participate in that debit before commit.
- The guarded harness imports and patches both storage owners' clocks.

Reviewed automatic merges in acquisition publication, exact tracking and tracking
storage; both correction revision withdrawal and admission/readback wiring remain.
Merged full refreshed source history into integration using `--no-ff`, producing
`5cca8599c91a742829db695faab12915c842c3df`, with first parent `f561d76` and second
parent `fd02625`. Source's tree equals this merged tree. No new checkout was made.
Original dirty parent and 07 repair worktree were not edited.

All **26 original source-manifest entries** match `072a2f8`. Nineteen still match
the integrated tree; seven differ through 07 integration/conflict resolution.
The exact paths are retained in
[the manifest comparison](artifacts/watch-collection/merger-manifest-check.json).
The page conflict requires fresh frontend and actual UI proof; source evidence
was not substituted for those checks.

### Combined verification

Ran from integration, with the existing parent interpreter and this checkout's
source, in the documented cleared environment:

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

**106 passed in 104.02s**, with no skips/xfails. This includes source's 96 and
07's ten correction cases. All retained assertions remain. No full-repository
pytest or potentially live/configured-database fixture was used.

- Requested limiter/external-browser contracts: **37 passed in 0.23s**, ten
  existing Pydantic deprecation warnings. An earlier broader invocation also
  included BrowserClient: **73 passed in 0.47s**. That broader run emitted an
  additional unawaited `_FakeStream.readline` warning in its timeout fixture;
  no warning suppression or unrelated repair was made.
- Focused Ruff checks cover **24 Python files**: **17 clean**, 98 inherited
  diagnostics across seven legacy files, **zero added** rule/message multiset
  entries against `f561d76`. New probe passes Ruff. See
  [per-file comparison](artifacts/watch-collection/merger-ruff.json).
- Focused `mypy --follow-imports=silent` passes the 13 touched application files
  listed in the merger verification JSON, with existing unused-override notes.
- Repeated frontend: **25 tests passed**; TypeScript/Vite build passed,
  **642 modules**, retained large-chunk warning. Existing ESLint10 missing-config
  blockage remains documented; it was not suppressed or repaired.
- Repeated guarded Chrome collection proof on own port 8896 and correction proof
  on own port 8897: both pass at **1280x900** and **375x812**. Collection checks
  cover keyboard expansion, five candidates, capped/blocked/failed/empty states,
  aged evidence and no horizontal overflow. Correction checks cover target
  intent, original evidence, cost/coupon/history withdrawal, reload, stale edit
  rejection, dispute/resolution and no overflow. Actual desktop collection and
  narrow correction screenshots were visually inspected.
- Both drivers closed their own isolated browser sessions. Both servers stopped;
  shutdown receipts record `blocked_edges=[]`, zero notifications and temporary
  storage. Collection server exit130 is its intentional Ctrl-C; correction
  server exit0. See [collection UI](artifacts/watch-collection/merger-ui/receipt.json)
  and [correction UI](artifacts/watch-collection/merger-correction-ui/receipt.json).

### Reproduced shared-admission failure and controls

[The retained probe](../../tests/monitoring/collection_merger_probe.py) uses the
unchanged marked temporary-SQLite harness, controlled clock, normal Watch API and
registered scheduler job callback. A synthetic `http_v1` connector uses the actual
shared HTTPX request hook and `MockTransport`; no live provider or credentials
are involved. API data, captured transport sends and API-visible ledger establish
the results; no direct ledger mutation or private limiter call supplies the proof.

The finite policy covers global and provider requests, pages/details/retries/
fallbacks/storage/time with a one-request cap, zero recovery spacing and explicit
synthetic owner/permission/retention references. It is active at the controlled
time. The initial in-context call sends once and persists usage1. A second call
in that same context is capped before transport. Then:

- An independent API request task created with an empty Context, while the parent
  task still holds the supplied grant, sends again: **2 actual sends versus cap1**.
  Global/provider usage and durable attempts remain unchanged.
- The registered scheduler job callback in an independent context also sends
  again: **2 actual sends versus cap1**, unchanged ledger and attempts.
- A fresh process sharing the marked database reads the persisted exhausted grant
  when supplied for inspection, then executes the Watch API **without** the
  context: **1 additional send versus 0 remaining**, unchanged persisted usage1.
  This process imports the app only after installing the existing isolation guard.

Each outside-context read reports `state=blocked`, `operating_policy_required`,
no policy scope/usage, even though its Watch request just performed the controlled
transport. These three probes retain `result=failed` and exit1 at the acceptance
assertion. Legacy query, raw source query, enabled state, sources, filters,
schedule and notifications remain unchanged; notifications and escaped edges are
zero. [Probe result summary](artifacts/watch-collection/merger-probe-results.json).

Positive controls pass: a policy-less legacy run **with no persisted grant** sends
once, preserving established monitoring intent; a mapped search -> detail redirect
under the supplied one-request policy debits the search before send and rejects
the redirect before its transport. Usage remains requests1/pages1/details0, with
`resource_exhausted:requests`. Existing collection cases independently cover real
eBay OAuth/search/401 retry, detail fallback, concurrent demand, storage rollback,
last-good/readback withholding, reserved exact verification, crash/resume,
unsupported browser/unsupplied AI gates and finite timeout.

Run any standalone case with the following command (three acceptance cases exit1;
`legacy_no_grant` and `redirect` exit0):

```sh
env -i PATH=/Users/jay/.nvm/versions/node/v24.14.1/bin:/usr/bin:/bin \
  PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PWD/src:$PWD" \
  /Users/jay/.t3/worktrees/pricerecon/t3-7260bb2e/.venv/bin/python \
  -m tests.monitoring.collection_merger_probe CASE \
  "$PWD/docs/testing/artifacts/watch-collection/merger-CASE.json"
```

Use `context_api` and `context_scheduler` for independent same-process contexts.
For the fresh-process case, create a `pricerecon-offline-*` directory under `/tmp`,
write `.offline-monitoring` containing `ticket01-test-storage\n` (an actual final
newline), and run `process_seed` then `process_resume` as separate invocations
with `--storage /tmp/pricerecon-offline-...`. Seed exits0; resume exits1. Each
controlled acceptance failure is retained rather than xfailed or counted green.

`collection_policy.current_policy()` only reads its ContextVar. `acquire_sources`
constructs `budget=None` when it is absent; `account_request`, browser gates and
storage gates consequently have no durable admission in that execution context.
Persistence currently protects **participants supplied the policy**, not all
applicable consumers of the provider. A ContextVar design alone did not establish
failure: the concrete probes above do. This is incomplete shared admission, not
accepted optional enforcement. Repair must resolve/apply the applicable durable
grant or withhold an ambiguous/out-of-context caller before external work, while
preserving legacy intent and the no-grant compatibility control. No particular
new service or architecture is prescribed. The merger did not implement a repair.

### Retained prerequisites

Browser origin subrequests/resources and unmapped native/AI acquisition remain
unsupported; under the supplied context they are blocked before work and are not
counted as zero-cost supported lanes. Out-of-context enforcement is the open
shared-admission defect above. Finite runtime/spacing and no automatic catch-up
are demonstrated only for participating executions, not complete shared admission.

SQLite btree payload growth is not physical disk allocation or a log/backup quota.
Free pages, journals/WAL, control metadata, logs, retention/deletion, backups and
restore qualification remain explicit measured finite prerequisites. No affordable
breadth/cadence, source permission/retention authority, maintenance owner, live
history/offers, delivery, buyer walkthrough or production operating acceptance is
inferred from these offline results. Collection stays staged.

No installs/downloads, merchant/external network/live collection, real credentials
or accounts, production DB, activation, deployment, push, PR, delegation or unrelated
cleanup occurred. Only the known source refresh/conflict merge and integration
merge/probe/receipt/tracker changes were made. 07 stays open with its isolated
repair owner; no 11 claim or implementation occurred.


## Shared-grant repair handoff — 2026-10-27

Implementation branch `t3/shared-grant-bypass-repair`, isolated checkout
`/Users/jay/.t3/worktrees/pricerecon/t3-b00df60d`. Before edits this clean checkout
fast-forward merged `integration/watch-category-discovery` at
`f8ff7e5024401991ca33b9bf08468476dc708227`; `merge-base --is-ancestor` passed.
The original dirty parent, integration checkout and 07 repair checkout were not
edited. This is a local implementation handoff, not merger acceptance or ticket
closure. The earlier merger disposition and operating prerequisites remain the
acceptance record until independent integration review.

### Durable selection and enforcement

The existing `DurableAdmission` owner now selects one immutable database-wide
envelope. Schema **2.1** adds only `collection_policy_selection`; 07's **2.0**
remains untouched. Selection and the initial policy commit in a separate
`BEGIN IMMEDIATE` transaction before acquisition or a reservable debit. A first
request/provider/time denial, expired first grant, evidence rollback or restart
cannot restore never-configured eligibility. Usage is still atomic and finite;
there is no refill, refund, automatic new scope, catch-up, scheduler or queue.

`current_policy()` now resolves persisted selection. `supplied_policy()` exposes
only the caller's optional ContextVar for diagnostics. An absent context or
explicit `operating_policy(None)` resolves the same existing envelope. Supplied
values must equal that envelope, including scope, caps, version and references;
a different scope cannot silently replace it. There is deliberately no grant
renewal/reconciliation or policy-writing HTTP endpoint in this repair. A later
explicitly designed transition would require its own authority and accounting
contract. This supersedes the earlier implementation description that treated a
new supplied scope alone as sufficient to change the shared grant.

A single historical policy is selected during startup migration. Multiple
historical policies are ambiguous and block work. Missing selected payloads,
malformed payloads, mismatched identities or orphaned prior accounting fail
closed; a supplied policy cannot silently repair or replace them. Selection
survives removal of the selected payload. Provider lanes absent from the selected
grant remain gated. A truly never-configured database with no selection, policies,
usage or attempts retains existing saved-search monitoring behavior; discovery
still requires operating policy and its separate admission prerequisites.

API requests, registered scheduler callbacks and new processes resolve selection
before connector construction. Existing actual-edge accounting remains on their
resolved admission through OAuth, retries, redirects, fallbacks, cleanup and
persistence. A hooked transport/browser/resource request without a run admission
also checks durable selection and blocks governed work before transport. It
cannot inherit legacy eligibility merely from an empty active-admission ContextVar.
Discovery, snapshot/event persistence, exact assessment and pending-target dispatch
now resolve the same durable envelope through their existing policy gates.

`GET /api/discovery/collection` reports the selected grant and real usage outside
caller policy contexts. Expired and damaged/ambiguous state remains visible with
its gate and retained attempts. Watch checks denied by the policy/persistence
boundary return a structured `blocked` or `capped` response with original error
and acquisition outcomes, rather than a generic HTTP500. They do not advance a
successful-check timestamp. Existing response shape and collection UI parser
support these states; no frontend source change or new activation route is needed.
Old listings/evidence and saved intent remain retained; capped/blocked attempts
are unrefreshed, not successful empty markets.

### Exact red and green evidence

Applied the TDD skill at the explicitly approved API and normal-execution seams,
with controlled transport/time and temporary SQLite. No private limiter method or
fabricated usage establishes the results. Retained merger probes were first run
unchanged on `f8ff7e5`: `context_api`, `context_scheduler` and `process_resume` each
exit1 at the extra-transport assertion. The first two send twice under cap1;
resume sends once with zero remaining. `process_seed` exits0.

The same transport/API/scheduler/process probes now exit0. Outside API readback
must equal supplied readback, provider/request usage stays at1, a denied attempt
is retained, and its conservative ten-second run reservation is counted. The
probe's former whole-ledger-equality assertion was strengthened to require this
accounted denial; asserting unchanged attempts would conceal the repaired
behavior. Raw-context assertions now use `supplied_policy()` so they continue to
prove the caller supplied no policy. The no-grant legacy and actual redirect
controls still pass: one legacy send without governing state; redirect denied
before its second edge with request/page usage1 and detail usage0.

Exact JSON evidence is under
[shared-grant-repair](artifacts/watch-collection/shared-grant-repair/verification.json):
`red-context_api.json`, `red-context_scheduler.json`, `red-process_seed.json`,
`red-process_resume.json` and matching `green-*.json`, plus
`green-legacy_no_grant.json` and `green-redirect.json`.

Additional regressions are in `tests/monitoring/shared_grant_workflows.py` and
`tests/test_shared_grant_workflow.py`. Baseline-source replay uses a temporary
`git archive` of `f8ff7e5:src` with the current controlled drivers; its exact
failures and the passing full legacy-intent control are in `red-additional.json`.
These cover remaining allowance under explicit None, exhaustion, expiry, expired
first grant, zero first elapsed/request/provider denial, changed scope/values,
independent-context concurrency, standalone transport/browser/AI-resource gates,
and missing/invalid/ambiguous persisted policy. Further green checks cover
zero-first-denial fresh-process resumption, two simultaneous independent processes
sharing one provider/global allowance, and startup migration of single/ambiguous
historical grants. Those additional process/migration checks are green coverage;
no separate initial-red claim is made for them.

The new `legacy_intent` positive control runs every retained legacy workflow
assertion with `operating_envelope=False`: filters, raw queries, enabled/paused
state, schedule, editing, baseline, real captured price-drop channels, no duplicate
send, listings/history and restart. The original governed legacy case also
remains. Nothing weakens the missing-policy discovery regression.

Two fixture adjustments were necessary and retain or strengthen assertions:

- Standalone external-browser contracts now initialize a temporary SQLite with
  genuinely empty collection state instead of consulting an uninitialized
  workspace database. Every original browser assertion remains. New teardown
  assertions require the operating-policy-required discovery gate and empty
  scope, usage, provider usage and attempts. These contracts do not represent an
  already-governed database with its required policy missing; dedicated damaged
  policy workflows test that denial separately.
- `target_storage_readback` no longer switches to a second zero-storage scope.
  It supplies one immutable synthetic 200000-byte envelope from the outset, then
  exceeds it with a 300000-character evidence title. Original above-target,
  withheld, `source_refresh_unavailable` and no-send assertions remain; new
  assertions require the exact storage-exhaustion reason, original scope and
  usage within its original cap. No usage/ledger reset or internal debit mock.

### Verification and remaining gates

The cleared-environment combined command below passed **126 workflows in
122.89s**: all **106 retained** plus the first **20 added**. The two subsequently
added migration workflows pass separately in **1.61s**. After the final UTC alias
lint fix, all seven affected expiry/changed/missing/invalid/ambiguous API cases
pass again in **5.45s**, including the unchanged last-check timestamp assertion. There are **128 passing workflows** across these runs,
no skipped/xfail cases or removed assertions. Do not represent these as one
128-case invocation.

```sh
env -i PATH=/Users/jay/.nvm/versions/node/v24.14.1/bin:/usr/bin:/bin \
  PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PWD/src:$PWD" \
  /Users/jay/.t3/worktrees/pricerecon/t3-7260bb2e/.venv/bin/python -m pytest -q \
  tests/test_collection_workflow.py tests/test_monitoring_workflow.py \
  tests/test_discovery_workflow.py tests/test_qualification_workflow.py \
  tests/test_cost_workflow.py tests/test_history_workflow.py \
  tests/test_coupon_workflow.py tests/test_tracking_workflow.py \
  tests/test_correction_workflow.py tests/test_shared_grant_workflow.py
```

The command now collects128, because the migration cases were added after the
126-case run. The fresh-child driver is unchanged in its isolation guard; all
application imports occur after guarded temporary storage is selected.

- Exact native limiter/external-browser suite: **37 passed in 0.37s**, ten existing
  Pydantic deprecation warnings (`test_rate_limiter.py`, `test_external_browser.py`).
- Focused mypy: **14 source files pass**, existing unused-override notes only.
- Focused Ruff: **17 changed Python files**, 15 clean, 18 inherited diagnostics
  across two files, **zero added** code/message multiset entries against
  `f8ff7e5`. Exact comparison: `shared-grant-repair/ruff.json`. No suppressions.
- Frontend: **25 tests pass**, TypeScript/Vite build passes, **642 modules**;
  retained large-chunk warning. Existing integration node_modules were linked,
  not installed. No frontend edits, preview tools or new browser/UI claim.
- `git diff --check` passes. Existing Python dependencies were reused. No full
  repository pytest or potentially live fixture was run.

Development failures were retained honestly: the first combined run had104 passes
and two failures (Node absent from the cleared PATH, and the old scope-switching
storage fixture); both were resolved as described before the final combined run.
The standalone browser suite initially lacked a database fixture and failed closed;
it created an empty worker-local SQLite file, which was removed before adding the
temporary fixture. No configured/production database was involved. Early new tests
also exposed the generic HTTP500 denial response, now covered by structured
blocked/capped assertions. No failed run is presented as acceptance.

Operating limitations from the merger receipt remain: unmapped browser origin,
native and AI acquisition lanes, physical disk/WAL/log/control-metadata quotas,
retention/deletion/backups/restore, source rights, measured sustainable cadence,
costs and maintenance ownership, live history/offers/notification acceptance and
buyer activation. This repair is offline shared-policy enforcement proof, not
an accepted production envelope. 07 remains separately owned and open; its known
configuration-scope gap was not repaired here. No integration merge or ticket
closure was performed by this implementation worker. No install/download,
external network/live collection, credentials/accounts, production DB, activation,
deployment, push, PR or delegation occurred. Local commits are authorized by the
parent task. Final local commit and latest-integration ancestry receipts are
recorded alongside this handoff.
