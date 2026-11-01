# Adversarial buyer walkthrough run — 2026-11-01

**Stance: buyer who suspects the app will lie, plus an attacker trying to launder
synthetic/fixture evidence into live-looking claims.** This run's job was to
**falsify** the [buyer walkthrough kit](buyer-walkthrough.md) and to catch any state
that would mislead a reasonable buyer. It is the counter-run to the
[faithful agent-run of 2026-10-31](walkthrough-agent-run-2026-10-31.md), which
*verified* the kit's Expect lines; this run *attacks* them. Where that run recorded
"evidence match", this run tried to make the screen show the opposite or something
ambiguous. A task is recorded **pass** only where an attack **failed** to falsify it.

**This run does NOT clear the human-comprehension gate.** It upgrades behaviour
verification to **adversarial confidence**; the buyer's own understanding of what the
app knows, does not know and is withholding remains **unproven pending the buyer's own
session**. The misleading states found below are fix items before that session, not
reasons to skip it. No claim here is signed for the buyer.

Read-only in code: findings are reported, nothing is fixed in this run.

## 1. Session setup and routes

- **Synthetic fixture (mutation target).** A fresh guarded walkthrough fixture
  (`tests.monitoring.discovery_ui_server --workflow` — temporary SQLite, paused
  scheduler, captured transports, audit-guarded edges, zero outbound) was built from
  this worktree and served on a loopback port. The three long-running fixture servers
  the brief reserved (8893–8895) were probed read-only at start and again on shutdown:
  **not listening; nothing killed or touched.** Two fresh fixture instances were run
  in turn (the first was deliberately polluted with crafted attack state, then
  discarded; the second, clean, ran the session-script steps `baseline → cross →
  duplicate → drop → costs → coupon`).
- **Marker gate** (`/api/offline-verification`) reported `ticket12-connected-ui-v1`,
  `temporary_storage=true`, `automatic_checks=false`, `blocked_edges=[]` before any
  task. The fixture's final guarded-shutdown receipt on the clean instance reported
  `blocked_edges=[]` and only the enabled legacy watch in the scheduler.
- **Deployed instance (read-only probes).** Probed over the documented encrypted
  guest-agent route via the hypervisor host (the direct LAN route to the app VM is
  recorded as known-bad and was not retried; no authentication or configuration
  change was made). Only GETs were issued against the deployed instance. Because the
  deployed API is **unauthenticated on the LAN** (accepted-risk posture recorded in
  [deploy-2026-10-30](deploy-2026-10-30.md)), its read surface was treated as part of
  the attack surface; **no** POST/PUT/DELETE was sent to the deployed instance — all
  mutations went to my own fixture.
- **UI driving.** Headless Chrome through the repo's own `agent-browser` pattern
  (`--allowed-domains 127.0.0.1`, unique session), at desktop width and the fixture's
  own local-only image mode (no outbound image fetches). API probes were direct reads
  (fixture) and the guest-agent route (deployed).
- **Crafted-state method.** The synthetic-laundering and fabricated-value attacks
  below plant adversarial payloads in the fixture's temporary SQLite (my own fixture)
  and then re-read through the **real** `/api/discovery/assessments` and
  `/api/discovery/candidates/{id}/history` read paths. This models the threat the #149
  marker derivation explicitly claims to defend against — "a payload written before
  the marker existed (or by any writer that omits it) would re-serve a fixture-decided
  amount as a live market fact … Re-derive from the retained paths on every read …
  never downgraded" (`src/pricerecon/models/assessments.py:65-78`). A read-path
  derivation that can be defeated by a crafted stored payload is exactly the contract
  under test.

## 2. Findings (ranked)

Each finding: **attack attempted → exact reproduction → what the app showed vs what
honesty requires → what a buyer would wrongly conclude**, and **confirmed by
reproduction** vs **reasoned only**.

### F-1 (major) — Synthetic-laundering: a fixture amount with absent/stripped `paths` reads `synthetic: false` · **confirmed**

- **Attack.** Plant a stored price claim whose amount is fixture-decided but whose
  provenance paths are empty, and try to get `synthetic: false` served on it. This is
  the "strip the paths" laundering move: the marker derivation re-derives from
  `paths`, so with no paths there is nothing to derive from and the stored flag wins.
