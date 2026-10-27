# Watch source evidence — deterministic offline implementation, 2026-10-27

Ticket 11 implementation is ready for parent acceptance. **11 remains in progress;
the parent merger owns closure. Collection remains staged.** This receipt covers
original synthetic payloads and isolated application behavior, not current merchant
offers, source rights, live freshness, buyer acceptance or production operation.

## Checkout and authority

- Worktree: `/Users/jay/.t3/worktrees/pricerecon/t3-3f2871eb`.
- Branch: `t3/carry-source-evidence`.
- Initial clean HEAD: `ef86af6d41fbb3cac8982f43997068e906477025`.
- Verified integration was clean at
  `52104eb3de8e4b7c6ff615763d8ecc3572e4e34d`, then fast-forward merged it before
  any source edits. No checkout was created in the shell.
- Implementation commit: `82d1175256bd0b540d06907048733a936b075860`.
- Refresh merge: `17a65e452c2623dba146488654bdd43bbc5af784`, second parent
  `fbe27584f3e7ea73ec375b0a405bc4213af9a60e`. Three conflicts in
  `Discovery.tsx`, `discovery.css` and `discovery_ui_server.py` retain both the
  source-evidence slice and ticket08 price-assessment/coupon behavior.
- Final refresh: `b24ec52baebc61e73e93d3c9dfdefe645449f180`, second parent
  `446ee9e649ad91406d66cb5b0c43990f3be590db`. This includes08's subsequently
  accepted type-factory repair without conflicts. No comparison/coupon source
  repair was authored by11.
- The current task explicitly authorises local commits/merges, superseding the
  ticket's historical no-commit wording. Neither the dirty original checkout nor
  integration source was edited. No subagents, push, PR, install/download,
  credential/account operation, live acquisition, production DB, activation,
  deployment or purchase occurred.

Final integration identity, checked source hashes, commands and results are bound
in [verification.json](artifacts/watch-source-evidence/verification.json). The
receipt commit is discoverable in local branch history; it does not contain its
own impossible self-referential hash.

## Implemented behavior and boundaries

The existing shared acquisition owner now carries typed source receipts beside
its outcomes. Existing offer revisions retain source observations beside their
qualification. Existing capture/offer JSON storage and history projections carry
these fields across restart; no new tables, scheduler, capability registry or
ledger was introduced. Schema 2.3 was unnecessary and remains unused by 11;
ticket08's schema 2.2 is preserved.

The normal discovery feed includes a read-only projection of the accepted source
decision: six mandatory families and 16 explicit routes. Accepted research status,
last attempted acquisition and missing current evidence are distinct. Militado,
Merkur, specialist secondhand, UK retail, international, search, aggregator and
community gaps remain visible even before any acquisition. All lanes remain
staged; the roster configures no transport or activation.

The existing AliExpress browser inspector, eBay Browse connector and Shopify
storefront connector produce discovery reports from their real external shapes:

- AliExpress retains displayed selected options, SKU absence, price scope,
  destination literal, quantity, VAT/shipping claims, content truncation and
  product/page limits. A capped/unqualified browser result can be a partial review
  lead without becoming a selected offer. Affiliate, DS and search lanes never
  silently replace browser-first discovery. Legacy Watch search retains its
  existing stricter return contract.
- Browse retains seller, literal condition, normalized condition claim, buying
  modes, auction bid versus listing price, destination estimate, stock claims,
  shipping quote, missing fields, one-page/50-item cap and presence of a next
  page. Missing money/currency/availability never become GBP/zero/in-stock in
  discovery. No details or next pages are implicitly fetched. Empty tax arrays
  remain unknown. Next URLs, postal codes and token material are not retained.
- Shopify retains each variant ID, explicit movement/strap options and its own
  price without assigning the first variant's value to its siblings. Absent
  currency stays absent. `sanmartin.watch` is labelled independent retailer, not
  manufacturer. Its single 250-product page is partial, not a complete query
  result or selected UK offer. Militado is blocked before transport on its
  unresolved recognized-signer prerequisite, even with a synthetic-use label.

Field evidence retains issuer versus extractor, route, locator, controlled
retrieval/observation time, source capture, acquisition capture, derivation,
permission reference and retention class. The frontend also renders rejected
claims and the literal unqualified source summary. That summary is never used
as qualification input. A selected ID, generic stock claim, successful response
or GBP display cannot manufacture manufacturer identity, selection binding,
destination, complete cost or historical rights.

