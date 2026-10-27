# Exact-offer delivered-cost implementation receipt — 2026-10-27

Ticket: [04: Show defensible UK delivered-cost scenarios](../../.scratch/watch-category-discovery/issues/04-show-uk-delivered-cost.md).
Scope: source-only, offline implementation; merger acceptance remains pending.

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