- **Reproduction** (fixture SQLite write, then real read path):
  1. Clone a live `discovery_price_assessments` payload; set
     `current_best = {state: "supported", amount: "45.10", synthetic: false, paths: []}`
     (and the same for `observed_low`); insert as a new assessment row.
  2. `GET /api/discovery/assessments` → serves
     `current_best: {state: "supported", amount: "45.10", synthetic: false}`.
  3. Model-level boundary (the derivation's exact behaviour):
     | stored claim | result |
     |---|---|
     | unmarked `synthetic` default + one synthetic path | upgraded to `true` ✓ |
     | `synthetic:true` + retained path | stays `true` (never downgraded) ✓ |
     | unmarked + mixed paths | upgraded to `true` ✓ |
     | **unmarked + retained-only path** | **stays `false`** ✗ |
     | **unmarked + empty `paths` + amount set** | **stays `false`** ✗ |
     | **`synthetic:false` + empty `paths` + amount set** | **stays `false`** ✗ |
- **Showed vs required.** Honesty requires that a fixture-decided amount always read
  `synthetic: true`, and that "an unmarked stored payload is upgraded to synthetic,
  never downgraded" (`models/assessments.py:65-78`, kit S1). The app shows
  `synthetic: false` whenever no retained path carries `synthetic: true` — i.e. when
  the paths are empty, absent, or all marked non-synthetic. The fail-closed claim
  holds **only when at least one path is present and marked synthetic**; it is blind to
  a path-less claim. The frontend parser (`frontend/src/lib/assessments.ts`) accepts an
  explicit `synthetic:false` and would therefore **suppress** the per-amount warning
  "Synthetic verification data: … not a live market fact."
- **Buyer would wrongly conclude.** "Lowest verified total among offers checked:
  GBP 45.10" with **no** synthetic warning — a fixture amount presented as a live
  market fact.
- **Reachability caveat (why major, not blocker).** Planting the payload needs a DB
  write (or a future/legacy writer that emits path-less claims). There is no public
  HTTP endpoint that writes assessments directly. But the derivation's stated purpose
  is precisely to defend stored/legacy/tampered payloads, and it fails that purpose for
  the path-less shape.

### F-2 (major) — Synthetic-laundering: FX-quote / benefit / coupon-resulting-cost-FX evidence is not scanned by the marker derivation · **confirmed**

- **Attack.** Defeat the derivation's coverage, not just its path count. The synthetic
  scan (`src/pricerecon/db/history.py:252-254`) computes
  `synthetic = any(c.retention == "synthetic" for c in offer.evidence + cost_claims + coupon_claims)`,
  where `cost_claims` = scenario `context_evidence` + **component** evidence only. It
  **omits `CostScenario.fx_quotes[].evidence`, `CostScenario.benefits[].evidence`, and
  (inside the coupon chain) `resulting_cost.fx_quotes[].evidence`.** A synthetic
  **FX quote decides the converted amount** (the exact mechanism behind the fixture's
  Casio `GBP 49.68` = 48 + 2.10 × 0.8), so a fixture-decided amount can hide in the
  one channel the derivation does not read.
- **Reproduction.**
  1. Model-level: build a `CostScenario` whose scanned evidence (context + components)
     is `retention: "minimal_fields"` and whose **only** synthetic evidence is a
     distinct FX quote (`fx_quotes[0].evidence[0].retention = "synthetic"`) plus a
     synthetic benefit. Replicating the exact history scan returns
     `synthetic = False` → `evidence_kind = "retained"`, `market_history_eligible = True`.
  2. Real read path (fixture SQLite): flip every scanned evidence row to
     `minimal_fields`, leave a synthetic FX quote in `discovery_cost_scenarios`, then
     `GET /api/discovery/candidates/{id}/history`. The observation flips
     **`evidence_kind: "synthetic" → "retained"`** purely because the surviving synthetic
     evidence is in the un-scanned FX channel. (The previously stored claim stayed
     `true` only via never-downgrade; a **fresh** `evaluate_comparisons` on that state
     builds `path.synthetic = observation.evidence_kind == "synthetic"` = `False`.)
- **Showed vs required.** Honesty requires the marker to cover every evidence channel
  that can decide a fixture amount ("coupon-chain evidence included in the derivation",
  kit S1, `db/history.py:190-196`). The app covers offer/cost-component/coupon chains
  but **not the FX/benefit channels** that can decide the payable. The claim in kit S1 —
  "re-derived from the underlying paths on every read … never downgraded" — is
  incomplete for an FX-decided amount.
- **Buyer would wrongly conclude.** An amount whose real provenance is a synthetic FX
  rate reads `evidence_kind: "retained"` and can back a `synthetic: false` claim →
  treated as live market evidence and even counted toward market history.
- **Note.** In the *stock* fixture this is masked only accidentally: the FX quote reuses
  the scenario's `context_evidence` objects (`tests/monitoring/watch_workflow.py:160-170`),
  which are scanned. The moment a fixture uses a distinct FX-evidence record (a normal
  shape), the marker leaks. This is the same class the coupon-chain fix already closed;
  FX/benefit were left out of that fix.

### F-3 (major) — Fabricated value: a total is accepted with an unknown/missing component at the decision layer (S2 read-path leak) · **confirmed**

- **Attack.** Force a delivered total where a payable component is missing: plant a
  `CostScenario` with `state = "verified_at_observation"`, `total = GBP 45.10`, but a
  **shipping component in `state: "unknown"` with `amount: null`**, and see whether the
  assessment/tracking decision layer still claims the total.
- **Reproduction** (model decision layer, `core/exact_tracking.assess_scenario`): with
  valid evidence times and one unknown shipping component, the result is
  `delivered_gbp = 45.10`, `state = "eligible"`, `reasons = ["qualifying_observation"]`
  — identical to the all-known-component control. The unknown shipping does **not**
  withhold. `assess_scenario` checks only `cost.state == "verified_at_observation"`,
  `cost.total is not None`, `cost.total.currency == "GBP"`; it never re-derives the
  total from the components or requires every component to be present/known.
  `assess_observation` then uses `checked.delivered_gbp` as a `ComparablePath.amount`,
  and `claim()` publishes it as `current_best`/`observed_low`.
- **Showed vs required.** Honesty requires "a delivered total computed with an unknown
  component" to be a red flag and "Unknown … never folded into a total" (kit S2/E2).
  That is enforced **only at write time** by `core/costs.evaluate_cost` (which refuses to
  set `total` when any issue exists, incl. `{kind}:unknown`). The **read/decision layer
  trusts the stored `total`/`state`** and will consume a forged total → a "verified
  delivered total crossed your target" alert and a "Lowest verified total … GBP 45.10"
  claim backed by a total containing an unknown component.
- **Buyer would wrongly conclude.** A delivered total is complete and verified when it
  silently rests on an unknown (here: shipping) charge.
- **Reachability caveat (why major, not blocker).** Through the normal acquisition path
  `evaluate_cost` will not emit such a scenario; this needs a crafted/legacy/migrated
  stored scenario (or any writer that bypasses `evaluate_cost`). But it is exactly the
  fail-closed-on-read posture the honesty machinery claims, and it is not enforced at
  read.

### F-4 (minor) — Comprehension trap: a historical assessment reads "Current comparison unavailable. Lowest verified total among the offers checked." · **confirmed**

- **Attack.** Put an assessment into the historical/withdrawn state the walkthrough
  visits (I2 correction, or any superseded revision) and read the mounted History view.
- **Reproduction** (rendered UI, Addiesdive History view after steps/correction): every
  historical assessment renders the literal line
  > **Current comparison unavailable. Lowest verified total among the offers checked.**
  (`frontend/src/pages/Discovery.tsx:452-458`: for a non-supported/historical claim the
  headline is the static `'Current comparison unavailable'`, then `'.' + reason`, where
  the reason string is the claim's generic `"Lowest verified total among the offers
  checked."`).
- **Showed vs required.** Honesty requires an unavailable/historical claim to read as
  unavailability, not to trail a superlative price assertion. The reason fragment is
  unlabelled, so the screen juxtaposes "unavailable" with "Lowest verified total among
  the offers checked" — a contradiction on its face. (The correct cases render fine:
  `"Current comparison unavailable. No qualifying comparable observations in the
  disclosed scope."`)
- **Buyer would wrongly conclude.** That there *is* a lowest verified total among the
  offers checked, despite the assessment being unavailable/historical. It recurs on
  **every** historical revision, i.e. throughout the I2 state the session visits.

### F-5 (minor) — Comprehension trap: mixed-currency Costs summary hides the FX basis · **confirmed**

- **Attack.** Read the Casio Costs view at the post-`costs` state (USD shipping resolved
  through a synthetic 0.8 GBP/USD payment-FX quote).
- **Reproduction** (rendered UI): the summary reads
  > Public total, no coupon — **GBP 49.68** — Verified at observation
  > Merchant payable **GBP 48; USD 2.10** · Known subtotal **GBP 48; USD 2.10**
  > … shipping (2) **USD 2.10**; observed …
  The USD→GBP conversion rate (0.8) and its evidence are **not** rendered on the Costs
  summary (they live in the scenario `fx_quotes` in the record/Technical JSON — the kit
  already flags this as D-4/Partial).
- **Showed vs required.** On screen `48 + 2.10` does not visibly reconcile to `49.68`;
  the arithmetic only closes with a conversion factor the buyer cannot see on this
  surface. Honesty (E4) wants the FX assumption visible where the total is presented.
- **Buyer would wrongly conclude.** Either that the total is wrong (48 + 2.10 = 50.10)
  or, worse, accept `GBP 49.68` without seeing that a foreign-currency charge was
  converted at a synthetic rate. The total is *correct* and the conversion is *evidenced*
  — but the summary hides the basis, so it cannot be checked on the screen it appears on.

### F-6 (nit) — Redundant/echoed claim sentence on the current assessment · **confirmed**

- **Reproduction** (rendered UI, Addiesdive History, current revision): the line reads
  > **Lowest verified total among offers checked: GBP 45.10. Lowest verified total among the offers checked.**
  (headline `Lowest verified total among offers checked: GBP 45.10` + `.` + the reason
  string `"Lowest verified total among the offers checked."`). The reason duplicates the
  headline verbatim. Not a false fact, but a reader may wonder whether these are two
  different claims. Suggest de-duplicating or labelling the trailing clause as the reason.

### Not-a-finding (recorded as attacks that failed)

- **Stored XSS / SQL injection / unicode in watch names and correction rationales —
  pass.** A correction saved with actor `Adv tester <script>alert(1)</script>` and
  rationale `Race probe; DROP TABLE discovery_leads; -- ᴍ ሴ 😈` renders **inert**: the
  `<script>` appears as literal text, no injected `<script>` node (page has exactly one
  `<script>` — the app bundle), no alert/dialog, and the SQLi text is inert
  (parameterised queries; values rendered as text). There is **no
  `dangerouslySetInnerHTML`/`innerHTML`/`eval` anywhere** in `frontend/src`; inputs are
  bounded (actor ≤250, rationale ≤1000, value ≤500) and field-validated. Lineage
  renders correctly (`dial: mint → salmon (corrected)` with actor + rationale).
- **Race / robustness — pass.** (a) Stale-write replay of a correction → **409**
  "Identity or correction changed; reload before saving." with no success message.
  (b) Two concurrent corrections from the same `expected_revision` → exactly **one 201
  + one 409**, a single lineage entry (no double-apply, no lost update). (c) Oversized
  value (5000 chars) → **422**; unknown field → **422**; negative `expected_revision`
  → **422**. (d) The correction transaction rolls back cleanly on the 409 path.
- **Usual-price / savings from sparse history — pass on the buyer surface.** `savings`
  is typed `None` in the models (a non-null value fails validation), `usual_price`
  defaults to `unavailable`, and the mounted History view hard-codes "**Usual price
  unavailable.** … No savings claim." (observed in the rendered UI). No percentage-off
  or "you save" text appears anywhere. *(Minor residual, reasoned: the assessment
  parser `claim()` in `frontend/src/lib/assessments.ts` does not itself refuse a
  `usual_price` of `state:"supported"` with an amount — only `parseHistory` rejects a
  non-null usual amount. The mounted buyer surface is safe because it renders static
  text, but the "Complete retained record" JSON could carry a crafted usual_price. The
  history parser and model defaults keep the buyer-facing claim withheld.)*
- **Coupon expiry / stacking / cashback — pass at the decision layer.** The public cost
  path gate (`core/coupons.public_cost_paths`) admits only a `reproduced_at_observation`
  coupon with **no issues**, a typed direct receipt, and public non-conditional terms;
  `assess_scenario` independently withholds `coupon_expired_or_not_started` /
  `coupon_validity_unknown`. Promotions are never summed (each coupon is its own path;
  the minimum wins), and cashback/conditional benefits are `excluded_from_payable`.
- **Cohort separation / current-bid-as-price — pass.** `cohort_for` keys on
  condition + quantity + purchase_mode (+ buyer context), so used/auction/new never
  share one comparison; `assess_scenario` withholds `offer_unavailable_or_not_buy_now`
  for any non-`buy_now` offer, so a current bid is never a purchase price.
- **Missing-costs block totals on the normal write path — pass.** `evaluate_cost` sets
  no total when a component is unknown/conflicting (E2/S2 hold for any
  `evaluate_cost`-produced scenario). **The gap is only at read (F-3).**
- **Deployed-instance honesty posture — pass (read-only).** `GET
  /api/discovery/assessments` → `{"items":[],"reason":"Explicit comparison policy
  required; no production calibration is assumed."}`; `GET /api/discovery/collection` →
  `state:"blocked"`, `activation:"staged"` with `live_activation_not_authorized` among
  the gates; `GET /api/discovery/watches` → source-coverage roster with per-lane
  reasons/prerequisites. No live amount is claimed. (The unauthenticated read surface
  returns watch/price/coverage data to any LAN caller — the documented accepted risk,
  and the surface on which F-1/F-2 would matter if crafted data were ever stored.)

## 3. Falsification table

Per cluster A–K and spot-checks S1–S5. "pass" = an attack **failed** to falsify the
kit's Expect lines for that cluster. Prior "partial" tasks (the 15 from the faithful
run) were attacked first.