Discovery adapters require an explicit capture/use reference before auth or
transport. This reference is an input prerequisite, not a licence certificate;
history rights remain unqualified. Browser/native-origin and AI paths remain
blocked by existing shared admission, rather than being admitted at zero cost.
Shopify's HTTP requests now use the existing shared event-hook client; product
pages/details join its existing classification. Actual token sends, Browse
requests and retries traverse the same durable admission. HTTP access/auth/rate
failures retain explicit outcomes and route prerequisites without refreshing the
last-good candidate. The ticket10 all-source denial/timestamp controls are kept.

## Accepted seam and safety

Tests use the buyer-approved normal `execute_discovery`/Watch execution plus API,
temporary SQLite, controlled time/connector edges and captured actual notification
transport. Original HTML and JSON are supplied at external navigation/HTTP edges;
the real inspector/parsers, adapter reports, acquisition, resolvers, persistence,
history and API remain in the path. Tests do not replace adapters with ideal
qualified merchant reports.

All application imports occur inside `MonitoringHarness` in fresh children.
The harness rejects network, native curl, browser startup, subprocess escape and
unmarked/non-temporary DB connections. No unexpected edge or notification was
observed in source fixtures. Browser UI checks use only inbound loopback traffic
against that guarded application, with paused automatic scheduling. The separate
CLI driver runs installed Chrome; it does not launch acquisition browsers.

## Red/green receipts

Run from this worktree with the original interpreter and a cleared environment:

```sh
env -i PATH=/Users/jay/.nvm/versions/node/v24.14.1/bin:/usr/bin:/bin \
  PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PWD/src:$PWD" \
  /Users/jay/.t3/worktrees/pricerecon/t3-7260bb2e/.venv/bin/python \
  -m pytest -q tests/test_source_evidence_workflow.py
```

The same prefix was used for each focused red/green invocation below. Red logs
record expected exit1; the corresponding green passes exercise the completed
normal persisted behavior.

| Slice | Exact test suffix/selection | Retained red → green |
| --- | --- | --- |
| Browser review leads | Initial source module, one test | `red-browser.log` → `green-browser.log` |
| Browse fields/missingness | `-k browse` | `red-browse.log` → `green-browse.log` |
| Retailer variants | `-k independent` | `red-retailer.log` → `green-retailer.log` |
| Use/browser gates and failure | `-k 'authority or failure'` | `red-gates.log` → `green-gates.log` |
| Mandatory roster and restart | `-k 'mandatory or fresh_process'` | `red-roster.log` → `green-roster.log` |
| Destination, stock and shipping | `-k source_destination` | `red-context.log` → `green-context.log` |
| Product truncation | `-k truncated` | `red-truncated.log` → `green-source-workflows.log` |
| Signing gate | `-k militado` | `red-militado.log` → `green-source-workflows.log` |
| Discovery truncation | `-k truncated_discovery` | `red-discovery-truncated.log` → `merged-source-workflows.log` |

The final source module has **15** workflows: the above behavior, real admitted
and capped auth retries, malformed item isolation, fresh-process readback and a
merged ticket08 interaction. The latter supplies comparison policy while passing
all three real adapter fixtures through normal execution; no supported best/low,
usual price or saving can be obtained from those unqualified leads. Existing
working behavior controls passed on their first run and are not described as
new red failures.

The first broad run recorded **172 passed, 1 failed** in
`guarded-workflows-initial.log`. The new capture-use gate correctly stopped the
old actual-Browse retry fixture, whose config lacked a use reference. Its original
synthetic declaration was added; every existing cap, send, retry and accounting
assertion remains intact. The focused source-plus-original-control run then passed
**15 tests** at that intermediate stage. No prior assertion was removed, relaxed,
skipped or suppressed.

The final combined command adds the new module and integrated08 module to all
eleven required workflow modules:

