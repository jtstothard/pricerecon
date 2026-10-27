# Exact delivered-target tracking — 2026-10-27

Ticket 05 source/offline verification receipt. The parent merger owns integration
acceptance and ticket closure. Buyer walkthrough, live evidence and activation
remain unproven.

## Workspace and authority

Implementation checkout: `/Users/jay/.t3/worktrees/pricerecon/t3-c80e6d25`, branch
`t3/exact-product-tracking`. Before source edits, fast-forwarded the clean branch
to integration claim commit `375a4a4` and confirmed ancestry of closed-04 base
`c682d568b3ce49e99beaf9d1d325bea75165d954`. Used only committed integration
contracts. No sibling dirty source was imported; the original dirty parent
`t3-7260bb2e` was not edited. Its existing `.venv/bin/python` was reused with this
checkout's `src` and root on `PYTHONPATH`. This checkout's `frontend/node_modules`
is a symlink to integration's existing dependencies. No packages were installed.

Read the implementation spec, exact issue, glossary, contribution/engineering
standard, accepted watch-proof protocol/resolution, experience and operations
decisions, identity/cost research and retained monitoring/qualification/cost
receipts. Used the TDD skill at the already-approved application API plus normal
execution seam. All acquisition, time and sending edges below are controlled;
storage is marked temporary SQLite in fresh Python processes.

## Implemented behavior

`models/tracking.py`, `db/tracking.py`, `core/exact_tracking.py`, `api/tracking.py`
and the focused frontend tracking component own the slice. Track stores an
explicit configuration/capture/revision anchor, positive exact-decimal GBP
delivered target and explicit notification-channel choice. It creates no Watch,
scheduler job, source route or activation setting. Existing Watches retain their
queries, filtering, targets, enabled state, schedules and notifications.

HTTP intent routes are `POST/GET /api/discovery/tracking` and
`GET/PUT /api/discovery/tracking/{id}`. PUT compares the expected revision under
`BEGIN IMMEDIATE`. Creation validates the retained candidate/capture/binding and
the selected configuration revision. Equivalent later captures of the same
supported definition are allowed; changed/unsupported definitions, unknown
anchors, duplicate intent and obsolete edits fail closed. The feed carries
tracking projections separately from unqualified discovery lead claims.

Normal `execute_discovery(..., tracking_policy=...)` may evaluate targets only
under admitted programmatic execution. The default stays staged and cannot
collect or send. HTTP target/preferences writes cannot supply execution policy.
`TrackingPolicy` requires an explicit version, evidence age, allowed conditions,
quantity, destination nation/region and payment method. There are no production
freshness, cadence, cap or eligibility defaults. The controlled test policy is
synthetic: 7,200 seconds, new, one unit, England/synthetic-region and a fictional
GBP payment method. Those values are not operational recommendations.

Only a supported exact configuration and merchant binding, in-stock buy-now
offer, standalone verified public no-coupon GBP delivered total, matching buyer
scenario/preferences and fresh supporting evidence can move target price state.
The evaluator checks configuration/binding/offer/cost revisions and every
supporting observation time/expiry. Conditional/personal/payment/cashback totals,
legacy normalized item prices and unknown/stale/withdrawn evidence cannot become
verified delivered alerts. Health/retrieval timestamps do not renew observations.

The first qualified observation establishes a baseline, following the retained
engineering standard; Track itself never sends. At or below target, a subsequent
qualified crossing sends once. The same offer/price is suppressed; a further
drop below the reserved low or a fresh crossing after a qualified rise above
target can send again. Below-target oscillation does not re-alert an old low.
Target or policy changes require another baseline; an edit alone never alerts.
Withheld observations do not reset the previous qualified price or notified low.

Durable identity uses merchant/product/variation, seller, condition/details,
quantity and buyer scenario, excluding capture IDs and acquisition source/route.
Equivalent decimal prices compare numerically. Restart, duplicate routes,
unchanged source recovery and older replayed evidence do not create a new event.
Conflicting totals for the same offer from two routes in one capture are withheld.

## Notification ownership and recovery

Migration **1.6** adds tracking intent/price state and versioned links to existing
events. It makes `events.watch_id` nullable for the new exact-target event type,
retaining legacy IDs, indexes, references and the AUTOINCREMENT high-water mark.
The migration is transactional. No legacy Watch or notification configuration is
rewritten. Existing `notifications` gains a nullable unique delivery key; legacy
dispatch calls keep their prior behavior.

The existing dispatcher, event log and webhook/Telegram/Discord transports send
the new `exact_target_crossing` event, with an explicit **verified UK delivered**
message and lineage. The tracking event link holds target/evidence revisions,
not a second notification platform or scheduler. There is no background worker,
service, autonomous retry loop or new collection queue. Recovery runs only at
the admitted normal execution seam, or its explicit programmatic recovery entry.
No selected channels means no target sends, including global default routes.

