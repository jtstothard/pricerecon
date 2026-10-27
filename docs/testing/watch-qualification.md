# Ticket03: exact configuration and merchant-offer qualification

2026-10-27. Implementation checkout:
`/Users/jay/.t3/worktrees/pricerecon/t3-4e6f8e87`, branch
`t3/explain-offer-qualification`. Started clean at `ef86af6`; merged
`integration/watch-category-discovery` at
`21b3b5801fccdc6b9ab85b998a64d40deecda848` **before editing**, and confirmed
that commit is an ancestor. Final local HEAD is recorded in the handoff.
The merger owns acceptance, ticket closure and integration; ticket03 remains open.

This is offline application proof. All positive attribute/selection evidence in
these tests is **invented synthetic test data**, including values attached to the
real product names. It is not a manufacturer or merchant receipt. No evidence
was acquired for real Militado or Merkur offers; both deliberately abstain.

## Contracts and persistence

The existing normal `execute_discovery` entry point consumes an additive optional
`search_with_evidence(query, filters) -> EvidenceSearchReport` adapter boundary.
Ordinary Watch execution still calls `search`; connectors without the optional
method still produce unresolved discovery leads. Existing live adapters have not
been qualified or switched to this method. The result must be the concrete typed
report and is revalidated, including nested models. Arbitrary normalized dicts,
legacy confidence/exactness/stock/landed-cost flags and title equality cannot enter
as identity evidence. Invalid typed output produces a generic `parse_error`
outcome, without exposing the source payload through discovery diagnostics.

Each report retains a merchant/storefront namespace, opaque product/listing and
stable selected-variation identifiers. Configuration subject keys scope
manufacturer claims to the exact definition. Each field claim has its own ID,
subject, allowlisted field, literal value and assertion/applicability state,
issuer and issuer role, extractor and method (plus nullable version/model/run and
uncertainty), observed/retrieved/effective times, original capture ID, route,
URL and precise locator, structured configuration/selection/purchase context,
permission/retention reference and derivation/input-claim lineage. Unknown times
and dimensions are not fabricated. Repeated claims are not counted as votes;
AI, copied reseller definitions and unsupported human corrections are retained
with rejection reasons rather than promoted to direct authoritative assertions.
Human correction/adjudication writes belong to ticket07.

The watch category owns mandatory complete-watch, maker, exact reference,
generation/revision, movement, **case width** in mm, dial, strap and date/no-date
rules. Only case/whitespace and numeric-width equivalence are normalized; no
suffix stripping, inferred regional aliases, family inheritance or title parsing.
An explicitly evidenced inapplicable generation is permitted; an absent or
literal `unknown` dimension is not an equality wildcard. At this stage the
resolver conservatively requires an attributable manufacturer definition for
identity, and selected seller claims for the variation. Seller-only product
specifications remain visible but unresolved. Source authority labels must be
established by future reviewed adapters; a type or permission-reference string
is not an entitlement or truth certificate.

Configuration, selected variation, merchant offer and comparison remain separate
results. Selection must match all identity dimensions and bind price, currency,
quantity, destination and availability to the same merchant/product/variation
and purchase context. Missing stable SKU, first-array price, generic JSON-LD
stock, mismatched basket, size/dial/strap/movement/date/revision or near reference
cannot certify the requested offer. Multiple variations of a listing survive;
repeated reports of the same variation retain differing assertions and lineage.
Manufacturer assertions shared by variations of the same definition are checked
together so one report cannot silently hide a conflicting definition.

Seller, new/used/refurbished condition, seller description/visible-condition claim,
quantity, availability, purchase mode, selected item price/currency and destination
are returned explicitly. Used and auction offers have distinct prospective cohort
keys; quantity, destination, currency and used-condition description also scope
them. These keys do **not** certify comparability. Missing used-item detail remains
an exclusion reason. Auction bids and best-offer claims are rejected for the fixed
purchase-price comparison. Authenticity and internal health always remain unknown.
No merchant photograph or external image is fetched or used as assurance.