```sh
env -i PATH=/Users/jay/.nvm/versions/node/v24.14.1/bin:/usr/bin:/bin \
  PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PWD/src:$PWD" \
  /Users/jay/.t3/worktrees/pricerecon/t3-7260bb2e/.venv/bin/python -m pytest -q \
  tests/test_collection_workflow.py tests/test_monitoring_workflow.py \
  tests/test_discovery_workflow.py tests/test_qualification_workflow.py \
  tests/test_cost_workflow.py tests/test_history_workflow.py \
  tests/test_coupon_workflow.py tests/test_tracking_workflow.py \
  tests/test_correction_workflow.py tests/test_correction_target_ownership.py \
  tests/test_shared_grant_workflow.py tests/test_assessment_workflow.py \
  tests/test_source_evidence_workflow.py
```

`test_correction_workflow` includes correction-scope workflows. No full repository
suite, configured-DB `tests/test_api.py` or standalone correction-scope module was
run. Final counts and final integration refresh checks are recorded below and in
the machine-readable receipt.

## Static, frontend and browser proof

Focused mypy passed on the 16 changed application files. Final uncached mypy
also includes08's refreshed tracking model and passes all **17 files**. Ruff comparison retains
inherited diagnostics separately; the source slice adds no suppression. Final
results and exact file lists are in the verification receipt. The 37 limiter /
external-browser contracts pass with ten inherited deprecation warnings.

The existing integration `frontend/node_modules` was reused through an ignored
symlink. Builds finished before fixture/app imports; no build ran concurrently
with a fixture server. Frontend tests retain all 25 checks. ESLint remains blocked
by the existing missing `eslint.config.*`; no pass or suppression is claimed.
The build's existing chunk-size warning remains explicit.

The agent-browser skill was read. Its documented `skills get core` command is not
available in the installed CLI, so the installed `--help` and retained driver
contract were used without installing/downloading anything. The source UI red
run (`red-ui.log`) failed because no source-coverage control existed. Its initial
passing screenshots contained a narrow scroll-framing limitation; final merged
artifacts supersede those initial images.

Reproduce final source UI proof with two separate terminals, starting the server
only after the build exits:

```sh
env -i PATH=/Users/jay/.nvm/versions/node/v24.14.1/bin:/usr/bin:/bin \
  /Users/jay/.nvm/versions/node/v24.14.1/bin/npm --prefix frontend run build

env -i PATH=/Users/jay/.nvm/versions/node/v24.14.1/bin:/usr/bin:/bin \
  PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PWD/src:$PWD" \
  /Users/jay/.t3/worktrees/pricerecon/t3-7260bb2e/.venv/bin/python \
  -m tests.monitoring.discovery_ui_server --port 8891 --source-evidence

env -i PATH=/Users/jay/Library/pnpm:/Users/jay/.nvm/versions/node/v24.14.1/bin:/usr/bin:/bin \
  PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PWD/src:$PWD" \
  /Users/jay/.t3/worktrees/pricerecon/t3-7260bb2e/.venv/bin/python \
  -m tests.monitoring.source_evidence_browser_check --port 8891 \
  --artifacts "$PWD/docs/testing/artifacts/watch-source-evidence/ui-merged"
```

Final source proof uses real Chrome at **1280×900 and 375×812**. It verifies the
fixture marker before interaction, keyboard Enter expansion, all 16 routes and
named blocked prerequisites, selected Space Gray versus mint title, unbound price,
missing selected SKU/stock, reload persistence, no horizontal overflow and no page
errors. Screenshots were actually opened and inspected:

- [Desktop coverage](artifacts/watch-source-evidence/ui-merged/desktop-source-coverage.png)
  and [desktop source details](artifacts/watch-source-evidence/ui-merged/desktop-source-evidence.png).
- [Narrow coverage](artifacts/watch-source-evidence/ui-merged/narrow-source-coverage.png)
  and [narrow source details](artifacts/watch-source-evidence/ui-merged/narrow-source-evidence.png).
- [API/browser receipt](artifacts/watch-source-evidence/ui-merged/receipt.json)
  and `ui-server.log` retain zero escaped edges/notifications and fixture cleanup.

The merged assessment mode also uses the unchanged real browser driver against
port8892 (`discovery_ui_server --assessments`, then
`discovery_browser_check --assessments --artifacts .../assessment-ui`). This verifies
both conflicted fixture modes and the page retaining08's scoped coupon payable,
unavailable usual price, reload and correction withdrawal. Its receipt/images and
server cleanup log are retained beside source proof. Both owned browser sessions
and fixture servers are closed.