Event reservation and price state commit together. Before each channel, the
dispatcher atomically rechecks target/invalidation/preference/offer/cost versions
and expiry, then durably claims the channel before external I/O. An in-flight
claim prevents target edits and participating corrections. A preference change
while the first channel is awaiting transport withholds the next channel.

A crash before a transport claim leaves a pending reservation recoverable once,
provided its original policy fingerprint, revisions and freshness still match.
A claimed channel is never automatically retried, even when its transport returns
false: an external recipient may have accepted a message before its ACK was lost.
API/UI delivery records distinguish pending, sent, withheld and ambiguous results.
There is **no exactly-once external delivery guarantee**.

`GET /api/discovery/tracking/{id}/deliveries` exposes the records.
`POST .../{id}/deliveries/{event_id}/resolve` accepts a revision-checked operator
resolution (`record_sent` or `abandon`) and explicit confirmation that the sending
process has stopped/no send remains in flight. The server cannot independently
prove that assertion or remote receipt. Resolution records knowledge, retains
the target and suppression, and never resends. The UI explains these limits.

## Extension contracts for parallel/later tickets

- **06 history:** `TrackingAssessment`/`TargetEvent.assessment` retain capture,
  configuration/binding/offer/cost revisions, preference revision, policy version
  and fingerprint, validity limit and delivered amount. History can refer to
  these decisions without treating events or `exact_tracking_prices` as an
  observation ledger. No history projection/interface was implemented here.
- **09 coupons:** `assess_offer` consumes the cost owner's typed, revisioned
  `CostScenario` inputs. This slice accepts only standalone verified
  `public_no_coupon`. A future accepted coupon adapter must supply exact public
  payable scenario/evidence and extend the scenario-selection seam while keeping
  the same binding/configuration/revision/freshness gates, durable offer-price
  identity and dispatcher. Advertised terms, conditional eligibility and personal
  benefits cannot enter by renaming a price. No coupon engine was implemented.
- **07 corrections:** call `invalidate_configuration_tracking(connection,
  configuration_id, reason)` in the caller's `BEGIN IMMEDIATE` correction
  transaction. It increments invalidation/intent revisions, retains the original
  subject and target, and withholds dependent alerts. It raises `TrackingConflict`
  during an in-flight send so the caller rolls back rather than publishing a
  contradictory correction. It cannot retract an already externally accepted
  send. Relinking/revalidating corrected evidence belongs to 07; this slice does
  not restore or relabel old prices. UI and API already expose invalidation.

## Red/green receipts

Expected outcomes were stated in application workflows before implementing each
behavioral repair. No xfails/skips/suppressions were introduced.

| Tracer | Observed red | Observed green |
| --- | --- | --- |
| Discovery → Track → edit | POST returned 405; no intent API | Positive GBP target persists; stale edit 409; bad decimal 422; unknown anchor 404; Watches/jobs/searches unchanged |
| Qualified crossings | Normal execution rejected the new policy argument | Delivered £70.10 → £58.10 sends; repeat suppressed; £57.10 sends; oscillation suppressed; £70.10 → £58.10 sends again |
| Withholding/read-time expiry | After advancing the clock, API still said above-target | Unknown/conditional costs, stale/expired evidence, unresolved identity/SKU, withdrawal, payment mismatch, missing policy and preference mismatch withhold; feed/API expire together |
| Restart/routes | First launcher was rejected by the existing temp-root guard because parent TMPDIR differed; corrected to marked `/tmp` storage | Fresh process retains target/event/log state; duplicate decimal representations/routes send zero; a new qualifying drop sends once; old rise cannot rearm |
| Pre-send interruption | Restart acquired a newer revision before resuming and lost the pending send | Admitted normal execution first recovers a still-valid pre-send reservation once, then suppresses the identical capture |
| External crash | No reconciliation API (405) | Captured external accept followed by process interruption remains ambiguous across restart; no automatic replay; explicit abandon unlocks later edits without resend |
| Overlap/invalidation | Second channel still sent after preferences changed during first send | Target edit 409 during transport; changed preferences withhold next channel; correction seam retains target and invalidates further sends |
| Reused policy label | Recovery sent using changed allowed conditions with the same version label | Full supplied policy fingerprint differs, so pending event is withheld |
| Conflicting routes/channel opt-in | Two different totals for the same merchant selection could notify | Conflicting route totals withheld; no selected channels cannot inherit a global target-event send |
| Migration high-water | New event reused an ID below a deleted event 25 | Retained legacy event 15 is unchanged; next new event is above 25; legacy Watch events remain separately queryable |
| Browser capture revisions | Track card rejected because another offer held a newer but equivalent configuration revision | Capture/binding anchor plus compatible latest definition permits saving; wrong revision remains rejected |