| Cluster | Attack outcome | Notes / finding |
| --- | --- | --- |
| A — Monitoring preservation | pass | Queue/watches preserved across discovery + corrections; the A2 saved-interval gap is the known D-8 app UX item, not a new falsification. |
| B — Discovery feed & preferences | pass | Labels, strengths, banner and custom-value persistence hold; placeholders are honestly captioned (no substitute images). |
| C — Identity & uncertainty honesty | pass | Unknown dimensions never silently satisfied; unresolved/conflicting states labelled; item lead never a delivered total. |
| D — Seller, condition & cohorts | pass | Cohort separation and pinned `authenticity/internal_health = unknown` hold; no current-bid-as-price. |
| E — UK delivered cost & missing costs | **finding F-5** | Missing-cost write path holds (E2/E3); but the Costs summary hides the FX basis behind a mixed-currency total (F-5). Fabricated-total read leak (F-3) also lives here. |
| F — Coupons & conflict withholding | pass | Expiry/stacking/cashback withholding holds at the decision layer; no reduced payable from an advertised code. |
| G — Assessments & history honesty | **finding F-4 (+F-6)** | Three-way separation and no-savings hold; but historical assessments read "Current comparison unavailable. Lowest verified total among the offers checked." (F-4) and the current claim echoes its own reason (F-6). |
| H — Coverage & freshness disclosure | pass | Roster scopes, caps-as-unset, age/freshness and no-catch-up hold. |
| I — Corrections & lineage | pass | Lineage append-only with actor/rationale/time; dependents withdrawn not transferred; 409 rejection honest. |
| J — Exact tracking | pass | Crossing/suppression/further-drop logic holds; alert never from unknown/conditional total **on the normal path** (the F-3 forged-total case is the read-layer exception). |
| K — Source evidence | pass | Per-claim issuer/extraction/retrieval/lineage and named withholding gates hold. |
| **S1 — Synthetic provenance, fail-closed** | **finding F-1, F-2** | Marker derivation defeated by (a) absent/stripped `paths` and (b) un-scanned FX/benefit/coupon-FX evidence channels. |
| **S2 — Missing costs block totals** | **finding F-3** | Enforced at write; the read/decision layer accepts a stored total with an unknown component. |
| S3 — Savings never render from sparse history | pass (buyer surface) | `savings` typed-null + static "No savings claim"; minor assessment-parser residual noted. |
| S4 — Expired/conflicting coupons withhold | pass | Expiry and non-summing enforced at decision; base total untouched by an advertised code. |
| S5 — Corrections invalidate dependents + lineage | pass | Withdrawal/invalidation/lineage/retained targets all hold; injection inert. |

