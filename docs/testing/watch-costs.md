# Exact-offer delivered-cost implementation receipt — 2026-10-27

Ticket: [04: Show defensible UK delivered-cost scenarios](../../.scratch/watch-category-discovery/issues/04-show-uk-delivered-cost.md).
Scope: source-only, offline implementation; accepted in the FX repair merger section below.

## Workspace and authority

- Worktree `/Users/jay/.t3/worktrees/pricerecon/t3-d772dea6`, branch
  `t3/ticket04-offer-cost-evidence`, initially clean at `ef86af6`.
- Before edits, fast-forward merged `integration/watch-category-discovery` at
  `9c93d9f2188697d5130291004b159d528a071cbf`; `git merge-base --is-ancestor`
  confirmed the required integration commit is an ancestor. The integration tip
  was merged again before handoff and ancestry rechecked (still `9c93d9f`).
- Used the accepted spec, ticket04, UK-cost decision/research, identity/selection
  contracts, ticket03 receipt, Watch ADR and external boundary-review notes.
  Followed `/Users/jay/.agents/skills/tdd/SKILL.md` at the already approved
  API plus normal `execute_discovery` seam. No new seam approval was necessary.
- Reused the original parent's `.venv` interpreter with this worktree's `src`
  and repository on `PYTHONPATH`. `frontend/node_modules` is a local ignored
  symlink to integration's existing directory. No installation or download.
- Original dirty parent `/Users/jay/.t3/worktrees/pricerecon/t3-7260bb2e` was
  untouched. Its tracked-diff SHA-256 before and after was
  `38ab9795757655e9119022af759fe392bfb901bce1ce8175038fc6c0b73e8914`.
  Integration checkout was not modified. Local commits only; no integration
  merge, ticket closure, push, PR, delegation, activation or deployment.

## Implemented contract and checklist coverage

1. **Versioned exact-offer scenarios:** acquisition's existing typed merchant
   report carries `cost_scenarios`. Shared `models/costs.py` and `core/costs.py`
   contain no wristwatch identity fields or category rules. They consume the
   resolved configuration, selected binding and merchant offer. A new additive
   `discovery_cost_scenarios` table in the existing SQLite store appends cost
   revisions and links exact offer/binding/configuration revisions in the same
   transaction. No second scheduler, service or database.

   Context records definition/store/product/variation, seller, condition,
   purchase mode, quantity, country/nation/region/service, seller establishment,
   goods location, dispatch, customs origin and route, basket/consignment members
   and grouping basis, purchase scope, payment method and display/charge/funding
   currencies. Missing context or mismatched evidence withholds a total. Context
   changes produce distinct scenario IDs; recapture of the same scenario appends
   a revision. Prior rows remain unchanged and visible through read-only
   `GET /api/discovery/offers/{offer_id}/costs`; feed costs are scoped to the
   exact latest offer revision. Pre-existing rows receive no cost certification.

2. **Precise component accounting:** all amounts enter as finite, bounded exact
   decimals; floats and malformed numeric inputs fail the acquisition boundary.
   Computation uses sufficient Decimal precision for bounded inputs, quantity
   and FX; no binary floating-point money. Item/per-scenario basis and inclusion
   relationship are explicit input fields. Included VAT/charges are not added
   again. Inclusion cycles, missing parents, excessive included amounts and an
   item included inside another charge withhold a total.

   Merchant payable is separate from recipient import tax, duty, carrier and
   payment liabilities. An explicit `basket_other_items` quote supports a whole
   basket; an allocated share is conditional, with assumptions. Neither is
   promoted to a standalone public offer price. Buyer-payment FX and customs
   valuation FX are separate records. Payment conversion requires its own
   evidenced rate, direction, converter, spread treatment, rounding quantum/mode
   and time validity; customs FX cannot substitute for it. There is no legal-rate,
   tariff, consignment-threshold, carrier-fee or spot-FX lookup/calculator.

