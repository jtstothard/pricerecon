# Retained observation history — ticket06 offline receipt

Dated **2026-10-27**. Implementation for
[ticket06](../../.scratch/watch-category-discovery/issues/06-show-observation-history.md)
under the [accepted specification](../specs/watch-category-discovery.md).
Parent merger owns integration acceptance and ticket closure. This receipt does
not claim buyer acceptance, real longitudinal evidence or live source approval.

## Scope and identity

Worktree `/Users/jay/.t3/worktrees/pricerecon/t3-0c43fde9`, final branch
`t3/observation-history` (initially `t3/0c43fde9`). Before edits, fast-forwarded from `ef86af6` to integration claim
`375a4a474a77e374f95d5c1318445f44860c0733`. Confirmed closed04 base
`c682d568b3ce49e99beaf9d1d325bea75165d954` is an ancestor. The original dirty
parent and integration checkout were not edited. No sibling dirty code imported.

Used the TDD skill at the already-approved application API and normal execution
seam. The existing `MonitoringHarness` supplies controlled acquisition and time,
marked temporary SQLite, paused automatic checks, blocked outgoing transports,
and captured sends. Application processes start with this worktree's source on
`PYTHONPATH`, using the parent's existing `.venv`. Frontend dependencies are a
local symlink to integration's installed `node_modules`. No installs, downloads,
credentials, accounts, merchant requests, production DB access, deployment,
activation, push, PR or delegation occurred.

## Implemented behavior

- `models/history.py` and `db/history.py` project the retained capture, lead,
  configuration, binding, offer and cost revisions. No copied observation ledger,
  replacement scheduler, queue or notification owner was added. API/feed reads
  hold a SQLite read transaction while assembling revision associations.
- `GET /api/discovery/candidates/{candidate_id}/history` exposes every retained
  offer record, including initial, unchanged, increased and decreased public
  standalone totals. Different configurations, purchase contexts, currencies,
  condition, quantities and policies form separate bases. Unknown/conditional
  totals remain unqualified records, never zero-price samples or price changes.
- Full exact revisions, field evidence, safe evidence pointers, monetary
  components, FX, benefits, context, availability, condition, quantity,
  destination, policy versions and derivation lineage remain available.
  `supported_at_capture` describes historical support only: `current_eligible`
  is always false and freshness remains unvalidated.
- Duplicate price/availability capture identity is scoped to the selected
  merchant/product/variation, across routes and candidate IDs. Adding extraction
  claims cannot manufacture independence. Retained configuration and selection
  definitions can support a genuinely new offer capture without making it a
  duplicate. Last-good age uses the oldest retained offer/cost observation time;
  replay, cache retrieval or a failed attempt cannot refresh it.
- Existing acquisition reports gain explicit partial/cache states, reason,
  completeness and original-cache capture identity. Mutated reports are
  revalidated at the existing acquisition boundary. Failed, blocked, capped,
  staged, empty, partial and cached attempts remain distinguishable; source
  health remains owned by the existing acquisition lifecycle. Real adapter
  qualification and integration of those statuses are later source work (11).
- Attempts use the same source/executed-query scope. Successful absence means
  not returned in that scope, never sold or continuously unavailable. Gaps
  explicitly mark intervals between samples and the open interval since the
  latest sample. No expected cadence, interpolation, forward fill or invented
  missing scheduled checks is supplied.
- Feed candidates carry a typed history summary with last-good age/validity.
  The buyer's existing evidence panel gains an expandable observation and gap
  view with full historical monetary/context/provenance details. Failures and
  acquisition attempts are shown separately from observations and alert events.
- New normal captures carry `observation-history-v1`. Older capture records
  default to `legacy_unqualified`; saved snapshots, legacy price rows and alert
  events are never backfilled as qualified observations. Cold start keeps usual
  price unavailable and savings null. Synthetic evidence is explicitly labelled
  and cannot become market history, however many synthetic dates are supplied.
- Additive migration **1.7** creates only exact-revision history invalidation
  references. The future correction owner can append a withdrawal inside its
  transaction with `append_history_invalidation`; duplicate IDs cannot overwrite
  earlier withdrawals. API qualification is withdrawn when any exact dependency
  is invalidated, while original offers/costs/revision associations survive.
  There is no correction write API, identity remapping, target or coupon owner
  here. Ticket07 must connect its correction transaction to this contract.

## Red / green observations

Expected and observed behavior through the application seam:

| Cycle | Observed red | Observed green |
| --- | --- | --- |
| Retained prices | History GET returned 404 | Four controlled captures retain `50.10`, `50.10`, `60.10`, `40.10` GBP with initial/unchanged/increased/decreased labels and exact revisions |
| Acquisition gaps | Typed report rejected partial/cache metadata | Duplicate, cache, partial, failure, cap, empty and unobserved intervals remain explicit; cached capture retains its original time |
| Copied extraction | Adding another capture ID to copied assertions incorrectly removed duplicate status | Original price/availability acquisition still owns the observation; copied evidence is excluded |
| Retained definitions | Reusing older configuration/selection evidence wrongly made a fresh offer a duplicate | A new price/availability capture records the increase while preserving the exact older definition associations |
| Browser states | Feed row wait timed out because its decoder rejected partial/cache outcomes | New source states decode, history opens and renders all dated states and gaps |