Counts: **11 clusters/spothecks pass, 4 carry findings** (E→F-5, G→F-4/F-6, S1→F-1/F-2,
S2→F-3). Behaviour-verification verdict is therefore **Accept with follow-ups** *only in
the narrow sense that the fail-closed honesty contracts S1 and S2 are breached under
crafted state* — see the scope statement below.

## 4. What this run does and does not clear

**What it does:**

- Upgrades the behaviour verification from "the app did the right thing in the faithful
  run" to **adversarial confidence** on the tested surfaces: I actively tried to make
  the app lie (synthetic-laundering, fabricated totals, forced savings, coupon stacking,
  cohort mixing, XSS/SQLi, races) and recorded where it held and where it broke.
- **Confirms three honesty-machinery gaps that a reasonable buyer could be misled by if
  adversarial state is ever stored** (F-1, F-2, F-3) and **two on-screen comprehension
  traps** (F-4, F-5) that appear in states the normal walkthrough actually visits.
- Confirms the injection/race defences (XSS/SQLi inert, 409 + concurrency correct) and
  the deployed instance's honest empty/refusing posture.

**What it does NOT clear (explicitly):**

- **The human-comprehension gate.** Nothing here shows the *buyer* correctly understood
  what the app knows, does not know and is withholding. That is the buyer's own session,
  in his own words. The traps found here (esp. F-4) are precisely the kind of thing that
  session must adjudicate — they are **fix items before the buyer's session**, not
  substitutes for it.