3. **Evidence and honest states:** every required component needs attributable,
   time-valid, exact-context evidence or supported inapplicability. Evidence
   retains issuer/extractor, observation/retrieval/effective/expiry times,
   capture, route, pointer/locator, permission/retention and derivation lineage.
   Supported zero requires evidence. Missing price/currency/charges remain absent;
   no default GBP or zero. Unknown/conflicting/unbounded inputs yield no delivered
   total and retain known subtotals by currency. Bounded assumptions accompany
   conditional amounts. `verified_at_observation` means complete nonconflicting
   accounting for that capture, never current freshness or comparison acceptance.

   Distinct/conflicting extractions are retained, without first-report wins or
   majority voting. Unsafe pointers are rejected and sanitized even on rejected
   components. SQL uses parameters and `BEGIN IMMEDIATE`; input/output models
   forbid extra fields. No cost write or collection/activation HTTP endpoint was
   added. React renders source text as text and never fetches evidence URLs.
   Region/method tokens carry scenario context, not street addresses, account
   numbers or payment credentials. Live retention/source-authority acceptance
   remains a separate gate; a synthetic reference cannot establish it.

4. **Application cases:** synthetic quotes exercise VAT already included,
   quantities crossing a hypothetical consignment boundary (no inferred legal
   treatment), basket changes, selected variation changes, destination/dispatch/
   payment changes, international GBP display, missing shipping/tax/duty/carrier/
   payment fees/currency, contradictory charges, absent/expired/conflicting FX,
   unknown spread, and explicit conditional FX. Restart/API history proves
   immutable first-capture readback and correct revision lineage.

5. **Public scenario and buyer display:** the no-coupon public scenario remains
   separate from conditional personal/payment/cashback scenarios. Conditional
   benefits are retained **outside payable accounting** and do not reduce the
   merchant debit or public total. No personal-benefit/account integration or
   coupon execution was built. Item-price leads remain discovery prefilters;
   budget fit can use only a single verified standalone GBP total **at its
   observation**, with that limitation stated. Conditional/unknown costs cannot
   establish budget fit. The API/feed carries expandable component/context/
   provenance/FX/assumption explanations. Usual price is unavailable, savings
   null, collection staged and bargain alerts disabled. Alert work remains 05.

## Observed red → green cycles

Each application cycle used deterministic acquisition/time, marked temporary
SQLite, the existing `MonitoringHarness` and captured notifications. Assertions
use API/feed readback and the normal execution path, without database inspection
as an assertion side channel. Fixtures are original synthetic assertions dated
by the controlled clock, not legal guidance or real offers.

- **Included VAT:** red rejected `cost_scenarios` at the typed report boundary.
  Green persists/publicly reads item `48.00` + shipping `2.10` = `50.10`, with
  quoted included VAT `8.00` counted once. Freshness and comparison stay withheld.
- **History/revisions:** red history GET returned 404. Green survives a fresh
  process, retains the first `50.10`, then quantity two and shipping `4.20` give
  `100.20` with new context and correct revision links. Repeated capture appends
  the same scenario's next revision; POST remains 405.
- **Conflicting extraction:** red returned verified `50.10` after a duplicate
  report changed shipping to `9.10`. Green retains both shipping quotes and
  returns unknown total, with the known item subtotal.
- **Import/FX:** red rejected the missing FX contract (after correcting a test
  import that preceded harness isolation). Green separates merchant `50.10`
  from additional `19.00`, total `69.10`. Another quote has `50.30 USD` plus
  `3.05 GBP`; synthetic buyer rate `0.8` gives `43.29 GBP`. Customs rate `0.7`
  is retained independently and cannot supply payment conversion.
- **Conditional eligibility:** red rejected benefits. Green retains a public
  `50.10` and separate conditional personal/payment/cashback scenarios with
  `10.00` benefits excluded from payable. A lead item `1.00` cannot establish
  budget `49.00`; verified observation cost is above budget. Conditional cost
  keeps budget unknown. A later red exposed the misleading `uk_cost_unknown`
  comparison reason for conditional cost; green uses `uk_cost_conditional`.