## Final verification and refresh

| Check | Observed result |
| --- | --- |
| All guarded workflows, source state `ae1cbea15f7ed0e835f42d755ef05d7ad73a7549` | **186 passed in 198.60s**, no failures/skips/xfails; `guarded-workflows-merged.log` |
| Final refresh, `b24ec52baebc61e73e93d3c9dfdefe645449f180` | **38 passed in 37.07s**: all 15 source workflows, all 11 assessment workflows and 12 exact-tracking workflows; `final-refresh-workflows.log` |
| Final uncached mypy | **17 source files passed**; `mypy-final.log` |
| Focused clean Ruff | **14 files passed**; `ruff-clean.log` |
| All 23 changed Python files versus final integration | **Zero added findings**, 48 baseline / 46 current inherited diagnostics; `ruff-final-comparison.json` |
| Limiter/external-browser | **37 passed**, ten inherited warnings; `contracts.log` |
| Refreshed frontend | **25 passed**, build passed; `frontend-tests-merged.log`, `build-merged.log` |
| Actual source UI | **Passed**, desktop/narrow/keyboard/reload, no overflow/errors; `ui-merged/receipt.json` |
| Actual assessment UI after page/server conflict resolution | **Passed**, desktop/narrow/reload/correction withdrawal; `assessment-ui/receipt.json` |
| ESLint | **Blocked**, inherited missing `eslint.config.*`; `eslint.log` |
| Diff and ancestry | Source/document diff whitespace passes; final integration and original base are ancestors. Whole staged diff exits2 only for whitespace emitted by retained raw pytest/Vite/frontend logs; `diff-raw-logs.log` preserves the diagnostic. Raw logs were not rewritten. |

The earlier inherited tracking-model mypy failure is retained in
`inherited-tracking-mypy.log` for chronology. It is resolved by the final
integration refresh; it is **not a remaining failure**. The final integration delta
only changes that model's typed default factory and its acceptance receipts. The
full guarded run was therefore followed by the focused 38-workflow and uncached
type checks rather than another full suite. Frontend, source-adapter behavior,
shared admission and browser artifacts are byte-identical across this last
type-only refresh; their passing checks are reused on that stated basis.

The final focused test command is the earlier cleared-environment prefix plus:

```sh
python -m pytest -q tests/test_source_evidence_workflow.py \
  tests/test_assessment_workflow.py tests/test_tracking_workflow.py
```

`verify_static.py` retains the exact final 23-file Ruff comparison and original
Git blob baseline. `verification.json` retains full commands, source hashes,
frontend tree identity, screenshot hashes and ancestry. No production/activated
or complete-source claim follows from these checks.

## Remaining acceptance gates

Parent review/acceptance and ticket12 remain separate. No real Militado signer or
manufacturer identity, reconciled Merkur reference, selected-SKU UK stock/total,
source-specific retention/derivation grant, permitted longitudinal history,
repeated freshness or buyer walkthrough was fabricated. Reviewed access receipts
remain dated research, not fresh live acquisition authority. Budget figures are
synthetic test allowances. Finite measured breadth/cadence/cost, physical disk / WAL /
journal / logs / backup quotas, retention/deletion/restore proof and named
maintenance ownership remain operating prerequisites. Nothing activates collection.

## Sole merger disposition — 2026-10-27

**11 remains open for one concrete adapter-boundary finding. 12 remains blocked
and unclaimed.** The source implementation is merged for review, not accepted as
complete. The parent owns the contained repair; this review changed no application
code or existing test assertions and performed no 12 work.

Integration was clean on `integration/watch-category-discovery` at
`446ee9e649ad91406d66cb5b0c43990f3be590db`; source was clean on
`t3/carry-source-evidence` at `7fb56beb54f9b60a0555eee53df0c2b31e718e0c`.
Both `52104eb` and `446ee9e` were source ancestors. Integration had not moved,
so no source refresh was performed. Local `git merge --no-ff
7fb56beb54f9b60a0555eee53df0c2b31e718e0c -m "Merge ticket 11 source evidence for
offline acceptance review"` produced **`8eb1d777ed7614a69712ea8f074af67fa0dd7550`**,
with first parent `446ee9e649ad91406d66cb5b0c43990f3be590db` and second parent
`7fb56beb54f9b60a0555eee53df0c2b31e718e0c`. There were no merger conflicts;
source and merge trees matched exactly. Both source refresh merges and all prior
histories remain reachable. No squash, rebase, reset, cherry-pick, checkout creation,
push, PR, install/download, credential/account operation, live acquisition,
production DB access, activation, deployment, purchase or unrelated cleanup occurred.

