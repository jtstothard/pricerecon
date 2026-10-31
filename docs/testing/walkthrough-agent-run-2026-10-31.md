# Agent-executed buyer walkthrough run — 2026-10-31

**This run does NOT clear the human-comprehension gate.** This was an
AGENT-EXECUTED walkthrough of the [buyer walkthrough kit](buyer-walkthrough.md)
(the authority for session setup, the tasks, the S1–S5 honesty spot-checks and
the verdict form). It verifies that the application's **behaviour** matches the
kit's expectations and records observed evidence. Human comprehension — the
buyer (Jay) looking at the deployed application and correctly understanding what
it knows, does not know and is withholding — remains **unproven pending the
buyer's own session**. Nothing here is signed for the buyer; the acknowledgement
and signature slots in the verdict form below are deliberately left empty.

Per the kit's recording convention, each task ends with an evidence-match
(yes / partial / no): *did the evidence on screen match the claim the task
made?* The "buyer's words" half of the convention is empty by construction —
there was no buyer in this session. Overclaiming is treated as a defect: where
the kit's Expect line did not hold as written, the disagreement is recorded as a
discrepancy in section 5 rather than smoothed over.

Note on task count: the brief said "37 tasks"; the kit itself enumerates **33
tasks (A1–K2)** across eleven clusters, plus five spot-checks S1–S5. All 33
tasks plus S1–S5 were walked.

## 1. Session setup and routes

### 1.1 Health re-probe of the deployed instance (read-only)

The deployed instance on the app VM (two-service compose stack, app on port
8000, shape per [deploy-2026-10-30](deploy-2026-10-30.md)) was re-probed through
the working control channel — the encrypted guest-agent route via the
hypervisor host (the direct LAN route to the app VM has timed out before and was
not retried; no authentication or configuration change was made):

- `GET /api/health` (loopback on the app VM) → **200** `{"status":"ok",
  "connector_states":{…}}` at 2026-10-31T11:52Z — the deployed instance is up
  and healthy, with its usual mixed connector posture (several `ok`, plus
  pre-existing `bot_blocked` / `parse_error` / `degraded` entries with their
  recorded last-check timestamps). No live provider request was made by this
  probe; it is a loopback read of the app's own cached health state.
- `GET /api/discovery/assessments` (loopback, read-only, end of session) →
  **200** `{"items":[],"reason":"Explicit comparison policy required; no
  production calibration is assumed."}` — the production honesty posture from
  the deployment receipt is unchanged, and this run mutated **nothing** on the
  deployed instance.

### 1.2 Session route (synthetic fixture)

The walkthrough ran against the kit's fixture/synthetic session route so that no
real production data could be mutated:

- A **fresh** fixture UI server was started for this session, per the kit's
  setup ("Start a fresh fixture for this session"): the guarded
  `tests.monitoring.discovery_ui_server --workflow` server (temporary SQLite,
  paused scheduler, captured notification transport, audit-guarded edges),
  built from `origin/main` @ `07b6127` in a throwaway worktree, served at
  `http://127.0.0.1:8896`.
- The three long-running fixture servers the brief expected on ports 8893–8895
  were **not listening** at session start (probed read-only; nothing was killed,
  nothing was touched). The pre-existing Python listeners on other local ports
  are unrelated static/file servers and were left alone.