- **Changed context/inclusion:** red lacked the required item-inclusion refusal.
  Green withholds malformed inclusion and old proof after quantity, variation,
  nation, dispatch, basket, consignment and payment context changes.
- **Evidence boundary:** red counted a seller-paid component as buyer liability.
  Green withholds that scenario and missing zero proof, unsafe links, absent
  times, AI-derived assertions and tax/fee/currency conflicts. A signed-zero
  regression also went red before canonical serialization to evidenced `0.00`.
- **Decimal output safety:** red crashed because a valid large input's summed
  output exceeded the per-input bound. Green preserves the small `48.00`
  component beside the extreme input, using a separately typed computed output.
- **Basket scope:** red rejected the missing scope contract. Green retains an
  allocated `50.10` as conditional, a quoted whole basket `110.10` separately,
  and withholds a standalone price for either. Multi-item standalone claims fail.
- **Repeated claims:** red crashed applying a per-record cap to merged output.
  Green retains 128 conflicting components from separately valid bounded input
  records and withholds totals; it does not discard evidence or count votes.
- **Browser:** red frontend rejected the new qualified amount and timed out
  waiting for feed rows. Green displays verified, conditional and unknown costs.
  The first green attempt exposed an old driver's open/close toggle assumption;
  the corrected driver checks the row state before opening it. Final screenshots
  frame the scenario header and visible provenance at both widths.

Additional application verification covers malformed float/nonfinite/negative/
extreme-exponent inputs and a near-power FX rounding quantum as generic `parse_error` acquisition outcomes, absent
currency despite a GBP lead, parameterized hostile-looking history IDs, staged
execution without admission, and unknown/conflicting/expired payment conversion.

## Reproduction and results

From this worktree, after reusing the existing dependencies:

```sh
env -i PATH=/Users/jay/.nvm/versions/node/v24.14.1/bin:/usr/bin:/bin \
  PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PWD/src:$PWD" \
  /Users/jay/.t3/worktrees/pricerecon/t3-7260bb2e/.venv/bin/python -m pytest -q \
  tests/test_cost_workflow.py tests/test_qualification_workflow.py \
  tests/test_discovery_workflow.py tests/test_monitoring_workflow.py
```

**Passed: 46 workflows in 47.55s** on the final source: 12 cost workflows plus
all 34 retained qualification/discovery/legacy monitoring workflows. Earlier full runs passed 46 in 51.69s before the signed-zero/reason corrections
and 55.16s afterwards. A final boundary probe also
went red because ambient Decimal normalization rounded a near-power FX quantum
into an accepted power; the validator now inspects its exact coefficient. The
focused malformed-acquisition regression passes after that correction.
Every new workflow asserts zero captured notifications and no blocked external
edge attempts; collection stays staged. Existing migration/restart/Watch intent,
scheduler and notification compatibility remain covered by the retained suite.

- **Passed:** frontend `npm test -- --run`, 25 tests; `npm run build`, 633 modules.
  Existing greater-than-500-kB Vite bundle warning remains. No build overlapped
  application verification imports.
- **Passed:** Ruff on the two new cost modules plus qualification/discovery
  models, core, acquisition, API/storage and cost/browser workflows (12 files).
  Mypy `--follow-imports=silent` passed 14 source files: the two cost modules,
  qualification/discovery models/core, acquisition, API/storage, watches category,
  Watch executor, app, schema and connector base. Existing unused-override notes
  remain. `git diff --check` passed.
- **Blocked:** `npm run lint`, exit 2, ESLint 10.12.0 cannot find `eslint.config.*`.
  No workaround, suppression, install or dependency/configuration change.

Frontend commands use the existing Node directory on PATH and run from
`frontend/`. For the focused source checks, use the same interpreter and explicit
source file set above; no broad/live test collection is required.

## Actual browser proof

Used the retained controlled fixture/driver and existing Chrome/agent-browser
fallback, as explicitly authorized after the prior T3 snapshot timeouts. The
installed CLI lacks `agent-browser skills get core` (`Unknown command: skills`);
its local `--help` documents the commands used. Nothing was installed.

Build frontend first, then in one terminal:

```sh
env -i PATH=/usr/bin:/bin PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PWD/src:$PWD" \
  /Users/jay/.t3/worktrees/pricerecon/t3-7260bb2e/.venv/bin/python \
  -m tests.monitoring.discovery_ui_server --port 8879 --costs
```

In another terminal, with the existing `agent-browser` on PATH:

```sh
/Users/jay/.t3/worktrees/pricerecon/t3-7260bb2e/.venv/bin/python \
  -m tests.monitoring.discovery_browser_check --port 8879 --costs \
  --artifacts /tmp/pricerecon-ticket04-browser
```

The driver verifies the test-only identity before writing preferences, uses a
fresh isolated session restricted to loopback, checks keyboard save/reload,
opens cost/provenance details, tests 1280×900 and 375×812, checks no narrow
horizontal overflow, then navigates to legacy saved searches and closes Chrome.

Retained [browser receipt](artifacts/watch-costs/receipt.json),
[desktop page](artifacts/watch-costs/desktop.png),
[narrow page](artifacts/watch-costs/narrow.png),
[desktop cost detail](artifacts/watch-costs/desktop-costs.png), and
[narrow cost detail](artifacts/watch-costs/narrow-costs.png).
The two detail screenshots were visually inspected: readable totals, capture
qualification, known subtotal, full context/provenance and narrow wrapping.
The fixture was stopped after verification; its final receipt was
`blocked_edges=[]`, `notifications_sent=0`, `searches=3`, temporary storage true.
The simulated acquisition failure in its stderr is intentional coverage, not
real connector activity.

## Remaining gates and handoff

All ticket04 checklist behaviors are implemented and verified for this offline
slice; acceptance and ticket closure belong to the merger. No live offer passes
these synthetic fixtures. No current legal/source/retention authority, live
checkout, semantic freshness, longitudinal baseline, comparison acceptance or
buyer walkthrough is established. Observation-time cost verification cannot
supply those qualifications. Personal benefit realization and coupon execution
remain outside this slice; no cashback reduces a public payable total. Collection
and activation remain staged, with no real connector/network, credentials,
accounts, production DB, purchase, deployment or notification sending.

## Merger verification: 2026-10-27

**Ticket04 remains open.** Source review and the documented checks support much
of this offline slice, but an independently reproduced FX rounding defect breaks
the precise-money acceptance item. Tickets05/06/09 remain blocked and unclaimed.
This merger pass changes no implementation code and implements no later ticket.

### Integration and review boundary

Integration checkout `/Users/jay/.t3/worktrees/pricerecon/watch-category-integration`,
branch `integration/watch-category-discovery`, was clean at
`9c93d9f2188697d5130291004b159d528a071cbf`. Source checkout
`/Users/jay/.t3/worktrees/pricerecon/t3-d772dea6`, branch
`t3/ticket04-offer-cost-evidence`, was clean at
`af2ab0f8ed031d91a0f1e5af36e93a6fcbfdb8b9`. Their merge base was the integration
tip. Conflict-free `git merge --no-ff` produced
`ed1404b20d810371c07489044952552ab4d07452`, preserving both tips as its parents.

Reviewed the spec, implementation issue04, accepted UK-cost planning resolution
and research/contract, this implementer receipt, and the scoped acquisition,
models, evaluator, SQLite/API, feed and browser-workflow changes. The code retains
explicit context and evidence, required component/inapplicability checks,
included-charge accounting, unknown/conditional withholding, revision readback
and separate benefits. Passing fixtures and source review do not establish
current law, source permission, a real offer, freshness, comparable ranking or
alert acceptance. The defect below prevents acceptance of precise FX accounting.

### Observed blocker: numerically equal FX quanta change verified cost

`models/costs.py:157-163` accepts coefficient digits `1` followed by zeroes as an
explicit decimal power, preserving trailing zeroes. `core/costs.py:278` passes
that representation directly to `Decimal.quantize`, which rounds to its exponent,
not to the numerical increment. Consequently accepted equal quantum values have
different rounding behavior. This is observable persisted application behavior,
not only a private arithmetic assertion.