### Concrete blocker and minimal reproducer

**P2 — Shopify discovery runs its legacy monetary parser before its typed evidence
parser, so one malformed variant discards valid siblings and capture bounds.**
`ShopifyConnector.search_with_evidence` calls `search`, which calls
`_products_to_listings` before `shopify_evidence`. Add one variant with
`price: "not-money"` to the existing original synthetic SN0144 product. The
`Decimal(...)` conversion at `connectors/shopify.py:166` raises
`decimal.InvalidOperation`. The new per-variant validation/isolation at
`shopify_evidence.py:68–73` is never reached.

The unmodified two-variant control retains IDs 201/202, GBP 110.00 versus 180.00,
explicit movement/strap identity and absent second currency, without a qualified
UK total. Adding only malformed ID 203 instead returns **zero candidates**, a
persisted `failed/connector_error` outcome, and receipt `pages_captured=0` with
unknown page/item limits despite two completed, durably accounted HTTP sends.
Thus a bad variant contaminates the whole source result and actual captured
scope is lost. This fails the engineering standard's smallest-unit isolation and
11's adapter/failure-state contract. No false comparable price, escaped network
edge or notification was observed in either case. This is a reproduced offline
boundary failure, not a claim about current merchant content.

The [independent probe](artifacts/watch-source-evidence/merger/retailer_isolation_probe.py)
uses fresh-process `MonitoringHarness`, marked temporary SQLite, the original
synthetic HTTP fixture, real Shopify connector/parser, shared HTTP admission,
normal `execute_discovery`, public feed/collection APIs and captured notification
transport. It replaces only the external HTTP transport; it makes no private DB
assertions or ideal adapter replacement. Public feed/usage snapshots and exact
tracebacks are retained in `retailer-control.json/.log` and
`retailer-malformed.json/.log`. The failing assertion is retained unchanged.

Run from `/Users/jay/.t3/worktrees/pricerecon/watch-category-integration`:

```sh
env -i PATH=/Users/jay/.nvm/versions/node/v24.14.1/bin:/usr/bin:/bin \
  PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PWD/src:$PWD" \
  /Users/jay/.t3/worktrees/pricerecon/t3-7260bb2e/.venv/bin/python \
  docs/testing/artifacts/watch-source-evidence/merger/retailer_isolation_probe.py control
# exit0; passing original control, two sends, two retained leads, no notification

env -i PATH=/Users/jay/.nvm/versions/node/v24.14.1/bin:/usr/bin:/bin \
  PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PWD/src:$PWD" \
  /Users/jay/.t3/worktrees/pricerecon/t3-7260bb2e/.venv/bin/python \
  docs/testing/artifacts/watch-source-evidence/merger/retailer_isolation_probe.py malformed
# exit1; exact sibling-preservation assertion fails after API snapshots are retained
```

### Checklist review and preserved integration behavior

| 11 checklist | Merger finding |
| --- | --- |
| Adapter fields, lineage, missingness and outcomes across storage/API/UI | Demonstrated for supplied shapes, but **incomplete** for malformed Shopify siblings/captured bounds above; reopened. |
| Browser-first AliExpress, real Browse shapes and contrasting retailer | **Passed within synthetic scope.** Selected Space Gray versus mint title, unbound/displayed price, missing SKU/stock and truncation/caps remain explicit. No affiliate/DS substitution or selected-offer qualification observed. Browse seller/literal condition/normalized claims, bid versus fixed price, missing money/currency/stock, destination/shipping/tax unknowns, next-page presence and retry/auth caps survive the supplied workflows. No retained token/postcode/nextURL material was observed. Valid retailer variants retain independent prices/options, independent-retailer attribution and absent currency; single 250-product page scope remains partial. |
| Six mandatory families and 16 routes | **Passed.** Read-only accepted-decision projection retains blocked/unqualified/unsupported routes, Militado/Merkur gaps and prerequisites without configuring activation or a second capability service. |
| Rights prerequisites, shared admission and staged lanes | **Passed within offline controls.** Missing use declaration and Militado signer stop before transport; a use reference remains an input prerequisite, not proof of licence. HTTP sends/auth/retries use durable admission; unsupported browser/native/AI lanes remain gated. Failure does not refresh last-good or create qualified current/low claims. |
| Actual adapter/failure workflows at application boundary | **Incomplete** for the independent malformed retailer probe; reopened. Existing 186 pass, including 15 source workflows, but do not cover this counterexample. |

