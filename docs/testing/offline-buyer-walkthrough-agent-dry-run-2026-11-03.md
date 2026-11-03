# Offline buyer walkthrough: agent-executed dry run (2026-11-03)

> **This is NOT human buyer acceptance.** An agent ran all 33 tasks (A1–K2) and
> the five spot-checks (S1–S5) of the [buyer walkthrough kit](buyer-walkthrough.md)
> against a local synthetic fixture. It records what an agent could observe. It
> establishes no human comprehension, signs no cluster or overall verdict, and
> does **not** pass the buyer gate. Every "Accepted" box and the signed overall
> verdict stay **pending a human session** (§5). Historical receipts are unchanged,
> and the kit's §4 "do not conclude" list stands in full.

## 1. Setup and boundaries

- Branch from `origin/main` @ `081bef8`. Docs only; no production, test or
  dependency change. Python venv and frontend `node_modules` were built offline
  from the existing lockfiles (`uv pip install -e ".[dev]"` from cache,
  `npm ci --offline`).
- Fresh fixture on loopback port 8899: `tests.monitoring.discovery_ui_server
  --workflow`. Marker before the first task: fixture `ticket12-connected-ui-v1`,
  id `07e5b37786da49f19cb773f80ed0b10a`, `temporary_storage=true`,
  `automatic_checks=false`, `blocked_edges=[]`, 0 notifications.
- Fixture steps followed the kit's order, run through the run-bound conductor
  (`tests.monitoring.watch_workflow_ui --step …`): `baseline`, `cross`,
  `duplicate`, `drop`, `costs`, `coupon`, correction through the UI, `stale`.
  Sends read 0/1/1/2 across baseline/cross/duplicate/drop, then 3 after `coupon`
  (the third send is the further drop to GBP 50.10, which the kit does not list)
  and stayed at 3 through the correction and `stale`.
- Browser: headless Chrome via `agent-browser`, restricted to `127.0.0.1`, at
  1280×900 (375×800 for B1/B2). Remote image URLs were therefore blocked, so
  remote-reference images showed the placeholder (see B3).
- Shutdown guard: same fixture identity, `blocked_edges=[]`,
  `notifications_sent=3` (captured transport only), clock 2026-10-27T15:04:48Z.
  Port 8899 only. The consumed pilot marker was not read, created, modified or
  reset. No deployed-instance access, live provider/merchant request, live pilot
  or discovery activation.
- Automated checks, run sequentially: the 13 workflow suites the kit cites
  (`tests/test_{watch,assessment,collection,correction,cost,coupon,discovery,
  final_review,history,monitoring,qualification,source_evidence,tracking}_workflow.py`)
  190 passed; `tests/test_source_queries_routing.py` 8 passed; `npx vitest run`
  137/137; `npm run build --prefix frontend` clean (chunk-size advisory only);
  `python3 scripts/check_public_markers.py` passed. These are **suite evidence**,
  not walkthrough or comprehension evidence.

### How to read the results

- **Observed** — the screen/API did what the task's Expect line says.
- **Observed (partial)** — as above, but the kit itself marks part of the claim as
  record-only or suite-only, or a named string was not on screen. The gap is
  stated; nothing was weakened or counted as comprehension.
- Every task also has an element no agent can supply: the buyer describing what
  they understand before the expected state is explained, in their own words.
  That is **not assessed** for any task. Keyboard use and visual judgement of
  layout were not assessed either; at 375 px only a measured no-horizontal-
  overflow check was made (`scrollWidth` 375 on the feed and preferences).

## 2. Task-to-evidence map