The retained [application probe](../../tests/monitoring/cost_merger_probes.py)
uses normal deterministic acquisition and API/feed readback under
`MonitoringHarness`: same selected offer/context, GBP48 item, USD2.10 shipping,
synthetic buyer FX rate 0.741, all other liabilities explicitly supported, and
GBP49 budget. Only the quantum representation changes between captures.

| Accepted quantum | Persisted/public GBP total | Budget fit |
| --- | --- | --- |
| `0.01` | `49.56` | outside |
| `0.010` | `49.556` | outside |
| `1E+1` | `48.00` | fits |
| `10` | `50.00` | outside |
| `10.0` | `49.60` | outside |

All five return `verified_at_observation`, including the three noncanonical
representations with wrong rounding. The probe confirms five retained history
revisions, unchanged historical rows, matching feed/history amounts, unresolved
comparison, disabled alerts, zero notifications and no blocked external-edge
attempts. Its three numerical-equivalence assertions fail (exit1); observations
are retained in [the JSON receipt](artifacts/watch-costs/merger-fx-quantum.json).

From the integration checkout, reproduce without installations or live access:

```sh
env -i PATH=/usr/bin:/bin PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PWD/src:$PWD" \
  /Users/jay/.t3/worktrees/pricerecon/t3-7260bb2e/.venv/bin/python \
  -m tests.monitoring.cost_merger_probes /tmp/pricerecon-ticket04-fx-quantum.json
```

Required repair: canonicalize the quantum exactly before conversion, or reject
unsupported noncanonical representations at acquisition. Preserve the existing
near-power rejection without ambient Decimal rounding. Accepted equivalent
numeric quanta must produce equivalent persisted payable amounts/budget outcomes;
none may produce a wrongly verified total. Merger deliberately left the source
unchanged and retained this red application probe for the repair owner.

### Checks and artifacts

- **Passed:** documented safe suite, **46 workflows in 53.54s**, using the cleared
  environment and existing interpreter/dependencies above. This includes all 12
  cost and all 34 retained qualification/discovery/legacy workflows. No application
  imports overlapped the subsequent frontend build.
- **Passed:** frontend `npm test -- --run`, **25 tests**; `npm run build`,
  **633 modules**. Existing greater-than-500-kB Vite warning remains.
- **Passed:** Ruff on models costs/qualification/discovery, core
  costs/qualification/discovery/acquisition, API/storage discovery and the
  cost/browser/UI-server workflows (**12 files**), plus the new merger probe.
  Mypy `--follow-imports=silent` passed those **14 source files** documented
  above; existing unused-override notes remain. `git diff --check` passed.
- **Blocked, unchanged:** frontend `npm run lint`, exit 2: ESLint 10.12.0 cannot
  find `eslint.config.*`. No installation, suppression or config workaround.
- **Failed as an acceptance probe:** equivalent FX quantum application outcomes,
  as detailed above. The 46-test success does not cover or override this failure.
- **Inspected:** retained receipt plus desktop/narrow full-page and cost-detail
  PNGs. Details show readable observation-qualified cost, known subtotal and
  synthetic provenance; narrow detail text wraps. Receipt records keyboard
  save/reload, 375px overflow check, legacy navigation and buyer acceptance
  unproven. No new browser server/session or live route was run by this merger.

The original dirty parent was preserved: status plus a deterministic content
fingerprint of tracked and nonignored untracked files was captured before merge
and checked after verification. Content SHA-256:
`af79b778d587ac7d84b7881a17bf55f0a3fbff7fea8b6cac8897bda61f348224`.
Source checkout remains clean at its original HEAD. Only local merge and review
commits are authorized/performed; no installs, network/live collection,
credentials/accounts, production database, activation, deployment, push, PR,
delegation or unrelated cleanup occurred.

## FX quantum repair: 2026-10-27