SQLite migration `1.4` is additive: `discovery_configurations`,
`discovery_bindings`, `discovery_offers` and `discovery_assessments`, with separate
identities/revisions and indexed capture/candidate relations. Binding records name
the configuration revision; offers name the binding revision; comparison records
name the offer revision and policy. Capture plus all records commit atomically
under `BEGIN IMMEDIATE`, with foreign keys enabled. A price change retains offer
identity and advances its capture revision. Revisions retain inputs; unchanged or
reused claims are not new independent confirmation. Older 1.3 leads are projected
as explicit unresolved offers on read, without backfilling proof or converting
legacy £1 lead prices into qualified item prices.

`GET /api/discovery/watches` returns the richer read-only feed through existing
application authentication dependencies. There are no new collection,
qualification or correction HTTP write routes, auth changes, scheduler jobs or
notifications. The singular `configuration` is the first definition for
compatibility; `configurations` and each binding's configuration ID/revision
retain every selection's subject. The headline identity state aggregates all
configurations; preference fits require consistent known dimensions across them.
Manufacturer-supported width and dial can honestly fit or miss saved preferences;
unknown dimensions stay visible. Budget fit remains unknown.

The feed displays every state, mandatory-field issues and conflicting/rejected
claim IDs. Expanded field claims show issuer versus extractor, context, dates and
lineage. Source URLs with userinfo or recognized credential query keys are withheld;
ordinary `?variant=...` query semantics are retained. Source text is React-escaped;
SQL is parameterized. Numeric representation bounds prevent extreme exponent
and integer-conversion failures; exact Decimal equality avoids rounding claims
into agreement. No new dependency, permission or auth architecture was added.

**Public UK delivered totals remain unknown until ticket04.** Successful identity,
selection and merchant representation do not imply complete cost, current semantic
freshness, comparison eligibility or alert eligibility. Ordinary positive examples
therefore have unresolved comparison with `uk_cost_unknown` and
`freshness_unvalidated`; known incompatible mappings/accessories are rejected.
Usual price remains unavailable, savings null and alerts disabled.

## Dated red/green receipts

All following failures and green checks were observed locally on 2026-10-27 at
the buyer-approved API plus normal execution seam, using the existing fresh-process
harness, controlled acquisition and UTC time, marked temporary SQLite and captured
notification transports. There were no live/network collection attempts.

| Slice | Observed red | Observed green |
| --- | --- | --- |
| Lead abstention | API `KeyError: configuration` | Legacy exact/title/generic-stock lead exposes unresolved configuration, binding and offer; seller/availability unknown |
| Five-case qualification | Synthetic complete evidence still returned unresolved identity | AD2066, SN0144 and exact-suffix Casio synthetic identities/selected offers are supported; delivered comparison withheld; Militado/Merkur unresolved |
| Multiple selected offers | API retained one offer instead of two | £1 accessory and £48 intended watch persist separately; duplicate extraction adds no third offer or price transfer |
| Persistence/revision | After fresh process and £48→£45 capture, offer revision stayed 1 | Stable offer/binding IDs, revision 2, binding revision relation and exact £45 item price survive API readback |
| Credential URL | Sensitive sentinel in discovery response | Userinfo and credential query URL absent from API, with rejected/missing evidence visible |
| Numeric boundary | An extreme exponent raised `decimal.Overflow` during normal execution | Oversized numeric claims are rejected as generic `parse_error` before resolution, without creating proof |
| Typed boundary | Arbitrary dict reported `connector_error` | Dict rejected as generic `parse_error`, no candidates/proof created |
| 1.3 migration | API old lead had no explicit offer, `IndexError` | Old lead/query/price and legacy saved rule survive; explicit unknown selected price/seller/binding, no backfilled proof |
| Known rejection | Accessory comparison was only unresolved | Explicit rejected comparison; intended watch still cost/freshness unresolved |
| Actual browser | Old frontend rejected new identity states; `.discovery-row` timed out after 25 seconds | New feed renders states and evidence, keyboard save/reload, five named cases, rejected dial mapping, used auction separation, desktop and 375px, no browser errors |