| Task | Agent result | Evidence |
| --- | --- | --- |
| A1 | Observed | Queue UI: 2 watches (1 active, 1 paused). `/api/watches` is byte-identical before and after discovery use, including a preferences save. The list view shows only name, fallback query, sources, schedule and status, so the other fields were compared via the API. |
| A2 | Observed | Title-only edit through the form: API diff shows only `display_title` and `updated_at` changed. The form listed "Every 30m (saved)" on open. The kit's known issue (saved option vanishes after changing it) was not reproduced; the automated select did not confirm a change event, so it is unassessed. |
| B1 | Observed | Five cards in title order: Addiesdive, Casio, Merkur, Militado, San Martin. The page carries the "Synthetic session" banner; each card has a delivered-price state, "UK delivered · no coupon · cashback excluded", and Product details/Track/Wrong watch details links. All five leads are `category_discovery`. 375 px: no overflow. |
| B2 | Observed | Width 38 hard, "mint, salmon" via "Type another value…" soft, budget 150 hard. Values persisted after reload and at 375 px. Interpretation lines "Hard constraint. / Soft preference. / Unset." and "Unknown dimensions stay visible…" shown. "Not set" saved as "Unset." |
| B3 | Observed (partial) | `ticket12-local` mode: Casio "Photograph" with rights attribution; Merkur placeholder plus "PriceRecon original SVG illustration… not a product photograph". Technical image block on San Martin: "Remote reference image; exact configuration not established", configuration note, source links. Remote images were not displayed (egress blocked), so how a loaded remote reference looks was not assessed. |
| C1 | Observed | After saving preferences, Militado and Merkur cards read "Identity unresolved", "Preference fit unknown", "Total unknown". Costs show "Item lead GBP 1" beside "Total unknown". Overview lists "Unresolved configuration". Not alert-eligible. |
| C2 | Observed | Separate fields for reference, generation, movement, size, dial, strap. San Martin: configuration dial mint vs selected "Space Gray" gives binding resolution `rejected`, issue `configuration_mismatch`; the UI reads Qualification "unresolved", Comparison "rejected". Casio keeps "MTP-B145D-2A2VEF". |
| C3 | Observed (partial) | API: merchant/product/variation sit on the binding, separate from the configuration. Correction form "product kind" offers complete_watch/accessory/component. `SourceOfferEvidence` is mounted nowhere (grep) and fixture offers carry `source_evidence: null`. No accessory/component in the fixture. |
| C4 | Observed | All five leads carry one capture id (`218ca190…`) with distinct listing ids. Technical shows capture, source listing, reported source, issuer, extraction, retrieved, observation time, validity and "Derived from". |
| D1 | Observed (partial) | Per offer: seller, Condition, Availability, Qualification, Comparison; hero repeats Condition. API `authenticity` and `internal_health` are `unknown`. "Source claims do not certify…" text is not on screen (same unmounted component). |
| D2 | Observed (partial) | API assessments carry cohort (`condition`, `quantity`, `purchase_mode`, `eligibility`). Eligibility copy seen: "Freshness and buyer eligibility policy have not been supplied.", "Same offer and price…". The kit's "Offer is unavailable or lacks a fixed buy-now price" string was not reached in the session. The cohort line component is unmounted. |
| E1 | Observed | Addiesdive Costs: "GBP 70.10 — Verified at observation", Merchant payable vs Additional liabilities, eight itemised charges with state and reason, "Observed … Freshness unvalidated." |
| E2 | Observed | Militado/Merkur/Casio "Total unknown". Casio shipping `unknown`, "Known subtotal GBP 48; incomplete, not a delivered total." API: scenario `total` null, unknown charges keep amount null. |
| E3 | Observed | Merchant tax GBP 8.00 "Synthetic quoted VAT already included in item"; total 70.10 = 68 + 2.10. |
| E4 | Observed | After `costs`: San Martin rev1 unknown, rev2 shipping unknown, rev3 `conditional` GBP 70.10 with the regional-quote assumption in the API. Casio rev1 unknown, rev3 GBP 49.68 `verified_at_observation` with "Payment FX basis… 0.8 GBP per USD". All three revisions retained at `/offers/{id}/costs`. |
| F1 | Observed | Seeded: "No verified applicable public coupon supplied." and base total. After `coupon`: "Synthetic TEN opportunity: Reproduced at observation", "Synthetic checkout evidence.", literal terms, resulting cost GBP 45.10 beside a base of GBP 50.10. |
| F2 | Observed (partial) | Only the reproduced receipt state exists in the fixture. Conflict/expiry withholding is suite-proven (`test_coupon_workflow` 12 and `test_final_review_workflow` 24 passed). |
| F3 | Observed (partial) | Seeded Costs: cashback under "Benefits excluded from payable… Excluded from payable", with a separate cashback scenario "Conditional". After `coupon` it survives only in cost/observation history. The "Cashback is not checkout cash" label was not on screen. |
| G1 | Observed (partial) | "Lowest verified total among offers checked: GBP 45.10", with "Synthetic verification data…" beneath; retired revisions "Historical assessment / Current comparison unavailable… a dated record, not a current price"; "Usual price unavailable… No savings claim." API: distinct `current_best`, `observed_low`, `usual_price` unavailable, `savings` null. Casio shows `current_best` unavailable beside `observed_low` 49.68. `observed_low` is not rendered in the mounted view. |
| G2 | Observed (partial) | History table lists 6 observations (initial, unchanged, decreased, unchanged, decreased, decreased), unchanged ones retained, with the "Limited retained history… No savings claim" panel. Direction is the API field `change`, not shown in the table. No increase exists in the fixture steps. |
| G3 | Observed (partial) | After `stale` (clock 15:04:48Z): "Last good evidence observed 12:03:36 PM; age 3 hours. Freshness unvalidated…". API gaps: `not_returned` ×5, `unobserved_interval`, `open_interval`. Every attempt state was `success`; no failed/capped/cached state appeared. |
| H1 | Observed | "Sources and gaps (16 routes)", all 16 "Latest recorded attempt: not attempted; missing current evidence", per-lane prerequisites, "Capped, blocked and failed attempts leave gaps…". Per-capture outcomes listed; no reused capture. Assessment scope text on every claim. Re-read after the correction: unchanged. |
| H2 | Observed (partial) | Usage rows, activation "staged", pending gates, and the closing note "Fixture allowances do not supply these operating prerequisites." See defect D-1: every reserve is 0 under a sentence saying capacity is reserved. |
| H3 | Observed (partial) | After `stale`: age grown, "Freshness unvalidated", tracking `withheld`, sends and events flat at 3. "Stale evidence · alerts wait" label never renders (kit-acknowledged). See D-2 on "Next eligible". |
| I1 | Observed | Via UI: dial mint→salmon ("Type another value…"), named actor, preset reason. Live preview, button "Save correction — old prices will be withdrawn", post-save summary, history entry "dial: mint → salmon (corrected)" with actor, rationale, time. Wording differs from the kit (D-3). |
| I2 | Observed | Card "Details corrected (dial mint → salmon) · old prices kept on record…"; total `unknown`; coupon `invalidated` (historical 45.10 retained); all 8 Addiesdive assessments `historical`; tracking `withheld` (`evidence_invalidated`); 6 observations `invalidated` but still `dial: mint`. |
| I3 | Observed | £60 target retained ("Prior evidence no longer applies — kept on record… · target retained"); `intended_values.dial` = salmon; £40 Casio target untouched; events and sends stayed at 3. "Intended dial" shown under "Show full intended configuration". |
| J1 | Observed | Addiesdive £60 + webhook and Casio £40 (no channels) saved: "Delivered target saved. Collection remains staged." Militado: "Exact identity must be resolved before starting exact tracking." with Save disabled; direct API POST returned 422. |
| J2 | Observed (partial) | `baseline` GBP 70.10 "Above target", 0 sends, 0 events; `cross` GBP 58.10 "Eligible at target — Verified delivered total crossed your target.", 1 event, 1 send. No-channel Casio copy shown. A no-channel crossing cannot be produced with the shipped steps (kit-acknowledged). |
| J3 | Observed | `duplicate` GBP 58.10: "Same offer and price, or no further drop; repeat alert suppressed.", sends 1. `drop` GBP 56.10: "A further qualifying delivered-price drop.", sends 2. Delivery records match. |
| J4 | Observed (partial) | "Load records" and the "exactly-once delivery is not guaranteed" copy shown. All records were `sent`, so the ambiguous-resolution controls never rendered (confirmation string seen only in source). Restart/recovery was not exercised (suite: `test_tracking_workflow` 13 passed). |
| K1 | Observed (partial) | Technical lists issuer, extraction, retrieval, validity, derived lineage per claim. Alert-eligibility details name each gate. API exclusions carry reason codes; gaps are under `coverage.gaps` (D-3). "Source claims: review required" block is unmounted. |
| K2 | Observed (partial) | Roster "Prerequisites" shown per lane; gate outcomes read as offline verification. The capture source receipt "Technical evidence" never renders (`source_evidence` null in this fixture). |
| S1 | Observed | All 32 assessments: every claim has an explicit `synthetic` marker and every amount reads `true`. History observations `evidence_kind: synthetic`, `market_history_eligible: false`, eligible count 0. Banner on feed/product pages; per-amount warning under the current-best amount; coupon "Synthetic checkout evidence." |
| S2 | Observed | Cards and Costs read "Total unknown" / "Known subtotal… incomplete, not a delivered total."; API `total` null with state `unknown`, no unknown charge with an amount. |
| S3 | Observed | "Usual price unavailable… No savings claim." in History and Observations; `usual_price.state` `unavailable` and `savings` null on assessment, history and feed envelopes; no `%` / "you save" / discount text across all rendered feed and product views (text search). |
| S4 | Observed (partial) | Reproduced receipt GBP 45.10 sits beside, not replacing, base GBP 50.10. Expired/conflicting terms are suite-proven only (see F2). |
| S5 | Observed | After the UI correction: totals "Total unknown", coupon invalidated, assessments historical, alert `withheld`, target retained, original observations still mint, lineage entry with actor/rationale/time. Consistent with [s5-retry-2026-11-02](s5-retry-2026-11-02.md) §4 on the current build, including the [F5 residual fixes](s5-f5-clarity-residuals-2026-11-02.md); this run did a single correction, not the earlier two-correction chain. |