Implementation handoff for the single merger blocker; ticket04 acceptance and
closure remain with the merger. Worktree
`/Users/jay/.t3/worktrees/pricerecon/t3-d53ed76f`, branch
`t3/fix-fx-quantum-equivalence`, fast-forward merged
`integration/watch-category-discovery` at
`24a69438a316d338d7567c6179d1217b7b12d4f3` before edits. Ancestry was confirmed
with `git merge-base --is-ancestor`. No edits were made in the original dirty
parent or the integration checkout.

### Repair and retained evidence

The evaluator constructs an exact coefficient-one Decimal from the validated
quantum's numeric adjusted exponent before quantizing. It never calls
`normalize`, never changes ambient precision to normalize an input, and retains
the original supplied quantum, quote evidence and scenario context. The exact
coefficient validator, representation bounds, rounding modes, defaults and cost
policy version are unchanged. Equivalent quantum values also share a numeric
quote signature within a capture, while every supplied quote and its evidence
remain retained and checked. Different increments and expired supporting evidence
still withhold a total.

### Observed red and green

- **Original merger reproduction, red before edits:** the exact documented
  `tests.monitoring.cost_merger_probes` command exited **1**. Persisted/public
  totals were `49.56` / `49.556` for `0.01` / `0.010`, and `48.00` / `50.00` /
  `49.60` for `1E+1` / `10` / `10.0`. Ten-unit budget fits were `fits` / `outside`
  / `outside`. All five were labelled observation-verified, including the three
  wrong totals. The new red JSON
  was byte-identical to the retained [original merger artifact](artifacts/watch-costs/merger-fx-quantum.json);
  that artifact is unchanged.
- **Original reproduction, green:** the unchanged probe now exits **0**.
  `0.01` / `0.010` both produce `49.56`, budget `outside`; `1E+1` / `10` / `10.0`
  all produce `48.00`, budget `fits`. Feed, history and five appended revisions
  agree, earlier rows remain unchanged, comparison remains unresolved, alerts
  are false and notifications/blocked edges are empty. Retained
  [repair JSON](artifacts/watch-costs/repair-fx-quantum.json).
- **New application regression, red:**
  `pytest -q tests/test_cost_workflow.py -k equivalent_fx` reported
  **1 failed, 12 deselected in 1.34s**. The first noncanonical case returned
  `49.565` for `0.010` under `ROUND_HALF_UP`, against literal expected `49.57`.
  After the exponent repair it reported **1 passed, 12 deselected in 2.43s**.
- **Equivalent claims regression, red:**
  `pytest -q tests/test_cost_workflow.py -k equivalent_quantum_claims` reported
  **1 failed, 13 deselected in 0.92s**: same-value quote representations produced
  `payment_fx_conflicting:USD:GBP`. After numeric quantum comparison it reported
  **1 passed, 13 deselected in 1.05s**; genuinely different increments and expired
  evidence remained unknown.
- **Affected suite after expanded boundary/budget checks:**
  `pytest -q tests/test_cost_workflow.py` reported **14 passed in 16.97s**.

The tests use the approved normal `execute_discovery` acquisition path and real
isolated storage, followed by API/feed and append-only history readback. Expected
totals are literal worked examples rather than duplicated evaluator arithmetic.
The 48-capture regression covers four representations each of small, unit and
ten-unit increments (including scientific forms), all four supported rounding
modes and exact half ties, under caller Decimal precision **2**. Every capture
checks supplied scenario/quote/component/context preservation, known subtotals,
public totals, retained history, unresolved comparison and disabled alerts. The
final controlled preference budget is **49.565**, exercising both fitting and
outside outcomes near the small-quantum boundary. A separate three-capture
workflow checks equivalent claims, genuine conflicts and expired evidence without
discarding any supplied quote. Expanded malformed acquisition coverage rejects
near-powers above/below one and near the small/ten-unit powers, overlong
coefficients, out-of-bounds exponents, zero and negative quanta at precision 2.
The retained malformed/normal execution workflow still proves staged collection
without admission and no notifications or blocked external-edge attempts.

### Verification commands and boundary