Harness-setup failures were corrected before counting behavioral evidence. The
first withholding tracer accidentally imported application code before entering
the harness and was rejected by its fresh-process guard. The first crossing
implementation also exposed a strict delivery readback-model mismatch, corrected
before its green result. Browser attempt two completed two captured sends but a
title-based locator then timed out; the retained driver now uses candidate IDs
and the fixture preserves the named cohort title. None of those failed attempts
is counted as a passing workflow.

## Verification commands and final results

Build before application imports; never overlap a dist rebuild with fixture/tests:

```sh
cd frontend
npm run build
npm test -- --run
```

Run the retained 48 application workflows plus the 10 tracking workflows from root:

```sh
env -i PATH=/Users/jay/.nvm/versions/node/v24.14.1/bin:/usr/bin:/bin \
  PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PWD/src:$PWD" \
  /Users/jay/.t3/worktrees/pricerecon/t3-7260bb2e/.venv/bin/python \
  -m pytest -q tests/test_cost_workflow.py tests/test_qualification_workflow.py \
  tests/test_discovery_workflow.py tests/test_monitoring_workflow.py \
  tests/test_tracking_workflow.py
```

Final combined result: **58 passed in 87.37s**, all retained 48 application
workflows plus all 10 tracking workflows. No application workflows were removed,
skipped or xfailed. An earlier combined run passed 55 tests in 92.53s before the
last three tracking tracers were added.

Frontend build passes TypeScript/Vite, 635 modules; the existing large-chunk
warning remains. All **25 frontend tests** pass. Focused Ruff passes the 14
new/previously-clean source/harness/driver files. Focused mypy with
`--follow-imports=silent` passes all 11 changed application source files, with
existing unused-override notes. The other four changed legacy files retain
exactly their pre-existing 41 Ruff findings (same codes/counts at `375a4a4` and
working source: app 5, notifications 8, schema 2, Watch models 26). No suppressions
or unrelated cleanup were added. Frontend lint remains blocked by the existing
ESLint 10 missing `eslint.config.*` failure, exit 2. Full repository pytest is not
invoked because legacy fixtures can touch their configured DB/live edges; this
receipt uses the retained guarded application suite.

## Browser receipt

T3 preview status/open succeeded for an isolated incognito tab, but two snapshot
calls each returned `Preview automation snapshot timed out after 15000ms.` Used
the explicitly authorized existing Chrome/agent-browser fallback. Its installed
CLI returns `Unknown command: skills` for `skills get core`; local `--help` and the
retained driver document the commands used. No browser was installed.

```sh
env -i PATH=/Users/jay/.nvm/versions/node/v24.14.1/bin:/usr/bin:/bin \
  PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PWD/src:$PWD" \
  /Users/jay/.t3/worktrees/pricerecon/t3-7260bb2e/.venv/bin/python \
  -m tests.monitoring.discovery_ui_server --tracking --port 8885

PYTHONPATH="$PWD/src:$PWD" \
  /Users/jay/.t3/worktrees/pricerecon/t3-7260bb2e/.venv/bin/python \
  -m tests.monitoring.discovery_browser_check --tracking --port 8885 \
  --artifacts /tmp/pricerecon-ticket05-browser
```

Each driver run has a unique browser session and checks the exact fixture identity, temporary storage,
disabled automatic checks and blocked-edge state before any write. Test-only
controlled step requests additionally compare a unique fixture token. The server
uses only loopback, fictional evidence, the existing temporary harness and
captured send transports. Its step route is never mounted in the application.

The retained browser receipt covers keyboard Track, editing/reload, explicit
channel selection, missing-policy withholding, above-target → crossing → duplicate
routes → further drop, delivery explanations, stale readback and preserved legacy
intent. Captured send counts are **0 → 1 → 1 → 2**. Both 1280×900 and 375×812 pass with
no horizontal overflow or browser page errors. Screenshots were visually inspected;
tracking details use the feed width rather than the narrow price column.

## Remaining gates

Collection is staged. No live acquisition, credentials/accounts, production DB,
source activation, network collection, installs/downloads, deployment, push, PR,
delegation or buyer acceptance occurred. Only local source/test preparation,
loopback browser verification and authorized local commits/merges are in scope.
Real source rights, operational limits/freshness/cadence, coupon success, retained
live history, ticket 07 corrections, live transport behavior and buyer walkthrough
remain separate gates. The first-observation baseline and ambiguous-transport
tradeoffs above describe implemented behavior, not invented buyer acceptance.