- **Live-market gates** (unchanged from kit §4): live offer obtainability, live
  delivered totals, live coupon success, history/savings calibration, operating limits,
  release/activation maturity, live manufacturer provenance. This run was offline except
  the app's own UI/API; every amount is fixture arithmetic.
- **The normal-path behaviour** the faithful run already recorded is not re-signed here;
  where I did not falsify a task I am reporting "attack failed", not fresh full
  verification of every Expect line at both viewports.

**Net:** the app's honesty machinery is strong on the happy path and under the shipped
fixture, but its **fail-closed-on-read claims (S1 marker derivation, S2 total
completeness) are not actually fail-closed against crafted/legacy stored payloads**, and
two label/wording states (F-4, F-5) can mislead a reader. Fix F-1/F-2/F-3 before any
wider exposure or any live data lands, and fix F-4/F-5 before the buyer's comprehension
session.

## 5. Claims I could not test (and why)

1. **Any live-market claim** (offers, delivered totals, coupons, savings calibration) —
   hard offline constraint; no merchant/provider calls were made, no live acquisition.
2. **The `channels_unset` no-channel crossing and the ambiguous-send reconciliation
   dialog** — unreachable in a single fixture run (no ambiguous delivery state is
   produced); suite-pinned per the kit's Partial note. Not attacked here beyond reading
   the copy.