Checks reused a temporary `.venv` symlink to
`/Users/jay/.t3/worktrees/pricerecon/t3-7260bb2e/.venv` and installed frontend
dependencies through the existing source checkout's `node_modules` symlink.
The temporary interpreter symlink was removed after checks to leave a clean
source checkout. No installs or dependency changes. Reproduce from this repair
worktree with the same interpreter directly:

```sh
env -i PATH=/usr/bin:/bin PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PWD/src:$PWD" \
  /Users/jay/.t3/worktrees/pricerecon/t3-7260bb2e/.venv/bin/python \
  -m tests.monitoring.cost_merger_probes \
  /tmp/pricerecon-ticket04-fx-quantum.json

env -i PATH=/Users/jay/.nvm/versions/node/v24.14.1/bin:/usr/bin:/bin \
  PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PWD/src:$PWD" \
  /Users/jay/.t3/worktrees/pricerecon/t3-7260bb2e/.venv/bin/python \
  -m pytest -q tests/test_cost_workflow.py \
  tests/test_qualification_workflow.py tests/test_discovery_workflow.py \
  tests/test_monitoring_workflow.py
```

The first full-suite invocation accidentally omitted the documented Node PATH:
**47 passed, 1 failed in 54.86s**, solely `FileNotFoundError: 'node'` before the
legacy form-payload workflow could run. No application assertion failed in that
invocation; the corrected command above supplies the installed Node directory.
The corrected full retained suite passed: **48 passed in 58.21s** — all original
**46 workflows** plus the two new quantum regressions. No workflows were removed
or skipped.

Focused Ruff passed the documented source/workflow set plus the merger probe and
test launcher (**14 files**); focused mypy `--follow-imports=silent` passed the
same **14 source files** listed in the original receipt. Its first run identified
a local variable type-name collision between component and quote signatures;
renaming the quote variable resolved it without suppression. Existing unused
override notes remain. `git diff --check` passed. Frontend source is unchanged;
the merger's retained **25 tests/build** evidence was not repeated. The recorded
ESLint missing-config blocker remains unchanged. No new browser/live proof was
required for this numeric repair.

Collection remains staged. No speculative legal rates, later-ticket work, live
collection/network, credentials/accounts, production database, activation,
deployment, push, PR or delegation. Only local commits are authorized. Existing
legal/source/freshness/comparison/buyer and activation gates remain separate;
passing this repair does not close ticket04.

## FX repair merger acceptance: 2026-10-27

**Ticket04 is closed for source implementation and deterministic offline
verification.** The precise-money blocker is resolved. Tickets05/06/09 are
**READY and unclaimed**, reserved for parent dispatch; no later ticket was
implemented or claimed in this pass.

### Reviewed identity and history-preserving merge

Integration `/Users/jay/.t3/worktrees/pricerecon/watch-category-integration`,
branch `integration/watch-category-discovery`, was clean at
`24a69438a316d338d7567c6179d1217b7b12d4f3`. Repair
`/Users/jay/.t3/worktrees/pricerecon/t3-d53ed76f`, branch
`t3/fix-fx-quantum-equivalence`, was clean at
`aa18c74c16c08cc8a8d3fe0423da93c9df6e5b73`. The integration tip was the merge
base and an ancestor of the repair. Conflict-free `git merge --no-ff` produced
`8b6481d5dfbd40e8dde2153ea5b82198e5b4f456`, with those two exact tips as parents.
The source checkout remains clean at its supplied HEAD.

Reviewed the full ticket04/spec, accepted UK-cost resolution/contract, both prior
merger and repair receipts, the entire repair diff, input bounds/quantum
validation, evaluator and append-only cost storage/API behavior. Exact
coefficient validation still rejects near-powers without ambient normalization.
For an accepted positive power of ten, `adjusted()` supplies its numeric exponent;
the evaluator constructs a coefficient-one Decimal solely for rounding. Decimal
numeric equality in the quote signature admits equivalent increments without
rewriting supplied representations. Quote state, rate, converter, rounding and
other context remain in the signature; supporting evidence remains retained and
checked. The 512-digit local arithmetic precision is unchanged and covers the
bounded inputs, quantity, FX multiplication and aggregation. No model, storage,
API, frontend, policy-version or operational-default change was introduced.