## 3. Per-cluster agent observations

These are agent observations, **not** the buyer's cluster verdicts.

- **A (US1–2).** The saved-search queue and its API record were unchanged by discovery use and by a title-only edit. The queue list is thin: it shows name, fallback query, source count, schedule and state, not rules or notification settings.
- **B (US3–5, 7–8).** The five-card feed is deterministic and labelled as synthetic test data. Preference interpretation is explicit and persists. Image provenance is partly assessable here: captions and attribution are present, but remote reference images could not display. The buyer's earlier "only 1 photo" complaint is reproduced and explained by blocked egress (see [buyer-session-2026-11-02](buyer-session-2026-11-02.md) §3b).
- **C (US6, 9–13).** Unknowns stay unknown. An item lead of GBP 1 never stands in for a delivered total. San Martin's dial mismatch is rejected rather than merged. All five leads share one capture lineage. Binding-scope detail lives in the Technical JSON/API, not on a friendly screen.
- **D (US14–17).** Seller, condition and availability are shown; authenticity and health stay `unknown`. Used/auction cohorts are not in this fixture (new/buy-now only), so cohort separation here rests on the API field and the suites.
- **E (US18–21).** Itemised costs, unknown-not-zero, once-counted VAT, and the `costs` step's conditional and FX-converted states all matched. The cost-history API retains the earlier unknown revisions.
- **F (US22–25).** The no-coupon path works and a reproduced receipt shows beside the base. Conflict/expiry and the cashback non-payable label are suite- or history-only in this fixture.
- **G (US26–29).** Separation of current best, observed low and usual price holds in the API; the mounted History shows the current-best summary. No savings text anywhere. The fixture produces only success attempts, so failure/cap states are suite-only.
- **H (US30–31, 41–44).** Coverage and fixture-allowance honesty are present. Two presentation issues are reported in §4 (D-1, D-2).
- **I (US33–35).** The correction flow, post-save summary, invalidation and lineage all behaved as the S5 receipts describe on the current build; wording has moved on from the kit text (D-3).
- **J (US36–40).** One alert per verified crossing, suppressed repeat, alert on a further drop, and captured sends 0/1/1/2 all matched. Ambiguous-send reconciliation and restart cannot be shown in one fixture run.
- **K (US32, 45–46).** Per-claim lineage and roster prerequisites are on screen; the source-evidence and source-receipt blocks are unmounted or empty in this fixture.