Actual modified adapters, acquisition, claim construction, JSON persistence,
history projections and frontend parsers/rendering were read. Issuer and extractor,
source and acquisition capture, retrieval time, derivation, permission reference
and retention class remain separate. Literal unqualified summaries are attached to
offers; qualification consumes field evidence, not those summaries. Source history
rights remain unqualified. The new source roster grants no acquisition authority.

The prior 08 conflict resolution retains `PriceAssessments` and coupon behavior in
`Discovery.tsx`, styles and both fixture modes. The merged full suite passes all 08
assessment/coupon cases, 07 exact binding-revision ownership/correction cases and 10
durable-grant/denied-Watch timestamp cases. Their application owners were not
repaired or rewritten here. The actual Browse retry fixture changes only its
synthetic-use declaration; its original cap/send/retry/accounting assertions remain
intact. Legacy saved Watch intent and enabled/disabled execution regressions pass.
These results establish the tested behaviors, not universal runtime qualification.

### Required merger checks and retained proof

The frontend build completed **before any application/fixture import**. Only the
existing dependencies and original parent interpreter were used. The complete
13-module cleared-environment command in the source receipt above was repeated
from integration with integration `src` and root in `PYTHONPATH`:
**186 passed in 174.96s**, no skips/xfails/failures (`merger/workflows.log`). No full
repository pytest, unsafe `tests/test_api.py` or live suite was run.

| Check | Observed result / merger artifact |
| --- | --- |
| Frontend build | **Passed**, existing chunk-size warning retained; `build.log` |
| `python -m pytest -q tests/test_rate_limiter.py tests/test_external_browser.py` with the same cleared prefix | **37 passed**, ten inherited warnings; `contracts.log` |
| `npm --prefix frontend run test -- --run` in cleared environment | **25 passed**; `frontend-tests.log` |
| `python -m mypy --no-incremental` all 16 changed app files plus `models/tracking.py` | **17 files passed**; exact command/environment in `checks.json`, output `mypy.log` |
| Focused Ruff versus exact 446ee9e Git blobs | **Zero added findings**, 48 baseline / 46 current on 23 changed Python files; `ruff-final-comparison.json`, `ruff-final*.json`, `ruff.log` |
| ESLint | **Blocked**, existing missing `eslint.config.*`, exit2; `eslint.log` |
| Independent retailer control / challenge | **Control passed; challenge failed**, exact outputs/snapshots retained; no assertion weakened/dropped/skipped |
| Source/document whitespace | **Passed**; raw tool-log whitespace remains separately recorded/inherited |
| Source and original parent integrity | 27 source hashes and 69 artifact hashes match; all 77 original-parent hashes/lengths match, unchanged source clean at 7fb56be; `integrity.json` |

Exact commands and cleared environments for build, full suite, contracts, types,
frontend, Ruff and probes are retained in `merger/review.json` and `checks.json`.
The Ruff command is the original cleared prefix plus
`python docs/testing/artifacts/watch-source-evidence/merger/ruff_compare.py`.
It reads the exact 446ee9e blobs without making another checkout. No suppressions
were added, and no global lint/type green is asserted. Two review-runner invocation
errors (an incorrectly sliced interpreter argument, then using system Python for
Ruff) are preserved in `runner-invocation-failure.log` and `checks-run.log`.
They were corrected in the review helper; successful type/frontend results were
not repeated, and Ruff alone was rerun with the original interpreter.

All seven retained final source/assessment desktop/narrow/withdrawal screenshots
were actually opened and inspected, together with both browser receipts and server
shutdown logs. All source/receipt hashes match. The frontend tree remains exactly
`08aa2e1fe99d9702e09ae087f8fcc1925452b547`; the source-mode image visibly retains
Space Gray/unbound price/missing SKU and stock, while assessment images retain
GBP 45.10 scoped coupon payable and later invalidated current/dated-low claims.
The recorded actual keyboard/reload/no-overflow/no-error checks remain dated source
proof; no new browser session was needed because the merger made no UI change.
Both retained server logs report zero escaped edges/notifications and stopped
fixtures; this merger opened no browser or server.