Additional application assertions cover 2035/VH31, dial mint/Space Gray, 39/42 mm,
strap steel/FKM, generation, date, Casio suffix, manufacturer conflicts, repeated
AI/copy lineage, first-SKU, generic stock, unknown assertions, missing observation
time, foreign destination, out-of-stock, selection/basket mismatch, credential URLs
and refused qualification HTTP writes. An AI claim reusing a direct claim's ID
cannot change the accepted value. Missing width/dial does not satisfy preferences.

## Final verification and repeatable commands

Use only the existing Python environment with **this checkout's source**:

```sh
MONITORING_PYTHON=/Users/jay/.t3/worktrees/pricerecon/t3-7260bb2e/.venv/bin/python
PYTHONPATH="$PWD/src:$PWD" "$MONITORING_PYTHON" -m pytest -q tests/test_qualification_workflow.py tests/test_discovery_workflow.py tests/test_monitoring_workflow.py
```

The final result is **29 passed**: 9 qualification, 5 discovery and all 15 legacy
monitoring workflows. Legacy coverage includes migration, matching, scheduling,
notification dispatch, failure preservation and fresh-process restart. The harness
blocks real HTTP/native curl/browser acquisition/process escapes; no unsafe global
or default-database API test suite was run. A preceding final run overlapped Vite's
clean/rebuild with an application import and hit a transient missing `dist/assets`
directory. Final verification was repeated after build completion, with no build
running during application tests: **29 passed in 29.72s**.

Frontend uses a symlink to the integration checkout's already installed
`frontend/node_modules`. No installs/downloads were performed. In `frontend`:
`npm test -- --run` passes all **25** existing tests; `npm run build` passes
TypeScript and Vite. The existing greater-than-500-kB bundle warning remains.
Focused Ruff on changed Python/application harness files and focused mypy on the
qualification/discovery/category/acquisition/API plus app/schema/Watch executor
pass; `git diff --check` passes. The repository's ESLint configuration remains
absent; `npm run lint` fails before checking source because ESLint 10 cannot find
`eslint.config.*`. No suppression, threshold reduction or config workaround was
added. Dependencies/lockfiles are unchanged; this is not a release audit.

Actual browser verification uses the retained fixture/driver with an explicit
qualification option and the installed agent-browser/Google Chrome fallback:

```sh
PYTHONPATH="$PWD/src:$PWD" "$MONITORING_PYTHON" -m tests.monitoring.discovery_ui_server --port 8883 --qualification
python3 -m tests.monitoring.discovery_browser_check --port 8883 --qualification --artifacts /tmp/pricerecon-ticket03-browser
```

The driver checks the test-only fixture identity marker **before** preference
writes, uses its own empty-config browser session restricted to loopback, opens
field claims and checks visible extractor text. Final screenshots and receipt:
[desktop](artifacts/watch-qualification/desktop.png),
[375px](artifacts/watch-qualification/narrow.png),
[receipt](artifacts/watch-qualification/receipt.json).
The fixture shutdown receipt is `blocked_edges=[], notifications_sent=0,
searches=3, temporary_storage=true`; its one legacy enabled job remains retained.
The fixture-only identity endpoint is not registered by the application.

The installed CLI still returns `Unknown command: skills` for the skill's
`skills get core` entry point; its installed `--help` supplied the command
reference. No install was used to work around that version mismatch.

## Limits and handoff

No live merchant evidence, entitlement, retention/deletion implementation,
longitudinal history, numerical freshness policy or buyer acceptance is claimed.
Real adapters need reviewed authority/selection/context mappings in later work;
no existing real normalized output is silently promoted. Human adjudication and
invalidation writes remain ticket07; full comparable-offer ranking is ticket08.
No cost/savings computation, collection activation, credentials/accounts,
production DB, deployment, push or PR was used. No delegation was used.

The dirty parent checkout was not edited or used for execution; only its existing
Python environment was reused. Its tracked-diff SHA-256 remained the retained
pre-task value `38ab9795757655e9119022af759fe392bfb901bce1ce8175038fc6c0b73e8914`.
Integration checkout was read only. The final integration tip is merged into this
branch before handoff and its ancestry confirmed; no merge into integration or
ticket closure was performed.