3. **Remote reference-image captions** in the outbound image mode — the no-outbound
   constraint kept images local, so the availability-gated captions were not exercised
   (the placeholder path is what rendered).
4. **Malformed query-param/ID fuzzing on every endpoint** — I probed the correction
   write and read paths and the discovery reads; I did not exhaustively fuzz every route
   with unicode/SQL/XSS payloads (the input models are bounded and literal-constrained,
   and React escapes all rendered values, so the injection class is well defended where
   tested).
5. **Whether a real writer can emit path-less or forged-total payloads** — I proved the
   read layer *accepts* them; I did not find a reachable HTTP writer that *produces* them
   (assessments are computed, not stored via the public API). The findings stand as
   fail-closed-on-read gaps regardless of the current writer set.
6. **Physical/operating limits and release maturity** (kit §4 gates 5–6) — out of scope
   for this offline run.

## 6. Constraints honoured

- Offline except the app's own UI/API. No merchant/provider calls, no pilot/live
  acquisition, no live-fact publication. The live-pilot one-shot grant marker file was
  never read or modified.
- Deployed instance: **read-only** (GETs only over the documented guest-agent route);
  every mutation ran against my own temporary fixture, destroyed with its guarded
  shutdown. The reserved fixture ports 8893–8895 were probed read-only and left
  untouched; nothing was killed that I did not start. Both of my fixture servers were
  stopped on completion.
- No production-code changes: this document only. No push.
- This report passes `scripts/check_public_markers.py` (deployed topology referred to
  as "the deployed instance" / "the app VM" / "the hypervisor host's guest-agent route";
  no private IPs or deployment hostnames).