- Pre-session marker gate (the kit's "If the marker differs, stop"):
  `/api/offline-verification` returned fixture `ticket12-connected-ui-v1`,
  `temporary_storage=true`, `automatic_checks=false`, `blocked_edges=[]`,
  `notifications_sent=0`, `images=ticket12-private-images-v1; Casio only; four
  explicit gaps`. **Fixture marker id: `9b8454f0e9ff4bc4af43c04cbef3e056`.**
- Final guard receipt at shutdown (SIGINT): same identity, `blocked_edges=[]`,
  `notifications_sent=2` — zero guarded-edge violations across the entire
  session, and the scheduler still listed only the enabled legacy watch. The
  temporary database was removed by the harness.
- Fixture steps ran through the run-bound conductor
  (`tests.monitoring.watch_workflow_ui --step …`) in the kit's session-script
  order: `baseline` → `cross` → `duplicate` → `drop` → `costs` → `coupon` →
  `stale`. Fixture clock: synthetic 2026-10-27T12:00:00Z → 15:04:48Z.
- UI driving: headless Chrome through the repo's own agent-browser pattern
  (`--allowed-domains 127.0.0.1`, unique session), at 1280×900 and 375×812,
  plus direct API reads. Actions were performed through the UI wherever the kit
  asks the buyer to act (preferences, targets, correction) and cross-checked
  against the API.

**Image-mode choice (affects B1/B3):** the session used the fixture's documented
local-only image mode (`?walkthrough=ticket12-local`) so that **no outbound
request left the machine** (hard constraint: the walkthrough exercises the app's
own UI/API only). Remote image bytes for the Addiesdive/Militado/San Martin
reference images were therefore deliberately not fetched; those candidates show
the honest placeholder ("Product image unavailable. Generic placeholder; does
not depict this watch.") plus their retained attribution/configuration
notes/original-source links. The two real Casio reference photographs render
from the fixture's own registered local assets.

## 2. Per-task results (session-script order)

Evidence-match answers: did the evidence on screen match the task's claim?
Buyer words: empty (agent run).

| # | Task | Evidence match | Observed evidence / notes |
| --- | --- | --- | --- |
| 1 | A1 — Saved searches survive discovery | yes | Baseline queue noted before any discovery use (UI edit form + API record): watch 7 "My compact colourful choices" / fallback query / raw CeX query ` (ML05 OR "ML05B") -parts  ` / synonym groups [ML05,ML05B],[blue,mint] / excluded title term `parts` / price ceiling 100.00 / enabled / 30m, Europe/London, 09:00–18:00 mon–wed / notifications webhook+telegram+discord; watch 8 "Paused saved search" paused. End-of-session diff vs baseline: **identical except `updated_at`** — discovery created, edited and deleted nothing. Note: notification destinations and `excluded_title_terms` are not surfaced by the edit form (API record only); the form's "Excluded terms" maps to `filters.exclude_patterns` (empty), confirmed by `WatchForm.test`. |
| 2 | A2 — Editing one field preserves the rest | partial | Edited only `display_title`, saved, reloaded: full record diff showed **only** `display_title` + `updated_at` changed — destinations, timezone/window, exclusions, raw per-source queries, filters, grouping all retained. Saved custom interval renders as its own option at load ("Every 30m (saved)"). **Missing:** the Do's change-and-restore leg — once the interval select is changed away, the "(saved)" option is removed (`WatchForm.tsx:506-507` derives it from live form state), so the saved custom value cannot be re-selected in-form (driver `select` on the old value fails); abandoning the form restores it. Change confirmed with the real driver, not synthetic events. |
| 3 | B1 — Independent illustrated feed | partial | Five candidates exactly as named (Militado ML05/ML05B, Addiesdive AD2066 mint, San Martin SN0144, Merkur Lightning salmon, Casio MTP-B145D-2A2VEF), all `origin=category_discovery` (API), not saved searches. Each card: title, delivered-price state ("GBP 70.10" / "Total unknown"), cost state ("Verified at observation · freshness unvalidated"), "UK delivered · no coupon · cashback excluded", supported specs ("steel · 35 mm · VH31"), identity/preference cautions, Product details / Track links. Session banner "Synthetic session · prices and buying evidence are test data." present at both widths; 375px shows no horizontal overflow. **Missing:** "illustrated" — in the no-outbound local mode only Casio renders an image; the other four show the honest placeholder (environmental constraint, see §1.2). Observed display order: Merkur, Militado, Casio, San Martin, Addiesdive. |
| 4 | B2 — Preferences and their exposed interpretation | yes | Set width 38 (hard), dial colours via **Other/custom** "mint, salmon" (soft), budget 150 (hard); saved; reloaded; re-checked at 375px. Interpretation lines exact: "Hard constraint. Compact means case width at most 38 mm." / "Soft preference. Colourful means one of these dial colours: mint, salmon." / "Hard constraint. Budget means public UK delivered total at most £150; item price alone is insufficient." + "Unknown dimensions stay visible for review. They do not satisfy hard constraints or soft preferences." Blank ("Not set") value renders "Unset." (observed in the initial saved state and via the select); the arbitrary value survives reload as a custom input — presets never replace it (`ChoiceValue.tsx` behaviour confirmed live). |
| 5 | B3 — Image provenance is labelled | partial | Casio product page: image caption "**Photograph**"; Technical image block: "Image source and attribution" (rights notice), provenance ("Official Casio Europe product image… Photo identity is independent of all synthetic price/selection evidence."), "Image evidence / Original image", "Permission: …", "Depiction: …" links. Merkur: "Product image unavailable. Generic placeholder; does not depict this watch." + "Placeholder"; no salmon substitute; "Dial colour unknown; title words and illustrations do not confirm colour." Militado (remote reference): configuration note "Original ML05 blue VH31 reference; ML05B Miyota target/configuration unresolved. These are not interchangeable." + attribution + "Remote display only; no licence or buying qualification claimed." + original-source/original-image links. **Missing:** the two availability-gated captions ("Product illustration; not a photograph" / "Remote reference image; exact configuration not established") render only when the image is available (`DiscoveryImage.tsx`); with remote bytes deliberately not fetched they show "Placeholder" instead. Cross-checked in mounted tests (`DiscoveryImage.test.ts`, `DiscoveryFeed.test.ts` — 92/92 frontend tests pass at this revision). |
| 6 | C1 — Unknown dimensions labelled, never silently satisfied | yes | Militado/Merkur cards: "Identity unresolved" + "**Preference fit unknown**"; totals "Total unknown"; `alert_eligible=false` (API). Product pages: "Unresolved configuration" section; Preference fit lines name the unknowns ("Case width unknown; compact fit needs checking." / "Dial colour unknown; title words and illustrations do not confirm colour." / "Delivered total unknown; an item price cannot satisfy this budget."). Costs view: "**Item lead — GBP 1**" beside "Total unknown"; caveat "Connector-reported item price only; may describe another variation or a normalized default."; "No bargain alerts until exact tracking and qualification." — the £1 lead never becomes a delivered total and does not satisfy the £150 budget. |
| 7 | C2 — Exact distinctions and conflicting evidence | yes | Evidenced configuration renders separate rows (product kind, maker, reference, generation, movement, case width mm, dial, strap, date display) — not merged titles. San Martin: mint configuration (evidenced) vs merchant selection dial "Space Gray" (binding record `variation_id=mint-vh31`, `resolution.state=rejected`, issue `dial: configuration_mismatch`, gaps `binding: selection_not_supported`) — merchant selection unresolved, binding not supported. Casio keeps the exact suffix "MTP-B145D-2A2VEF". Unresolved/conflicting states render as labels ("Qualification unresolved", "Comparison rejected", `missing_evidence` gap codes), never as certainty. |
| 8 | C3 — Variation binding and accessory/component distinction | partial | Binding separation verified in API + Technical record: selection values (Space Gray, `variation_id`) held apart from product identity and price scope; offer price is scoped to the binding, not the parent identity. Correction form field `product_kind` offers values **complete watch / accessory / component** (plus Not set / Other custom) — matches `corrections.ts:2`. **Missing:** the sentence the Expect quotes — "Reported selection and price scope do not establish a qualified binding" — lives in `SourceOfferEvidence` (`SourceCoverage.tsx:55-113`), which is **not mounted in any product view at this revision** (only its tests render it), and the walkthrough fixture's offers carry `source_evidence: null`, so no source-claims block exists to expand. See discrepancy D-1. |
| 9 | C4 — Discovery origins and merchant evidence stay separate | yes | Technical "Capture lineage": capture id, source listing id, reported source retained per lead ("Capture 1f142c89-… / Source listing casio / Reported source cex"). Per-claim rows carry Issuer ("connector_report from cex"), Extraction ("normalized_lead_v1 via connector_search_v1"), Retrieved, Source observation, Validity ("search lead; exact selection, identity and payable cost unverified") and "Derived from 1f142c89-…:cex:casio". A second candidate from the same query (San Martin) shows the **same capture id** — one acquisition lineage, copied claims not independent confirmation. |
| 10 | D1 — Offers describe what you can actually buy | partial | Per offer: "Synthetic merchant"/"Seller unknown", Condition ("new" / "Unknown"), Availability, Qualification state, Comparison state rows; hero repeats Condition ("Condition: new" / "Condition: Unknown"); API pins `authenticity: unknown`, `internal_health: unknown` for every offer; Militado/Merkur offer gaps name `purchase_mode: not_fixed_purchase_price`, `destination: uk_delivery_unproven`. **Missing:** "Source claims do not certify selected-SKU availability. Missing charges remain unknown." — same unmounted component + null fixture data as C3 (D-1). |
| 11 | D2 — Used offers and auctions sit in separate cohorts | partial | Every assessment carries its cohort in the API (`condition`, `quantity`, `purchase_mode`, configuration, buyer context, `eligibility: ordinary_public_purchase`); a current bid is never presented as a guaranteed purchase price (no auction case exists in this fixture). The named withholding reasons the Expect quotes ("Offer is unavailable or lacks a fixed buy-now price." / "Quantity, condition, destination or payment differs from the supplied policy.") exist in the eligibility vocabulary (`ExactTracking.tsx` reason map, rendered through "Alert eligibility details") but did not render this session: the tracked candidates' offers are all new/buy-now, and the not-buy-now leads refuse tracking. **Session-order note:** the task's Do needs a tracked watch; the script places D2 before J1, so the eligibility reading was taken at the J1 point. Cohort line confirmed via API/Technical as the kit's Partial note directs. |
| 12 | E1 — Delivered cost is itemised | partial | Addiesdive Costs: "Public total, no coupon — **GBP 70.10 — Verified at observation**"; scenario separates "Merchant payable GBP 70.10" / "Additional liabilities — No separately added evidenced amount" / "Known subtotal GBP 70.10"; charges itemised with kind, amount, state and reason — item £68 + shipping £2.10 + merchant tax £8.00 "Synthetic quoted VAT already included in item"; "Observed 2026-10-27T12:00:00Z. Freshness unvalidated."; other charges "unknown; not_applicable" and never folded into the total. **Missing:** "assumption text names currency/destination/dispatch context" — the base scenario's `assumptions` is empty, so the Costs view renders an empty assumption line; the currency/destination/dispatch context is retained in the scenario `context` + `context_evidence` (visible in the History/Technical records and the API). See D-4. |
| 13 | E2 — Missing costs block totals | yes | Militado/Merkur cards "Total unknown". Casio Costs: "Public total, no coupon — Total unknown"; "Known subtotal **GBP 48; incomplete, not a delivered total.**"; shipping rendered as `unknown; unknown` (never 0); API scenario `total: null`, `state: unknown`, unknown charge `amount: null`. No delivered total contains an unknown component anywhere. |
| 14 | E3 — Included VAT is counted once | yes | VAT charge reason reads exactly "Synthetic quoted VAT already included in item"; £70.10 = £68 + £2.10 with the £8.00 VAT marked `included_in: item` (API) and not added again. |
| 15 | F1 — Advertised code is not a reduction; no-coupon path works (first half, seeded) | yes | Addiesdive Costs: "Coupons and conditional benefits — **No verified applicable public coupon supplied.**"; base total GBP 70.10; compare and track proceed with no coupon at all. |
| 16 | J1 — Track an exact product from discovery | yes | Addiesdive: £60 target + webhook ticked → "Delivered target saved. Collection remains staged."; tracking block shows the exact tracked values (reference AD2066, dial mint, movement VH31, strap steel) and "Saving keeps this exact intent. Collection remains staged. A supplied policy and fresh qualified evidence are required before verified delivered alerts."; channel note "With no selected channels, no target message is sent." Casio: £40 target, no channels — same confirmation. Militado: "Exact identity must be resolved before starting exact tracking." and the save button is disabled — unresolved identities refuse tracking. Legacy queue untouched (diff-checked at the end). |
| 17 | J2 — One alert on a verified crossing (`baseline`, `cross`) | partial | `baseline`: "Above target · target £60 delivered", "Assessed delivered total £70.10.", reason "Verified at observation, above your delivered target." — zero sends. `cross`: "Eligible at target", £58.10, reason "**Verified delivered total crossed your target.**", exactly **one** alert event (`exact_target_crossing`), marker sends 0 → 1; delivery record `webhook: sent`, guarantee "External send/ack crashes are ambiguous; no exactly-once guarantee." **Missing:** the no-channel crossing clause — the fixture steps move only the Addiesdive price, so the no-channel Casio target never crosses (it stays withheld with the named gate "No qualifying source evidence was acquired; earlier evidence remains historical."); a live `channels_unset` crossing could not be produced (editing the Addiesdive target's channels mid-session re-baselined it — observed: "First qualified observation recorded; waiting for a qualifying price change."). The `channels_unset` event remains the recorded 2026-10-28 receipt. See D-7. |
| 18 | J3 — Repeat suppression and further drops (`duplicate`, `drop`) | yes | `duplicate` (58.10 again): nothing added — "Same offer and price, or no further drop; repeat alert suppressed."; sends stay 1. `drop` (56.10): "A further qualifying delivered-price drop." — second event, sends 1 → 2. No duplicate noise; a further qualifying drop alerts exactly once. |
| 19 | E4 — Currency, destination, dispatch and payment assumptions (`costs`) | yes | San Martin retained cost history rev 1→3: selected-dial trap (unknown) → missing shipping (unknown) → **Conditional** total GBP 70.10 ("Conditional", never "Verified") with the shipping component carrying assumption "Synthetic regional shipping quote requires confirmation" (API record). Casio rev 1→3: USD shipping without payment FX → total stays unknown; with the evidenced synthetic 0.8 GBP/USD `buyer_payment` FX quote (state `observed`, spread included) the total becomes "**GBP 49.68 — Verified at observation**" (arithmetic 48 + 2.10×0.8 ✓). Earlier unknown states retained in `/api/discovery/offers/{id}/costs` and the observations table, not overwritten. Note: component-level assumption text renders in the record/Technical JSON, not in the Costs view charge rows (D-4). |
| 20 | F1 — coupon block (second half, after `coupon`) | yes | "Synthetic TEN opportunity: **reproduced at observation**" + "Synthetic checkout evidence." + applicability "supported" + literal terms ("Synthetic TEN: one selected watch, GBP 40 item minimum incl VAT, web, no account restriction; no other promotions; 12:00 inclusive to 13:00 exclusive UTC.") + issues list (empty) + the coupon's own resulting-cost scenario "public coupon: Verified at observation — **GBP 45.10**" (item £43 + shipping £2.10). The public no-coupon total stays at its own base "**GBP 50.10 — Verified at observation**"; API `application.before_total: "50.10"`, `quoted_total: "45.10"`, `result: "applied"` — the receipt sits beside, never replaces, the base. |
| 21 | F2 — Eligibility, minimum spend, expiry and stack conflicts withhold | yes | `/api/discovery/offers/{id}/coupons` records eligibility (channel, new_customer, membership, eligible_base, terms_satisfied, reason), terms (starts_at/ends_at with inclusions, `minimum_spend: "40.00"` + basis "selected item including VAT; excludes shipping; before coupon", min/max quantity), `compatibility: "supported"` + `combination_rule: "Only TEN; no other automatic discounts or codes present"`, each with its own evidence rows; `coverage: "supplied_acquisition_evidence_only"`, `freshness: unvalidated`. Fixture coupon states observed: one public coupon (`reproduced_at_observation`, no issues) plus "No verified applicable public coupon supplied." elsewhere — no conflicting/expired case is scripted (suite-proven per the kit's Partial note); no reduced payable from an advertised code alone. |
| 22 | F3 — Public/personal/payment/cashback scenarios separated | partial | Cashback £10 recorded as a `ConditionalBenefit` with reason "**Excluded from payable**" on a separate `cashback` cost scenario (assumption "Synthetic cashback eligibility and later payment are unproven"); its scenario total is the same base (70.10) — cashback never enters the payable. It renders in the seed-state Costs view's "Benefits excluded from payable" block and is retained afterwards in the seed observation and offer cost history rev 1 ("cashback: GBP 70.10 · conditional" is a visible history row). **Missing at the task's scripted checkpoint:** after the price steps (which replace the offer's report), the current offer carries only the public scenario, so the cashback scenario exists only in retained history; and the non-public-coupon label "Conditional benefit excluded from public payable. Cashback is not checkout cash." has no fixture entry to exercise it. See D-5. |
| 23 | G1 — Usual price, current best and dated low are separate claims | yes | History view: "Scoped price assessment — Lowest verified total among offers checked: **GBP 45.10**." with the per-amount warning "**Synthetic verification data: the claimed amount is decided by fixture evidence, not a live market fact.**" directly beneath; scope line "Lowest among qualified offers checked in this scope only. Intervals are unobserved; no continuous availability, complete market or all-time claim."; "Retained dates … This does not establish current availability."; "**Usual price unavailable. … No savings claim.**" Retired revisions render "Historical assessment / Current comparison unavailable." with their own dated windows. API three-way separation: `current_best` 45.10 and `observed_low` 45.10 are distinct claims with distinct reasons, `usual_price.state: "unavailable"`, `savings: null`, `personal_price` unavailable. |
| 24 | G2 — Sparse history shows all directions, never a savings percentage | yes | "Load retained observations" table: six rows (seed + baseline + cross + duplicate + drop + coupon), unchanged observations retained as rows; each row shows its delivered total(s) or "Total unknown" (e.g. "public no coupon: GBP 70.10 · verified_at_observation / cashback: GBP 70.10 · conditional"); "· repeated evidence" / "· withdrawn" markers render where applicable (the "· withdrawn" markers appeared after the correction). Panel text exact: "Limited retained history. Usual price unavailable. No savings claim. Observations are separate from alert events and acquisition failures." Direction labels per API: initial, unchanged, decreased, unchanged, decreased, decreased — no increase in this fixture's steps (as the kit notes); no savings percentage anywhere. |
| 25 | I1 — Correct a field and keep its lineage | partial | Form shows original vs intended ("Original acquired dial: mint. Intended value: salmon.") and the consequence copy "Old prices stop applying. Your target stays; alerts wait for a matching offer." Saved with explicit actor/rationale; lineage entry "**dial: mint → salmon (corrected)**" with actor, rationale and time ("Automated walkthrough agent (not the buyer), 2026-10-31 · … The selected variation differs from this watch."); no invented actor. Rejected-stale-write path verified live: a competing writer advanced the revision (201), the stale form's submit was rejected with `role=alert` "Identity or correction changed; reload before saving. **Reload the feed before retrying.**" and **no success message** (later resolved to salmon; final lineage is append-only: mint→salmon (corrected), salmon→blue (disputed), blue→salmon (corrected)). **Missing:** the "promises no new price or refresh" element — that copy is not in `IdentityCorrection.tsx` at this revision (condensed away in the earlier overload/comparison redesigns); the closest statements on screen are "alerts wait for a matching offer" and "Corrected; fresh evidence required". See D-6. |
| 26 | I2 — Dependent evidence is withdrawn, not transferred | yes | Card caution "**Old prices withdrawn · matching offer needed**"; delivered total back to "Total unknown"; coupon `state: invalidated` with `resulting_cost: null` and `historical_resulting_cost` 45.10 retained; all price assessments now `historical`; alert assessment "**Alert withheld**" with reason "Evidence was withdrawn or corrected; intent retained."; observation rows show "invalidated · withdrawn" while **every observation keeps its original mint configuration** — no mint price relabelled salmon. |
| 27 | I3 — Tracking intent survives the correction | yes | £60 target retained — "Alert withheld · target £60 delivered" + caution "Evidence withdrawn · target retained"; API `intended_values.dial = "salmon"` (full intended set retained); correction history shows "Intended dial: salmon"; the separate Casio £40 target untouched (same configuration id, same target, its own named gate). |
| 28 | H1 — "Best" always carries its checked scope | yes | "Sources and gaps (**16 routes**)": per lane accepted status + reason + "Prerequisites: …" + "**Latest recorded attempt: not attempted; missing current evidence.**" for unrun lanes; roster intro "Accepted research roster… Every lane remains staged…"; cohort-gap cautions for Militado and Merkur; "Tracking and potential-alert verification have reserved capacity. **Capped, blocked and failed attempts leave gaps; an empty result means the declared search completed.**"; per capture outcome rows "cex: success; N leads returned. Source completeness unknown." (the "Reused capture …; no new source observation." marker is not applicable — this fixture's steps are all fresh successes). Assessment scope sentence present on every assessment block (G1). |
| 29 | H2 — Caps, reserves and gates disclosed as unset | yes | "Collection limits and coverage — Operating policy: supplied. Activation: staged." with pending gates ("live activation not authorized", "production operating envelope unproven"); usage rows in the exact pattern "requests: 8 used or reserved of 100000; tracking reserve 0." (requests/pages/details/retries/fallbacks/storage bytes/elapsed seconds + per-source rows); reserved-capacity note; "Storage accounting covers SQLite retained payload growth. Filesystem allocation, journals, logs and backups still require operating approval."; closing note exact: "Collection also requires finite measured budgets, physical storage/WAL/log/backup limits, retention/deletion/restore qualification and a named maintenance owner. **Fixture allowances do not supply these operating prerequisites.**" Nothing presented as operating capacity. |
| 30 | G3 — Missing periods and acquisition failures are visible | partial | Coverage reason exact: "Only retained captures in the same source/query scope. Intervals between samples are unobserved, with no cadence, interpolation or continuous stock claim. Synthetic dates establish no real longitudinal history."; API gaps list is explicit with `unobserved_interval`, `open_interval` (the 3-hour `stale` window: "No newer retained observation; current price and availability unknown.") and `not_returned` entries carrying the source outcome ("Not returned in this scope; disappearance and availability are unknown."); last-good age line rendered on a non-corrected candidate: "Last good evidence observed …; age 3 hours. Freshness unvalidated; current price and availability unknown." **Nuances:** on the corrected Addiesdive the panel honestly reads "No qualifying last-good evidence." (its evidence was invalidated); attempt states produced by this fixture are all `success` — cached/failed/capped attempts remain suite-proven per the kit's Partial note. |
| 31 | H3 — Age, staleness and no catch-up bursts (`stale`) | partial | Age preserved and grown (3 hours) with "Freshness unvalidated; current price and availability unknown."; collection panel "Next eligible …; **no catch-up replay**."; no catch-up burst — sends stayed at 2 and no new events fired; assessments remained withheld (stale evidence alone never alerted). **Missing:** "**Stale evidence · alerts wait for a fresh offer**" did not render: the fixture's `stale` step advances the clock without re-assessing tracking (assessed_at stayed 12:04:48Z), and both tracked targets carry non-stale named gates (`evidence_invalidated`, `source_evidence_unavailable`). See D-3. |
| 32 | J4 — Restart, recovery and ambiguous sends | partial | "Load records" shows both delivery records ("£58.10 · target crossing · sent / webhook: sent", "£56.10 · further drop · sent / webhook: sent") and the disclaimer "External send/ack crashes can leave delivery unknown. Ambiguous attempts are not retried automatically; **exactly-once delivery is not guaranteed**." **Missing:** the ambiguous-send resolution controls ("I have stopped the sending process and confirmed no send is in flight." / "These actions record your resolution and never resend the message.") did not render — this fixture run produced no ambiguous state (both sends cleanly `sent`); restart/recovery non-duplication is suite-pinned per the kit's Partial note. |
| 33 | K1 — Expandable evidence and exclusion reasons | partial | Per-claim evidence rows (issuer/extraction/retrieval/observation/validity/derived-from) ✓; "Complete retained record — Raw provenance, including withdrawn evidence. This record does not establish current buying qualification." ✓; every withholding decision names its gate in "Alert eligibility details" ✓; assessment `exclusions` (populated, with observation ids) and `gaps` queryable at `/api/discovery/assessments` ✓. **Missing:** the "Source claims: review required" block ("Missing evidence: …") — unmounted component + null fixture data (D-1). |
| 34 | K2 — Receipts and rights prerequisites stay explicit | partial | Roster "Prerequisites: …" lines per lane ✓ (capture/display/reuse authority, retention grants, etc.), unrun lanes named as unrun, gate outcomes read as deterministic/offline verification ✓. **Missing:** the capture source receipt "Technical evidence" block (route and host, page/item/detail limits, discovered vs inspected counts, "Next page present/not reported", truncation state, "Use reference …; retention …; history rights unqualified. Retrieval does not grant storage or current freshness.") — `SourceReceipt` renders only when a capture outcome carries `source_evidence`, and the walkthrough fixture populates none (it exists in the separate source-evidence fixture/workflows). See D-2. |

Task evidence-match counts: **yes 18, partial 15, no 0** (of 33).

## 3. Honesty spot-checks S1–S5

Run at the seeded state (S1–S2, per the session script) and at the end state.

### S1 — Fixture/synthetic provenance is marked, fail-closed — **PASS**

- **API:** every price claim (`current_best`, `observed_low`, `usual_price`,
  `personal_price`) across all 128 claim records served at the end state carries
  an explicit `"synthetic": true|false`; every fixture-decided amount reads
  `true` (including the current `observed_low` 49.68 and the historical
  70.10/58.10/56.10/50.10/45.10 chains). Unavailable (null-amount) claims carry
  `synthetic: false` — no unmarked amount anywhere.
- **API (history):** observations carry `evidence_kind: "synthetic"` and
  `market_history_eligible: false`; envelope `market_history_eligible_count: 0`.
- **UI:** session banner "Synthetic session · prices and buying evidence are
  test data." on feed and product pages; the per-amount warning "Synthetic
  verification data: the claimed amount is decided by fixture evidence, not a
  live market fact." renders **directly beneath** the current-best amount
  whenever that envelope claim is synthetic (seen beneath GBP 70.10 at seed and
  beneath GBP 45.10 after `coupon`) and **stays absent** where no synthetic
  amount is claimed (e.g. Casio's "Current comparison unavailable." block shows
  no marker); the coupon block with retained synthetic checkout evidence
  surfaces "Synthetic checkout evidence." exactly as the kit expects.
- **Parser guard:** `frontend/src/lib/assessments.ts:10-12` refuses claim
  payloads without an explicit marker (source-cited; mounted tests green — 92/92
  at this revision, including the marker render coverage in
  `DiscoveryHierarchy.test.ts`).
- Red flags checked: none found.

### S2 — Missing costs block totals — **PASS**

Cards and cost scenarios read "Total unknown" / "Known subtotal GBP 48;
incomplete, not a delivered total." wherever a payable component is missing
(Casio at seed; Addiesdive after correction); API scenarios carry `total: null`,
`state: unknown`, and unknown charges keep `amount: null` (rendered "unknown",
never 0). No delivered total contains an unknown component; no subtotal is
labelled a total. Red flags: none.

### S3 — Savings never render from sparse history — **PASS**

"Usual price unavailable. … No savings claim." on the History view and the
observations panel; API `savings: null` and `usual_price.state: "unavailable"`
on every assessment (current and historical) and the history envelope;
frontend parsers reject non-null savings (`assessments.ts:28`, `history.ts:16`).
No percentage-off or "you save" text anywhere; no RRP/first-capture-as-usual.
Red flags: none.

### S4 — Expired/conflicting coupons withhold — **PASS (fixture scope)**

The deployed fixture shows one coupon state: `reproduced_at_observation`
(applicability `supported`, issues empty) whose 45.10 result sits **beside** the
50.10 no-coupon base (`application.before_total: "50.10"`), plus "No verified
applicable public coupon supplied." everywhere else. No reduced total from an
advertised code alone; no summed promotions; cashback excluded from payable.
The kit's own Partial note applies: the fixture scripts no
conflicting/expired-terms case — that withholding is regression-suite proof
(`tests/test_coupon_workflow.py`), and a missing demonstration is not by itself
a defect. Red flags: none.

### S5 — Corrections invalidate dependents and retain lineage — **PASS**

After the I-cluster correction: totals withdrawn ("Total unknown"), coupon
`invalidated` with its historical 45.10 retained, all assessments historical,
alert assessment `withheld` (reason "Evidence was withdrawn or corrected; intent
retained."), targets retained (intended dial salmon; Casio target untouched),
original observations unchanged (all still mint), and lineage append-only with
actor/rationale/time on every entry (three entries after the stale-write
repro). The rejected-stale-write path produced an error and "Reload the feed
before retrying." with no success message. Red flags: none.

## 4. "Requires human eyes" list

1. **The human-comprehension gate itself** — the buyer's own session, in his own
   words, one task at a time. Nothing in this run establishes it.
2. **Remote reference-image display** in `?walkthrough=ticket12` mode, including
   the availability-gated captions "Product illustration; not a photograph" and
   "Remote reference image; exact configuration not established" — outbound
   image fetches were deliberately excluded by the no-live-requests constraint.
3. **Visual layout, aesthetics and keyboard ergonomics** at 1280 and 375 — this
   run inspected rendered DOM headlessly; no human looked at the pages.
4. **Ambiguous-send resolution dialog** — the "I have stopped the sending
   process…" confirmation flow, unreachable in one fixture run (no ambiguous
   delivery state is produced).
5. **Buyer wording for every task** (the kit's "your words" column) and the
   buyer's tick/accept boxes.

## 5. Real discrepancies (kit Expect vs observed)

These are the substantive output of this run. None of them is an app honesty
failure — in each case the app withheld or labelled more conservatively than the
kit's screen claim. They are documentation/fixture-reachability gaps in the kit.

- **D-1 (tasks C3, D1, K1):** the source-claims block — "Source claims: review
  required", "Reported selection and price scope do not establish a qualified
  binding.", "Source claims do not certify selected-SKU availability. Missing
  charges remain unknown.", "Missing evidence: …" — is rendered by
  `SourceOfferEvidence` (`frontend/src/components/discovery/SourceCoverage.tsx`)
  which is **not mounted in any product view** at `07b6127` (only its unit
  tests render it), and the walkthrough fixture's offers carry
  `source_evidence: null`. The kit cites it as on-screen evidence without a
  **Partial:** marker. The underlying behaviour (binding separation, withheld
  qualifications) is demonstrable via the Overview/Technical/API records.
- **D-2 (task K2):** the capture source receipt ("Technical evidence": route and
  host, page/item/detail limits, discovered vs inspected counts, next-page
  state, truncation, the rights line) renders via `SourceReceipt` only when a
  capture outcome carries `source_evidence`; the walkthrough fixture populates
  none (the separate source-evidence fixture/workflows do). The kit presents it
  as demonstrable in this session.
- **D-3 (task H3):** "Stale evidence · alerts wait for a fresh offer" cannot
  appear in this session — the fixture's `stale` step advances the clock without
  re-assessing tracking, and both tracked targets carry non-stale named gates.
  Either the step should re-assess (as the tracking fixture's stale handler
  does) or the Expect should be marked **Partial**.
- **D-4 (tasks E1, E4):** the Costs view renders scenario-level assumptions only;
  the base scenario's `assumptions` is empty, and component-level assumptions
  (e.g. "Synthetic regional shipping quote requires confirmation") are carried
  in the record/Technical JSON but not on screen. The
  currency/destination/dispatch context the E1 Expect calls "assumption text" is
  retained in `context` / `context_evidence`, visible in the History/Technical
  records and the API.
- **D-5 (task F3):** the price steps replace the offer's cost scenarios, so at
  F3's scripted checkpoint (after `coupon`) the cashback scenario exists only in
  retained history (offer cost-history rev 1 and the seed observation), not in
  the current Costs view; and no non-public coupon entry exists in this fixture,
  so "Conditional benefit excluded from public payable. Cashback is not checkout
  cash." is never exercised.
- **D-6 (task I1):** the "promises no new price or refresh" copy the Expect
  cites is not present at this revision (it was condensed away during the
  information-overload and comparison redesigns); the consequence line "Old
  prices stop applying. Your target stays; alerts wait for a matching offer." is
  present exactly.
- **D-7 (task J2):** the no-channel crossing ("the crossing is still recorded
  but nothing is sent", event status `channels_unset`) is not reproducible with
  the shipped step set: the steps move only the Addiesdive price (the no-channel
  Casio target never crosses), and editing a target's channels re-baselines it
  (observed: "First qualified observation recorded; waiting for a qualifying
  price change.", which also suppressed the later qualifying drop). The Expect
  leans on the recorded 2026-10-28 receipt; the kit should say so.
- **D-8 (task A2, app UX finding):** once changed away, a saved custom interval
  cannot be restored in-form — `WatchForm.tsx:506-507` derives the "(saved)"
  option from live form state, so the option disappears with the first change;
  abandoning the form restores the saved value. The Expect's claim (the saved
  value shows as its own option) holds at load.
- **D-9 (brief vs kit):** the parent brief describes "37 tasks"; the kit
  enumerates 33 (A1–K2). Counts reconciled in this record's title section.

## 6. Verdict form (agent-filled; buyer slots left empty)

Session metadata:

- Date(s): **2026-10-31** · Sittings: **1** · Fixture restarted between
  sittings? **n/a**
- Deployed instance revision (commit): deployed instance runs the
  `60577e3`-era build per the [deployment receipt](deploy-2026-10-30.md)
  (health re-probed only; no session data written there). The **session** ran
  against a fresh fixture built from **`07b6127` (origin/main)**. Fixture marker
  id: **`9b8454f0e9ff4bc4af43c04cbef3e056`**.
- Viewports used: **desktop 1280×900 and narrow 375×812** (headless Chrome,
  loopback-only network policy) + direct API reads.
- Assistance given: **n/a — agent-executed session; no buyer present.**

Per-story-cluster verdict (accept / flag). "Evidence match" is the judgement of
whether the screen matched the claims in the cluster's tasks.

| Cluster | Stories | Verdict | Evidence match (yes/partial/no) | Notes |
| --- | --- | --- | --- | --- |
| A — Monitoring preservation | US1–2 | ☑ accept ☐ flag | yes / partial | Queue identical across the whole workflow (A1); unedited-field retention exact; interval restore gap (D-8). |
| B — Discovery feed & preferences | US3–5, 7–8 | ☑ accept ☐ flag | partial / yes / partial | All states/labels/banner exact at both widths; image rendering limited by the no-outbound constraint (§1.2). |
| C — Identity & uncertainty honesty | US6, 9–13 | ☐ accept ☑ flag | yes / yes / partial / yes | Core honesty exact; C3's source-claims sentence unmounted (D-1). |
| D — Seller, condition & cohorts | US14–17 | ☐ accept ☑ flag | partial / partial | Offer rows/hero/pinned-unknown exact and cohort data complete in API; claim-labels sentence unmounted (D-1); D2's two named reasons never rendered this session. |
| E — UK delivered cost & missing costs | US18–21 | ☐ accept ☑ flag | partial / yes / yes / yes | Itemisation, VAT-once, missing-cost and FX/conditional evidence exact; E1's "assumption text" clause not rendered (D-4). |
| F — Coupons & conflict withholding | US22–25 | ☐ accept ☑ flag | yes / yes / partial | Reproduced-vs-base separation exact; F3's cashback block only in retained history at its checkpoint (D-5). |
| G — Assessments & history honesty | US26–29 | ☑ accept ☐ flag | yes / yes / partial | Three-way separation, all-directions table and gaps list exact; corrected candidate's last-good honestly null (nuance, §2 row 30). |
| H — Coverage & freshness disclosure | US30–31, 41–44 | ☐ accept ☑ flag | yes / yes / partial | Roster, caps and no-catch-up exact; H3's stale string unreachable in this session (D-3). |
| I — Corrections & lineage | US33–35 | ☐ accept ☑ flag | partial / yes / yes | Withdrawal/target/lineage behaviour exact incl. live 409 rejection; I1's "no new price or refresh" promise copy absent (D-6). |
| J — Exact tracking | US36–40 | ☐ accept ☑ flag | yes / partial / yes / partial | Crossing/suppression/further-drop exact; no-channel crossing not reproducible (D-7); ambiguous-send controls unreachable (one-fixture limit). |
| K — Source evidence | US32, 45–46 | ☐ accept ☑ flag | partial / partial | Evidence rows, retained record, gates and roster prerequisites exact; source-claims block and capture receipt not demonstrable (D-1, D-2). |
| S1–S5 — Honesty spot-checks | fail-closed contracts | ☑ pass ☐ flag | pass | All five pass; red flags none. |

Overall verdict (agent behaviour-evidence verdict only — **this is not the
human-comprehension verdict, which is deliberately unset**):

- ☐ Accept — offline human comprehension established; clusters and spot-checks
  clear.
- ☑ **Accept with follow-ups** — application behaviour accepted on evidence;
  the follow-up items below are recorded. *Human comprehension is not
  established by this agent run; see the banner at the top of this document.*
- ☐ Reject — one or more clusters or spot-checks failed comprehension or
  honesty; describe below.

Follow-up items:

| # | Item (what was unclear, missing or wrong) | Owner | Notes |
| --- | --- | --- | --- |
| 1 | Kit cites `SourceOfferEvidence` copy as screen evidence (C3/D1/K1) but the component is unmounted and the walkthrough fixture carries no source claims | kit author / parent | D-1: mount it in the product Technical/offers rows or mark the Expect **Partial** and name the API/record cross-check |
| 2 | Capture source receipt ("Technical evidence") not demonstrable in this fixture (K2) | kit author / parent | D-2: extend the walkthrough fixture with a `source_evidence` capture outcome or mark **Partial** |
| 3 | `stale` step does not re-assess tracking, so H3's "Stale evidence · alerts wait for a fresh offer" never renders | kit author / parent | D-3: re-assess on the stale step or adjust the Expect |
| 4 | Component-level cost assumptions (E1/E4) carried in records but not rendered in the Costs view | kit author / parent | D-4: render component assumptions or point the Expect at the record |
| 5 | Cashback scenario dropped from current state by the price steps; non-public coupon label unexercised (F3) | kit author / parent | D-5: retain the scenario, re-order the session, or mark **Partial** |
| 6 | I1's "promises no new price or refresh" copy no longer exists at this revision | kit author / parent | D-6: restore the sentence or amend the Expect |
| 7 | No-channel crossing (`channels_unset`) not reproducible with the shipped step set (J2) | kit author / parent | D-7: cite the recorded receipt explicitly in the Expect |
| 8 | Saved custom interval cannot be restored in-form after changing away | app follow-up | D-8: keep the saved value selectable in `WatchForm`'s interval options |
| 9 | Brief says 37 tasks; kit enumerates 33 (A1–K2) | parent | D-9: reconcile the counts |

Acknowledgement (the buyer signs this to bound the verdict):

- ☐ I understand this verdict accepts **offline behaviour and my own
  comprehension of it only**. The gates listed in section 4 of the kit — live
  offers, live delivered totals, live coupon success, history/savings
  calibration, operating limits, release/activation maturity, live manufacturer
  provenance — remain unproven and are not implied by my acceptance.

Buyer: \_\_\_\_\_\_\_\_\_\_ · Date: \_\_\_\_\_\_\_\_\_\_

*(Left empty on purpose. The buyer may countersign after running the walkthrough
himself; this agent run does not sign for him.)*

## 7. Constraints honoured

- Real production data: untouched. The deployed instance received only two
  read-only loopback GETs (`/api/health`, `/api/discovery/assessments`); all
  mutations ran against the temporary fixture database, which was destroyed
  with its guarded shutdown (final receipt: `blocked_edges=[]`).
- No live merchant/provider requests: the UI ran with a loopback-only network
  policy and the fixture's local-only image mode; merchant acquisition was not
  triggered by any task.
- The fixture servers on ports 8893–8895 were not running at session start and
  were not touched; the session's own server (port 8896) was stopped cleanly.
- The live-pilot one-shot grant marker state file was never read or modified.
- No production code changes: this document only. No push.