## 4. Defects and drift found (reported, not fixed)

Nothing here blocks the walkthrough, and no production change was made.

- **D-1 — "reserved capacity" claim with zero reserve.** Repro: start the fixture as above, open `/discover?walkthrough=ticket12&view=sources`. The panel says "Tracking and potential-alert verification have reserved capacity." (static text, `frontend/src/components/discovery/CollectionCoverage.tsx`), while `/api/discovery/collection` returns `tracking_reserve: 0` for every resource and every provider. The static sentence overstates what the data shows.
- **D-2 — "Next eligible" equals the attempt's own time.** Repro: same view, any step. Each attempt reads "Next eligible <its own attempted time>; no catch-up replay." After `stale` (clock 15:04:48Z) the line still shows 12:04:48 PM, which reads as already elapsed. Possibly a fixture artefact (`next_eligible_at` equals `attempted_at` in `/api/discovery/collection`); still confusing to a reader.
- **D-3 — Kit text drift against current UI/API.** The kit predates the F1–F10 and F5-residual copy. Examples: I1 consequence copy ("Old prices stop applying…"), I2 card caution ("Old prices withdrawn · matching offer needed"), I3 label ("Evidence withdrawn · target retained"), G2 per-observation `direction` (field is `change`), K1 `gaps` (under `coverage.gaps`), C2 San Martin "unresolved" (comparison reads `rejected`). A human session reading the kit verbatim would see mismatches that are not product defects. The kit was not edited here.
- **D-4 — Technical tab size.** The Addiesdive Technical view renders about 300 KB of raw JSON text after the corrections and steps. Observation only; legibility and load cost for a buyer were not assessed.
- **D-5 — Minor formatting.** Casio Costs prints "shipping:unknown" as one unspaced token; the Watch queue list omits rules and notification settings (A1 had to use the API).
- Environment note: the T3 worktree started with an unrelated stale WIP commit (`d238d71`) that conflicted with `origin/main`; I skipped it and reset the worktree branch to `origin/main` as instructed. The commit is still in the reflog.

## 5. Pending human acceptance (blocker)

The remaining blocker is only the human step: the buyer must run the kit against a fresh fixture, speak first on each task, and sign.

- All 33 "☐ Accepted" boxes and S1–S5 "☐ Pass · Flag": **unticked**.
- Per-cluster verdicts A–K and S1–S5: **pending**.
- Overall verdict (Accept / Accept with follow-ups / Reject): **pending a human session — not signed**.
- Acknowledgement and signature (Buyer · Date): **blank**.
- Not assessable by an agent: buyer's own words and comprehension; keyboard and assistive use; visual judgement of layout at 375 px; display of remote reference images; real-photo appearance.
- The §4 "do not conclude" gates (live offers, live totals, live coupon success, history/savings calibration, operating limits, release/activation maturity, live manufacturer provenance, cohort completeness) remain unproven. The buyer's earlier S5 acceptance
  ([s5-retry-2026-11-02](s5-retry-2026-11-02.md) §6) is their own decision and is neither extended nor weakened by this record.

Recorded by: agent session, 2026-11-03 · revision `origin/main` @ `081bef8`.