Machine-readable [review receipt and artifact hashes](artifacts/watch-source-evidence/merger/review.json)
bind the new results. In particular, the exact original-parent manifest is
SHA256 `93ada3e762355f117518d20a6dd2d0ad6f80e01cb2d49bea8ddff073e390c6b9`.
The final review commit is discoverable from local history rather than embedded
self-referentially in its own file.

Collection remains staged. Source-specific rights/retention/derivation,
Militado signer/manufacturer identity, Merkur exact evidence, live selected-offer,
history/coupon/delivery proof, empirical freshness/calibration, finite operating
and physical disk/WAL/log/backup/retention controls, named maintenance owner, buyer
feedback and activation remain separate and unproven. Passing synthetic checks
neither authorises new collection nor converts accepted research into current
rights. The frontier is the parent's contained 11 repair and independent acceptance;
12 dispatch remains with the parent after that gate passes.

## Parent retailer isolation repair and offline acceptance — 2026-10-27

**11 is closed for offline scope; 12 is claimed for isolated implementation.**
Parent repaired the contained merger finding directly on integration based on
`48a15e0`. Shopify's shared retrieval now returns the payload to the caller:
discovery passes it directly to the existing typed evidence parser, and legacy
Watch search retains its existing result parser/browser annotation. No duplicate
HTTP path, fallback, arithmetic or accounting service was added. The unused
intermediate payload instance state was removed.

The retained original probe was added to the guarded suite. It accepts an optional
output directory so new runs preserve the original merger's failed JSON/logs.
Its original sibling/price/missing-currency/unqualified-total assertions remain;
page count, limits and actual page accounting assertions were added. Before the
repair: **one failed, one control passed**. After the repair: both pass. Valid
variants201/202 keep GBP110.00/180.00 and the second currency stays unknown;
invalid203 is omitted with `invalid_variant:0:2`. Both runs report partial scope,
one captured products page, page limit1, item limit250 and two inspected variants.
The two real HTTP sends (search plus products) debit two requests and two page
resources. Neither result qualifies a UK total or sends notifications.

A third API control runs two normal legacy Shopify Watch checks without a
discovery-use declaration: each completes with two listings, four total HTTP sends,
correct timestamp and no duplicate notification. Existing disclosure/use/browser/
cap/failure/correction/assessment behavior remains covered by the full suite.

- **189 guarded workflows passed in 170.46s**, all 186 retained plus three controls,
  no skips or xfails. Same thirteen-module cleared-environment command as above.
- **37 limiter/external-browser contracts passed**; ten inherited warnings.
- Uncached mypy passes the changed connector with silent import following. The
  merger's 17-file proof is reused for the unchanged other application modules.
- Ruff comparison over all four changed Python files: **five inherited findings,
  five current, zero added**; no suppression or assertion weakening. Changed helper
  lines and new control pass Black; local source/document diff whitespace passes.
- Frontend tree remains `08aa2e1fe99d9702e09ae087f8fcc1925452b547`; the merger's
  25 tests/build and inspected desktop/narrow source/assessment/withdrawal browser
  evidence are reused. Existing ESLint missing-config, chunk warning and raw-log
  whitespace limitations remain recorded.
- Original parent's **77 files** still match their initial byte lengths and SHA-256.
  The source worktree was untouched; no new browser or fixture server was started.

[Red/green logs, fresh exact probe/control JSON and updated hashes](artifacts/watch-source-evidence/retailer-repair/verification.json)
bind the repair. Focused reproducer uses the preceding cleared environment:

```sh
python -m pytest -q tests/test_source_evidence_workflow.py \
  -k 'valid_siblings or legacy_retailer'
```

No installs, network/live acquisition, credentials/accounts, production DB,
activation, push or PR. Collection remains staged. Source-specific rights and
retention, Militado/Merkur evidence, live selected-offer/history/coupon/delivery,
empirical calibration, measured operating/physical limits, named maintenance owner
and actual buyer/activation acceptance remain separate and unproven.