Migration/restart was additionally verified across **three fresh processes**:
seeded old captures and legacy watches/snapshots/events/history; migrated and
read them without reacquisition; appended an exact cost-revision withdrawal;
restarted and verified withdrawn qualification with identical original offers,
costs and dependencies. Legacy notification delivery during seed creation used
three captured transports; later migration/read/restart phases sent none.
Unknown and hostile-looking history IDs return 404, and POST history returns
405. A malformed cache report becomes a typed parse failure; unrelated-query
failure does not pollute the candidate's checked coverage. Quantity changes do
not masquerade as price increases. Cross-source copies preserve one original
merchant capture identity.

The first inherited-environment regression run passed 51 cases and failed the
old cost restart launcher's temporary-directory guard: its parent inherited
macOS `TMPDIR` while its child intentionally cleared the environment. The same
case passed with the clean environment already used in prior receipts. No guard
was removed or weakened. Final application verification uses that clean process
environment; the new history launcher also binds shared storage's temporary root
explicitly.

## Reproduction

Build sequentially **before application imports**; do not rebuild while a fixture
is running. Final checks use only installed tools:

```sh
(cd frontend && npm run build)
env -i PATH=/opt/homebrew/bin:/usr/bin:/bin \
  PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PWD/src:$PWD" \
  /Users/jay/.t3/worktrees/pricerecon/t3-7260bb2e/.venv/bin/python -m pytest -q \
  tests/test_monitoring_workflow.py tests/test_discovery_workflow.py \
  tests/test_qualification_workflow.py tests/test_cost_workflow.py \
  tests/test_history_workflow.py
```

Actual-browser fixture and retained driver (separate terminals, local port 8886):

```sh
PYTHONPATH="$PWD/src:$PWD" \
  /Users/jay/.t3/worktrees/pricerecon/t3-7260bb2e/.venv/bin/python \
  -m tests.monitoring.discovery_ui_server --history --port 8886
/Users/jay/.t3/worktrees/pricerecon/t3-7260bb2e/.venv/bin/python \
  -m tests.monitoring.discovery_browser_check --history --port 8886 \
  --artifacts /tmp/pricerecon-ticket06-browser
```

The driver verifies `ticket06-history-ui`, temporary storage, paused automatic
checks, empty blocked-edge attempts and zero sends before interacting. It uses a
unique browser session, loopback-only navigation and existing Google Chrome.
T3 navigation worked, but two consecutive snapshots returned the exact error
`Preview snapshot failed: Preview automation snapshot timed out after 15000ms.`
The documented Chrome/agent-browser fallback was then used. The installed CLI
reported `Unknown command: skills` for the skill's discovery command; its local
`--help` and retained driver supplied the supported commands. No browser was
installed or downloaded.

Browser checks passed: initial/unchanged/increased/decreased records; copied
lineage; partial/cache/failed/capped/empty sources; unobserved periods; last-good
age 28 synthetic hours; expanded context, monetary and policy evidence; reload;
375px layout without horizontal overflow; preserved legacy navigation; no browser
errors. Fixture shutdown reported `blocked_edges: []`, `notifications_sent: 0`,
`searches: 10`, `temporary_storage: true`. Fictional dates and prices establish no
real longitudinal history.

Retained artifacts: [browser receipt](artifacts/watch-history/receipt.json),
[desktop](artifacts/watch-history/desktop-history.png),
[narrow](artifacts/watch-history/narrow-history.png).

## Remaining gates

Source permission/retention, real source capture/cache/cap semantics, empirical
longitudinal data, freshness/cadence/sufficiency calibration, targets/alerts (05),
coupons (09), corrections and dependent product behavior (07), live bounded
proof, buyer acceptance, deployment and activation remain separate gates.
No usual-price estimator, savings percentage or live collection policy was
invented. Local commits/merges alone are authorized for this implementation.

## Final verification and integration refresh

- Final combined application run: **55 passed in 75.83s** — all **48 prior
  workflows**, plus **7 history workflows**, with no skips/xfails added.
- Frontend: **25 passed**, production TypeScript/Vite build passed. The existing
  large-chunk warning remains; no bundle-performance acceptance is claimed.
- Focused Ruff passed all 15 changed/new source and harness/driver files apart
  from the schema bootstrap. Including that existing bootstrap reports its two
  unchanged `BLE001` findings at lines 39/46; this slice changes only the history
  initializer call there. No suppression was added. Existing repo-wide quality
  debt and ESLint configuration gap are retained from prerequisite receipts.
- Focused mypy passed **8 source files**, using `--follow-imports=silent` as in
  the retained receipt; no unchecked casts, `Any`, ignores, xfails or disabled
  assertions were introduced.
- Final browser recheck passed against the final source; screenshots and JSON
  above are from that recheck. Fixture shutdown again reported zero outgoing
  edge attempts and zero sends. Browser/server sessions were stopped.
- Final `git merge --no-edit integration/watch-category-discovery` returned
  **Already up to date** at `375a4a474a77e374f95d5c1318445f44860c0733`;
  both closed04 and the parent's claim are confirmed ancestors. No sibling
  source had landed in integration, so no conflicts or combined sibling changes
  required repair. `git diff --check` passed. Ticket status/closure is left to
  the parent merger.