### Independently reproduced failure and repair

Ran the **unchanged original application probe**, with the documented cleared
environment and existing interpreter, first at integration `24a6943` and again
on the merged tree. Before merge it exited **1**, reproducing all three numerical
equivalence failures and the ten-unit budget disagreement. After merge it exited
**0**: `0.01`/`0.010` both return **49.56 GBP**, budget outside;
`1E+1`/`10`/`10.0` all return **48.00 GBP**, budget fits. Persisted history and
public feed agree, all five revisions remain intact, comparison is unresolved,
alerts are disabled, and notifications/blocked edges are empty.

The independently generated red and green JSON files were byte-identical to the
retained [original failure](artifacts/watch-costs/merger-fx-quantum.json) and
[repair result](artifacts/watch-costs/repair-fx-quantum.json), respectively. No
replacement of the historical failure artifact was needed. Reproduce with the
commands in the two preceding sections; output files for this pass were
`/tmp/pricerecon-ticket04-merger-red-20261027.json` and
`/tmp/pricerecon-ticket04-merger-green-20261027.json`.

### Merged-tree checks and acceptance

- **Passed:** documented safe suite, **48 workflows in 61.24s**, using the exact
  cleared-environment command in the repair receipt, including the installed
  Node PATH. All 46 baseline workflows and both new regressions ran; none were
  removed or skipped. The 48-capture regression checks three increment sizes,
  four representations each, all four rounding modes and half ties at caller
  Decimal precision 2, public budget outcomes, supplied quote/components/context
  preservation and unchanged prior history. Equivalent claims remain retained;
  genuinely different increments and expired evidence withhold totals.
  Malformed/near-power/bounds, extreme money precision, changed buyer context,
  restart, inclusion, conditional benefits and legacy monitoring are covered by
  the retained application workflows with controlled external edges and storage.
- **Passed:** focused Ruff on the documented 12 source/workflow files plus the
  merger probe and cost test launcher (**14 files**). Focused mypy
  `--follow-imports=silent` passed the documented **14 source files**; existing
  unused-override notes remain. `git diff --check` passed.
- **Accepted retained proof:** prior merger's **25 frontend tests/build** and
  desktop/narrow browser evidence. The frontend and browser driver/server are
  byte-unchanged by this repair. Re-read the browser receipt: verified,
  conditional and unknown display, included VAT once, separate cashback, known
  subtotal, provenance, keyboard/reload and 375px overflow checks passed; buyer
  acceptance is explicitly unproven. No new frontend/browser run was needed.
- **Blocked, unchanged:** recorded frontend lint failure, ESLint 10.12.0 missing
  `eslint.config.*`; no installation or configuration workaround was attempted.

All five ticket04 checklist items are accepted for this offline slice, combining
these repaired arithmetic checks with the original implementation/merger
persistence, API, evidence/context and UI proof. This closes the reported FX
objection without claiming later tracking, history-product or coupon acceptance.
Verified means **at the synthetic observation only**. No current legal rules,
source/retention rights, real checkout, live offer, semantic freshness, comparison
qualification, usual-price baseline, alert or buyer walkthrough acceptance is
established. Collection remains staged and activation gates remain open.

The original dirty parent `/Users/jay/.t3/worktrees/pricerecon/t3-7260bb2e` was
read only. Before/after HEAD was `ef86af6d41fbb3cac8982f43997068e906477025`;
status SHA-256 was
`6dd6d0c6377dc3a26220278755da49a2b085c08094d7eb180cdcc017d718ac06` and
tracked/nonignored-untracked content fingerprint was
`d6f0cf20a897aeef3206031028e17679af2ff57399a378c8922b10583e1c3169`, both
unchanged. The content fingerprint sorts git-listed paths and hashes path,
file mode and bytes (or symlink target), including missing-path markers.
Only local merge/receipt commits occurred. No installs, network/live work,
credentials/accounts, production DB, activation, deployment, push, PR,
delegation or unrelated cleanup.
