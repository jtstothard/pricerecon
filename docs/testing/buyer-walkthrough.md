# Buyer walkthrough kit: task-by-task acceptance session

A guided checklist for the buyer (Jay) to walk the deployed application and clear the
human-comprehension acceptance gate. It complements, and does not replace, the
[existing buyer guide](watch-workflow-buyer-guide.md), which holds the launch recipe,
the fixture-step commands and the session history. This kit is the session document:
what to do, what you should see, what counts as a defect, and how to record the verdict.

**What this session establishes:** that a human can look at the deployed offline
application and correctly understand what it knows, what it does not know, and what it
is withholding. **What it does not establish:** anything live — offers, delivered
totals, coupons, history, savings or operating limits. Section 4 lists every gate that
stays unproven no matter how this session goes.

Ground rules (from the recorded sessions in the buyer guide):

- One task at a time. Let the buyer describe what they understand **before** explaining
  the expected state. Record the buyer's own words; do not fill the notes with agent
  observations. No narrated data dumps.
- Every "Expect" line below was cross-checked against the source tree at this revision
  (this kit's branch, which mounts the per-amount synthetic evidence markers in the
  discovery UI on top of main — see S1). UI claims cite `frontend/…:line`; API claims
  cite `src/…`. Where the screen shows less than the tested component library proves,
  the line says **Partial:** and names where to confirm instead.
- If the screen disagrees with an Expect line, record the disagreement as a
  discrepancy. Do not silently prefer either side; that discrepancy is session output.

## 1. Session setup

### Have running

- **The deployed instance**, built from this revision, running the synthetic
  walkthrough fixture (five invented watch cases, temporary SQLite, paused scheduler,
  captured notification transport). The launch recipe and the fixture-step commands
  live in the buyer guide's "Launch safely" section; use them unchanged. Start a fresh
  fixture for this session — earlier running sessions and retained screenshots predate
  later revisions and prove nothing about what you are about to see.
- Before any task, confirm the fixture marker endpoint (see the buyer guide) reports
  the current fixture identity, `temporary_storage=true`, `automatic_checks=false`,
  an empty `blocked_edges` list and the expected starting notification count. If the
  marker differs, stop.
- A second terminal for the session conductor (parent or you) to run the fixture
  steps named in the session script below. Steps are test-only endpoints on the
  fixture; they change only the temporary database and captured transports.

### Have open

- The deployed instance in a clean browser window at desktop width (1280) and, for
  tasks that say so, a narrow window (375).
- Two plain browser tabs for API spot-checks, pointed at the same host as the UI:
  `/api/discovery/assessments` and `/api/discovery/watches`. (The Event stream page is
  a placeholder at this revision — `frontend/src/pages/Events.tsx:10` — so alert
  events are inspected at `/api/events` instead.)
- This document, for ticking and note-taking.

### Time

Roughly **two hours** for all eleven clusters plus the honesty spot-checks and the
verdict form. Clusters A–G and the spot-checks are the comprehension core (~75
minutes); H–K are disclosure checks (~30 minutes); the verdict form (~15 minutes).
Running in two sittings is fine — restart with a fresh fixture if you do, and say so
in the session metadata.

### Recording convention

Every task ends with this line:

> ☐ Accepted · Evidence match (yes / partial / no) + your words: \_\_\_\_\_\_\_\_\_\_

- Tick the box only when the task was actually performed and observed.
- "Evidence match" answers one question: **did the evidence on screen match the claim
  the task made?** "Partial" is a real answer; write what was missing.
- Keep the buyer's actual words in the note. Difficulties and requested changes belong
  there too.
- Record the viewport used and any assistance given per task.

### Session script (fixture steps have a proven order)

The document is organised by story cluster, but the fixture steps must run in the
order the recorded receipts used, or the expected numbers will not match. Conductor:
run the tasks in this order and advance the fixture only where the table says.

| # | Tasks | Fixture state / conductor step |
| --- | --- | --- |
| 1 | A1–A2 | seeded fixture |
| 2 | B1–B3 | seeded fixture |
| 3 | C1–C4 | seeded fixture |
| 4 | D1–D2 | seeded fixture |
| 5 | E1–E3 | seeded fixture |
| 6 | F1 first half (no-coupon path) | seeded fixture |
| 7 | J1 | buyer saves targets |
| 8 | J2 | step `baseline`, reload, step `cross` |
| 9 | J3 | step `duplicate`, reload, step `drop` |
| 10 | E4 | step `costs` |
| 11 | F1 second half, F2, F3 | step `coupon` |
| 12 | G1–G2 | after `coupon` |
| 13 | I1–I3 | buyer performs the correction |
| 14 | H1–H2 | after `coupon` |
| 15 | G3, H3 | step `stale` |
| 16 | J4, K1–K2 | end state |
| 17 | S1–S5 spot-checks, verdict form | end state (S1–S2 also at step 5) |

Step commands: see the buyer guide ("Replace only the final step name with `cross`,
`duplicate`, `drop`, `costs`, `coupon` or `stale`"). Reload the buyer page after every
step. `Ctrl-C` on the fixture ends the session state; do not restart it mid-session.

## 2. Task-by-task walkthrough

Story references are the numbered user stories in the
[spec](../specs/watch-category-discovery.md) (US1–US46).

### Cluster A — Monitoring preservation (US1–2)

#### A1 — Saved searches survive discovery · seeded fixture (US1, US2)

- **Do:** Open the Watch queue first. Note for the enabled watch: display title,
  fallback query, per-source queries, matching rules/groups/exclusions, price ceiling,
  enabled state, interval/timezone/window and notification destinations. Note the
  paused watch's paused state. Now use discovery (preferences, later a target), then
  return to the queue.
- **Expect:** the queue is exactly what you noted: the same watches, same enabled/
  paused states (the fixture seeds one of each), same rules, targets and notification
  settings. Discovery neither created, edited nor deleted a saved search
  (`tests/monitoring/watch_workflow.py:207-212` asserts the queue is unchanged across
  the whole workflow).
- **Defect if:** any field differs; a watch appears, disappears or unpauses.
- ☐ Accepted · Evidence match (yes / partial / no) + your words: \_\_\_\_\_\_\_\_\_\_

#### A2 — Editing one field preserves the rest (US2)

- **Do:** Edit only the display title of the enabled watch; save; reload. Also try
  changing and restoring a custom interval if the form offers a saved value.
- **Expect:** every unedited field is retained — notification destinations, timezone/
  window, exclusions, raw per-source queries, filters, grouping; a saved custom
  interval shows as its own option rather than resetting to a preset
  ([isolated-monitoring](isolated-monitoring.md), "UI edit preservation follow-up";
  pinned by the 15 isolated monitoring workflow tests).
- **Defect if:** any unedited field silently resets.
- **Note (tested, not demonstrable here):** the query-term title gate applies only to
  watches carrying per-source raw-query overrides; plain watches keep legacy matching
  (gate scoping decision, 2026-10-29, in the same document). The fixture runs no
  collection, so this contract is test evidence only
  (`tests/test_source_queries_routing.py`).
- ☐ Accepted · Evidence match (yes / partial / no) + your words: \_\_\_\_\_\_\_\_\_\_

### Cluster B — Discovery feed & preferences (US3, 4, 5, 7, 8)

#### B1 — Independent, simultaneous illustrated feed · seeded fixture (US3, US7)

- **Do:** Open **Discover watches** (the comparison feed). Try 1280px and 375px
  widths. Do not open any product yet.
- **Expect:** five illustrated candidates — Militado ML05/ML05B, Addiesdive AD2066
  mint, San Martin SN0144, Merkur Lightning salmon, Casio MTP-B145D-2A2VEF — that are
  category discovery leads, not your saved searches (origin `category_discovery`,
  `tests/monitoring/watch_workflow.py:213`). Each card shows image, title, a
  delivered-price state ("GBP …" or "Total unknown"), the cost state and "freshness
  unvalidated", "UK delivered · no coupon · cashback excluded", supported specs
  (strap · size · movement), any identity/preference caution, and Product-details /
  Track links (`frontend/src/pages/Discovery.tsx:247-315`). A session banner reads
  "Synthetic session · prices and buying evidence are test data."
  (`frontend/src/pages/Discovery.tsx:691-695`).
- **Defect if:** a candidate is missing without an explanation; a saved search appears
  as discovery; a price appears without its state and the no-coupon/cashback-excluded
  label.
- ☐ Accepted · Evidence match (yes / partial / no) + your words: \_\_\_\_\_\_\_\_\_\_

#### B2 — Preferences and their exposed interpretation (US4, US5)

- **Do:** Open **Preferences**. Set maximum case width 38 mm (hard constraint), dial
  colours "mint, salmon" (soft preference), delivered budget 150 (hard). Also try one
  **Other / custom** value and a blank ("Not set") value. Save, reload the page, and
  re-check at 375px width.
- **Expect:** values persist after reload; each rule is explained in words with its
  strength ("Hard constraint." / "Soft preference." / "Unset.")
  (`frontend/src/pages/Discovery.tsx:143-149`); the panel states "Unknown dimensions
  stay visible for review. They do not satisfy hard constraints or soft preferences."
  (`frontend/src/pages/Discovery.tsx:150-153`); presets never replace an arbitrary
  value (`frontend/src/components/discovery/ChoiceValue.tsx:2-3`).
- **Defect if:** values lost on reload; the interpretation not shown; a custom value
  rejected or overwritten by a preset.
- ☐ Accepted · Evidence match (yes / partial / no) + your words: \_\_\_\_\_\_\_\_\_\_

#### B3 — Image provenance is labelled (US8)

- **Do:** Open two product pages (one with a real image — Casio; one without — Merkur)
  and read the image caption and the Technical image block.
- **Expect:** photographs, illustrations and references are distinguished: "Photograph"
  / "Product illustration; not a photograph" / "Remote reference image; exact
  configuration not established" with its configuration note and original-source links
  (`frontend/src/components/discovery/DiscoveryImage.tsx:41-62`); a missing image shows
  "Product image unavailable. Generic placeholder; does not depict this watch."
  (`frontend/src/components/discovery/DiscoveryImage.tsx:32`) and Merkur keeps its
  explicit missing image — no salmon substitute (image rights record:
  `tests/fixtures/watch-images/README.md`).
- **Defect if:** a reference image presented as the exact watch; an unattributed
  image; a placeholder presented as a depiction.
- ☐ Accepted · Evidence match (yes / partial / no) + your words: \_\_\_\_\_\_\_\_\_\_

### Cluster C — Identity & uncertainty honesty (US6, 9, 10, 11, 12, 13)

#### C1 — Unknown dimensions are labelled, never silently satisfied · seeded fixture (US6)

- **Do:** With your saved preferences, look at the Militado and Merkur cards, then
  their product pages (Overview).
- **Expect:** "Identity unresolved" caution on the card; "Preference fit unknown" —
  unknown fit is shown as unknown, not as satisfying your rules
  (`frontend/src/pages/Discovery.tsx:251-260`); configurations listed as "Unresolved
  configuration" (`frontend/src/pages/Discovery.tsx:337-339`); Militado/Merkur totals
  read "Total unknown" and are not alert-eligible
  (`tests/monitoring/watch_workflow.py:214-217`). An advertised item price is shown
  as an "Item lead", never as a delivered total
  (`frontend/src/pages/Discovery.tsx:390-404`) — a £1 item lead does not satisfy a
  £150 delivered budget.
- **Defect if:** an unknown dimension shown as satisfied; a preference-fit claim
  without evidence.
- ☐ Accepted · Evidence match (yes / partial / no) + your words: \_\_\_\_\_\_\_\_\_\_

#### C2 — Exact distinctions and conflicting evidence stay visible · seeded fixture (US9, US12)

- **Do:** Open San Martin and Casio product pages → Overview. Compare the
  configuration rows with the offer/source-claim rows.
- **Expect:** reference, generation, movement, size, dial and strap appear as separate
  fields, not merged titles ("Evidenced configuration" / "Unresolved configuration"
  sections, `frontend/src/pages/Discovery.tsx:334-348`). San Martin's mint
  configuration versus the "Space Gray" selected dial leaves the merchant selection
  unresolved — the binding is not supported
  (`tests/monitoring/watch_workflow.py:128-131,218`). Casio's exact reference suffix
  is retained. Unresolved and conflicting states render as labels ("unresolved",
  "conflicting"), never as certainty.
- **Defect if:** similar names merged into one candidate; a conflicting claim hidden;
  a parent-listing's cheapest option assigned to the watch (pinned by
  `tests/test_qualification_workflow.py:41`).
- ☐ Accepted · Evidence match (yes / partial / no) + your words: \_\_\_\_\_\_\_\_\_\_

#### C3 — Variation binding and accessory/component distinction (US10, US11)

- **Do:** On a product page, expand the offer rows and the source-claims block in
  Technical (via Source coverage). In the correction form, look at the "Identity
  field" choices.
- **Expect:** selected merchant variations are bound separately from product identity
  and price scope — "Reported selection and price scope do not establish a qualified
  binding" (`frontend/src/components/discovery/SourceCoverage.tsx:55-113`); the
  correction form offers `product_kind` = complete watch / accessory / component
  (`frontend/src/lib/corrections.ts:2`), and accessory/component listings can never
  surface as complete-watch bargains.
- **Defect if:** a variation price attributed to the parent identity; a strap, part or
  accessory shown as a complete watch.
- **Note (tested, not demonstrable here):** the walkthrough fixture contains complete
  watches only; the accessory/component trap is pinned in the qualification workflows
  (`tests/monitoring/qualification_workflows.py:243`) and the multi-offer traps in
  `tests/test_qualification_workflow.py:37-45`.
- ☐ Accepted · Evidence match (yes / partial / no) + your words: \_\_\_\_\_\_\_\_\_\_

#### C4 — Discovery origins and merchant evidence stay separate (US13)

- **Do:** Product page → Technical. Read "Capture lineage" and the per-claim evidence
  rows. Do the same on a second candidate discovered from the same query.
- **Expect:** capture id, source listing id and reported source are retained per lead
  (`frontend/src/pages/Discovery.tsx:515-521`); each claim shows issuer, extraction
  route, retrieval time, source observation time, validity context and "Derived from"
  lineage (`frontend/src/pages/Discovery.tsx:522-534`). Two leads copied from one
  capture read as one acquisition lineage — copied claims never count as independent
  confirmation (pinned by `tests/test_history_workflow.py:44-52`).
- **Defect if:** lineage missing; repeated or derived claims presented as
  confirmation.
- ☐ Accepted · Evidence match (yes / partial / no) + your words: \_\_\_\_\_\_\_\_\_\_

### Cluster D — Seller, condition & cohorts (US14–17)

#### D1 — Offers describe what you can actually buy · seeded fixture (US14, US17)

- **Do:** Product page → Overview → Offers; compare with the hero's Condition line and
  the source-claims block.
- **Expect:** per offer: seller (or "Seller unknown"), Condition (or "Unknown"),
  Availability, Qualification state and Comparison state
  (`frontend/src/pages/Discovery.tsx:356-366`); the hero repeats Condition
  (`frontend/src/pages/Discovery.tsx:621`). Source claims are labelled as claims —
  "Source claims do not certify selected-SKU availability. Missing charges remain
  unknown." (`frontend/src/components/discovery/SourceCoverage.tsx:55-113`).
  Authenticity and internal health are never implied: the model pins both to
  "unknown" (`src/pricerecon/models/qualification.py:286-287`).
- **Defect if:** a price with no condition/mode/seller context; photo-led assurance
  beyond visible condition.
- ☐ Accepted · Evidence match (yes / partial / no) + your words: \_\_\_\_\_\_\_\_\_\_

#### D2 — Used offers and auctions sit in separate cohorts (US15, US16)

- **Do:** Read a tracked watch's "Alert eligibility details", then check the
  assessment record at `/api/discovery/assessments` (or the Technical record).
- **Expect:** cohort separation is enforced at eligibility: "Offer is unavailable or
  lacks a fixed buy-now price." and "Quantity, condition, destination or payment
  differs from the supplied policy." are named withholding reasons
  (`frontend/src/components/ExactTracking.tsx:39-41`); every assessment carries its
  cohort (condition, quantity) in the API (`src/pricerecon/models/assessments.py`).
  A current bid is never presented as a guaranteed purchase price.
- **Partial:** the mounted History view shows the assessment summary; the cohort line
  is rendered by the Comparable-prices detail component
  (`frontend/src/components/discovery/PriceAssessments.tsx:22`) — confirm the cohort
  via the API or the Technical record. Cohort separation itself is pinned by
  `tests/test_assessment_workflow.py:59`.
- **Defect if:** a used or auction price inside a new/buy-now comparison.
- ☐ Accepted · Evidence match (yes / partial / no) + your words: \_\_\_\_\_\_\_\_\_\_

### Cluster E — UK delivered cost & missing-cost honesty (US18–21)

#### E1 — Delivered cost is itemised · seeded fixture (US18)

- **Do:** Addiesdive product page → Costs. Expand the cost scenario.
- **Expect:** "Public total, no coupon: GBP 70.10 — Verified at observation"; the
  scenario separates "Merchant payable" from "Additional liabilities" subtotals and
  itemises each charge (kind, amount, state, reason); "Observed … Freshness
  unvalidated."; assumption text names currency/destination/dispatch context
  (`frontend/src/pages/Discovery.tsx:183-235`). The recorded fixture total is item
  £68 plus £2.10 shipping (buyer guide, task 2).
- **Defect if:** a bare total with no component breakdown.
- ☐ Accepted · Evidence match (yes / partial / no) + your words: \_\_\_\_\_\_\_\_\_\_

#### E2 — Missing costs block totals · seeded fixture (US19)

- **Do:** Look at the Militado/Merkur cards and the Casio Costs view (Casio's shipping
  is unknown at this state).
- **Expect:** "Total unknown" wherever a payable component is missing — on cards
  (`frontend/src/pages/Discovery.tsx:281-283`) and in cost scenarios
  (`frontend/src/pages/Discovery.tsx:198-200`); Casio shows its missing shipping as an
  `unknown` charge and "Known subtotal GBP 48; incomplete, not a delivered total."
  (`frontend/src/pages/Discovery.tsx:208-210`, fixture assertion
  `tests/monitoring/watch_workflow.py:220`). Unknown is never rendered as zero and
  never folded into a total.
- **Defect if:** a delivered total computed with an unknown component; a subtotal
  presented as a total.
- ☐ Accepted · Evidence match (yes / partial / no) + your words: \_\_\_\_\_\_\_\_\_\_

#### E3 — Included VAT is counted once · seeded fixture (US20)

- **Do:** Read the Addiesdive charge rows.
- **Expect:** quoted VAT is shown as already included in the item amount and is not
  added again — the fixture's VAT charge reason reads "Synthetic quoted VAT already
  included in item" (`tests/monitoring/cost_workflows.py:97`); the £70.10 total is not
  inflated. Regression anchor:
  `tests/test_cost_workflow.py::exact_public_cost_counts_included_vat_once_and_keeps_acceptance_gates_separate`.
- **Defect if:** the total rises by a double-counted VAT component.
- ☐ Accepted · Evidence match (yes / partial / no) + your words: \_\_\_\_\_\_\_\_\_\_

#### E4 — Currency, destination, dispatch and payment assumptions are explicit · after `costs` (US21)

- **Do:** Conductor runs the `costs` step. Reload San Martin and Casio (Costs, then
  History / offer cost history).
- **Expect:** San Martin moves through its states — selected-dial trap, then missing
  shipping with unknown total, then a **Conditional** regional shipping quote carrying
  the assumption "Synthetic regional shipping quote requires confirmation"
  (`tests/monitoring/watch_workflow.py:140-180`). Casio's USD shipping without payment
  FX stays unknown; with the evidenced synthetic 0.8 GBP/USD payment-FX quote the
  total becomes GBP 49.68 "Verified at observation"
  (`tests/monitoring/watch_workflow.py:179`). Conditional is labelled "Conditional",
  never "Verified"; earlier unknown states are retained in the offer's cost history
  and the observations table rather than overwritten (check
  `/api/discovery/offers/{id}/costs` and History if a view shows only the latest
  scenario).
- **Defect if:** GBP display treated as UK-delivery proof; a foreign total presented
  as delivered without an evidenced payment-FX path.
- ☐ Accepted · Evidence match (yes / partial / no) + your words: \_\_\_\_\_\_\_\_\_\_

### Cluster F — Coupons & conflict withholding (US22–25)

#### F1 — An advertised code is not a reduction; the no-coupon path works · seeded fixture → `coupon` (US22, US24)

- **Do (first half, seeded fixture):** Addiesdive Costs shows "No verified applicable
  public coupon supplied." (`frontend/src/pages/Discovery.tsx:413`) and its base total.
  Confirm the core workflow — compare, track — proceeds with no coupon at all. Then
  conductor runs the `coupon` step; reload.
- **Do (second half):** Expand the coupon block under the Addiesdive offer.
- **Expect (after `coupon`):** the coupon appears with its own state (for the
  reproduced receipt, "reproduced at observation"), applicability, literal terms and
  an issues list (`frontend/src/pages/Discovery.tsx:414-442`). The reproduced public
  receipt is GBP 45.10 shown as the coupon's **resulting cost**, while the public
  no-coupon total stays at its own base (GBP 50.10 at that moment in the recorded
  run; fixture assertions `tests/monitoring/watch_workflow.py:310-319`, recorded
  session in the buyer guide, task 4). The scoped comparison can therefore show
  GBP 45.10 while the default no-coupon target uses the base.
- **Defect if:** an advertised code alone lowers a payable; the coupon total replaces
  the base total; the no-coupon path is blocked.
- ☐ Accepted · Evidence match (yes / partial / no) + your words: \_\_\_\_\_\_\_\_\_\_

#### F2 — Eligibility, minimum spend, expiry and stack conflicts withhold (US23)

- **Do:** Read each coupon's applicability and issues text and its history at
  `/api/discovery/offers/{id}/coupons`.
- **Expect:** eligibility, minimum spend, expiry and compatibility are separate
  recorded fields with honest "unknown" where unevidenced
  (`src/pricerecon/models/coupons.py:19-40`). Expired or mutually contradictory terms
  produce **no** reduced payable: the coupon stays unverified/withheld with issue
  text, and the base total is untouched. Incompatible promotions are never summed.
- **Partial — read before judging:** the walkthrough fixture's `coupon` step
  demonstrates the reproduced receipt and the no-coupon base; it has no scripted
  conflicting-terms case. Conflict/expiry withholding is proven in the regression
  suite (final review P1 repair: contradictory expired terms withhold GBP 45.10 in
  both report orders — [watch-final-review](watch-final-review.md)). Record which coupon
  states the deployed fixture actually shows; a missing demonstration is not by
  itself a defect, but a reduced payable from expired/conflicting terms is.
- **Defect if:** any reduced total traced to expired, ineligible or conflicting terms.
- ☐ Accepted · Evidence match (yes / partial / no) + your words: \_\_\_\_\_\_\_\_\_\_

#### F3 — Public, personal, payment and cashback scenarios are separated · seeded fixture → `coupon` (US25)

- **Do:** Expand the cashback scenario and any non-public coupon entry.
- **Expect:** cashback £10 is shown under "Benefits excluded from payable" with its
  conditional state and reason ("Excluded from payable")
  (`frontend/src/pages/Discovery.tsx:224-230`;
  `tests/monitoring/watch_workflow.py:114-127`); non-public categories are labelled
  "Conditional benefit excluded from public payable. Cashback is not checkout cash."
  (`frontend/src/pages/Discovery.tsx:424-429`); personal/payment benefits never enter
  the public payable (pinned by
  `tests/test_assessment_workflow.py:51`).
- **Defect if:** cashback or a conditional benefit inside a payable total.
- ☐ Accepted · Evidence match (yes / partial / no) + your words: \_\_\_\_\_\_\_\_\_\_

### Cluster G — Price assessments & history honesty (US26–29)

#### G1 — Usual price, current best and dated observed low are separate claims · after `coupon` (US26)

- **Do:** Product page → History ("Comparable prices"). Read the assessment block,
  then check `/api/discovery/assessments`.
- **Expect:** the scoped claim is labelled and scoped — "Lowest verified total among
  offers checked: GBP 45.10" (after the coupon step) with its reason, and — because
  that fixture amount is synthetic — the mounted warning "Synthetic verification
  data: the claimed amount is decided by fixture evidence, not a live market fact."
  directly beneath it (see S1); retired
  revisions read "Historical assessment" / "Current comparison unavailable"; the view
  states "**Usual price unavailable.** … No savings claim."
  (`frontend/src/pages/Discovery.tsx:452-483`). Retained dates are shown with "This
  does not establish current availability."
- **Partial:** "Dated observed low" is a separate claim on the API envelope
  (`observed_low`) and is rendered by the tested Comparable-prices detail component
  (`frontend/src/components/discovery/PriceAssessments.tsx:28`); the mounted History
  view at this revision shows the summary above. Confirm the three-way separation via
  `/api/discovery/assessments` (distinct `current_best`, `observed_low`, and
  `usual_price.state: "unavailable"` with `savings: null`) or the Technical record
  JSON (`frontend/src/pages/Discovery.tsx:542`).
- **Defect if:** a usual price presented as known; an RRP or first capture sold as an
  ordinary price; any savings percentage.
- ☐ Accepted · Evidence match (yes / partial / no) + your words: \_\_\_\_\_\_\_\_\_\_

#### G2 — Sparse history shows all directions and never a savings percentage · after `coupon` (US27, US28)

- **Do:** History → "Load retained observations". Read the table top to bottom.
- **Expect:** every retained observation is a row regardless of direction — after the
  session script the table holds the seed capture plus each step capture (the coupon
  step adds a further row), and unchanged observations are retained as rows too, not
  filtered down to drops (`frontend/src/components/discovery/ObservationHistory.tsx:50-83`).
  Each row shows its delivered total or "Total unknown"; "repeated evidence" and
  "· withdrawn" markers appear where applicable. The panel states
  "Limited retained history. Usual price unavailable. No savings claim. Observations
  are separate from alert events and acquisition failures."
  (`frontend/src/components/discovery/ObservationHistory.tsx:36-39`).
- **Partial:** the direction label itself (`initial` / `unchanged` / `increased` /
  `decreased`) is carried per observation in the API record rather than the table
  (`frontend/src/lib/history.ts:31`) — confirm it at
  `/api/discovery/candidates/{id}/history` if you want the labels. The buyer-fixture
  steps contain no price **increase**; rising observations are retained too, pinned by
  `tests/test_history_workflow.py::history_retains_initial_unchanged_rising_and_falling_exact_revisions`
  and the connected-proof receipt (initial, unchanged, increased, decreased, unchanged,
  decreased). The frontend parsers refuse any non-null savings figure outright
  (`frontend/src/lib/assessments.ts:28`, `frontend/src/lib/history.ts:16`).
- **Defect if:** a savings or discount percentage anywhere; a drops-only history; a
  single observation presented as a bargain.
- ☐ Accepted · Evidence match (yes / partial / no) + your words: \_\_\_\_\_\_\_\_\_\_

#### G3 — Missing periods and acquisition failures are visible · after `stale` (US29)

- **Do:** Same history panel and `/api/discovery/candidates/{id}/history` (gaps and
  attempts lists), after the conductor runs the `stale` step (three hours pass with no
  collection).
- **Expect:** the coverage reason reads "Only retained captures … Intervals between
  samples are unobserved … Synthetic dates establish no real longitudinal history."
  (`src/pricerecon/models/history.py:137-142`); last-good evidence shows its age with
  "Freshness unvalidated; current price and availability unknown."
  (`frontend/src/components/discovery/ObservationHistory.tsx:42-46`); the API carries
  an explicit gaps list (unobserved interval / open interval / source outcome / not
  returned).
- **Partial:** the walkthrough fixture's scripted steps produce successful captures;
  the cached, failed and capped attempt states are exercised in the guarded suite
  (`tests/test_collection_workflow.py`, the connected-proof "gaps" checkpoint,
  `tests/monitoring/watch_workflow.py:338-340`) rather than by a fixture step. Record
  what attempt states actually appear.
- **Defect if:** gaps hidden; continuity or availability implied between samples.
- ☐ Accepted · Evidence match (yes / partial / no) + your words: \_\_\_\_\_\_\_\_\_\_

### Cluster H — Coverage & freshness disclosure (US30, 31, 41–44)

#### H1 — "Best" always carries its checked scope · after `coupon` (US30, US31)

- **Do:** Discover → **Source coverage**. Read the roster, then the per-capture
  outcome list below it.
- **Expect:** "Sources and gaps (N routes)" with each lane's accepted status, reason,
  prerequisites and "Latest recorded attempt: … not attempted; missing current
  evidence" where nothing ran
  (`frontend/src/components/discovery/SourceCoverage.tsx:106-155`); cohort gaps in
  caution text; "Capped, blocked and failed attempts leave gaps; an empty result means
  the declared search completed."
  (`frontend/src/components/discovery/CollectionCoverage.tsx:41-43`); per capture,
  the outcome state, listing count, completeness and — where applicable — "Reused
  capture …; no new source observation."
  (`frontend/src/pages/Discovery.tsx:754-777`). Assessments carry their scope: "Lowest
  among qualified offers checked in this scope only. Intervals are unobserved; no
  continuous availability, complete market or all-time claim."
  (`src/pricerecon/models/assessments.py:86-90`). The fixture roster has sixteen
  lanes; unchecked real routes are named as unchecked (buyer guide, task 4).
- **Defect if:** "best" without a disclosed scope; a blocked or failed lane shown as
  empty results.
- ☐ Accepted · Evidence match (yes / partial / no) + your words: \_\_\_\_\_\_\_\_\_\_

#### H2 — Caps, reserves and gates are disclosed as unset — not as promises (US41, US42)

- **Do:** "Collection limits and coverage" panel (same view).
- **Expect:** operating policy state, activation state and pending gates; usage rows
  "… used or reserved of …; tracking reserve …" with the note "Tracking and
  potential-alert verification have reserved capacity."
  (`frontend/src/components/discovery/CollectionCoverage.tsx:33-78`); and the closing
  honest note: "Collection also requires finite measured budgets, physical
  storage/WAL/log/backup limits, retention/deletion/restore qualification and a named
  maintenance owner. Fixture allowances do not supply these operating prerequisites."
  (`frontend/src/components/discovery/SourceCoverage.tsx:149-151`).
- **Honesty:** the numbers shown are fixture allowances. Measured operating limits are
  an unproven gate (section 4) — nothing here is a commitment.
- **Defect if:** fixture allowances presented as operating capacity.
- ☐ Accepted · Evidence match (yes / partial / no) + your words: \_\_\_\_\_\_\_\_\_\_

#### H3 — Age, staleness and no catch-up bursts · after `stale` (US43, US44)

- **Do:** After the `stale` step, reload History, the collection panel and a tracked
  watch.
- **Expect:** last-good evidence is preserved with its grown age and "Freshness
  unvalidated"; the tracked watch reads "Stale evidence · alerts wait for a fresh
  offer" (`frontend/src/components/ExactTracking.tsx:65-67`) and its assessment is
  withheld — stale evidence alone never alerts; where a schedule exists the panel
  shows "Next eligible …; no catch-up replay."
  (`frontend/src/components/discovery/CollectionCoverage.tsx:88`).
- **Defect if:** a stale capture presented as a current verified offer; a duplicate
  alert after recovery.
- ☐ Accepted · Evidence match (yes / partial / no) + your words: \_\_\_\_\_\_\_\_\_\_

### Cluster I — Corrections & lineage (US33–35)

#### I1 — Correct a field and keep its lineage · after `coupon` (US33)

- **Do:** Open **Wrong watch details?** (product page → Correction). Change the dial
  from mint to salmon; enter your name and a reason ("The selected variation differs
  from this watch."); save; reload. (The retained conflict screenshots show an actual
  API 409 rendered by the UI if a competing write happens — buyer guide, task 6.)
- **Expect:** before saving, the form shows original vs intended values and the
  consequence copy "Old prices stop applying. Your target stays; alerts wait for a
  matching offer." (`frontend/src/components/discovery/IdentityCorrection.tsx:62,99-102`)
  — and promises no new price or refresh. After saving, the correction history lists
  each lineage entry "dial: mint → salmon (corrected)" with your name, rationale and
  time (`frontend/src/components/discovery/IdentityCorrection.tsx:174-211`); no field
  is attributed to an invented actor. A rejected/stale write shows an error and
  "Reload the feed before retrying." — never a success message
  (`frontend/src/components/discovery/IdentityCorrection.tsx:169`).
- **Defect if:** lineage erased or overwritten; an anonymous correction; success
  claimed on a rejected write.
- ☐ Accepted · Evidence match (yes / partial / no) + your words: \_\_\_\_\_\_\_\_\_\_

#### I2 — Dependent evidence is withdrawn, not transferred (US34)

- **Do:** After saving, revisit the feed card, Costs, History and the tracking view.
- **Expect:** the card caution "Old prices withdrawn · matching offer needed"
  (`frontend/src/pages/Discovery.tsx:261-263`); the delivered total returns to "Total
  unknown" (`tests/monitoring/watch_workflow.py:346`); the coupon state reads
  "invalidated" (`tests/monitoring/watch_workflow.py:347`); assessments go historical
  or withdraw ("Current comparison unavailable"); the alert assessment is "withheld"
  (`tests/monitoring/watch_workflow.py:350-352`). Original observations keep their
  original mint configuration — old mint prices are **not** relabelled salmon
  (`tests/monitoring/watch_workflow.py:357-360`).
- **Defect if:** a pre-correction price attached to the corrected watch; a total
  computed from withdrawn evidence; an alert from pre-correction evidence.
- ☐ Accepted · Evidence match (yes / partial / no) + your words: \_\_\_\_\_\_\_\_\_\_

#### I3 — Tracking intent survives the correction (US35)

- **Do:** Check **Saved targets** and the tracking view.
- **Expect:** the £60 target is retained with "Evidence withdrawn · target retained"
  (`frontend/src/components/ExactTracking.tsx:68-70`); the correction history shows
  "Intended dial: salmon"
  (`frontend/src/components/discovery/IdentityCorrection.tsx:184-191`) and the API
  tracking record carries `intended_values.dial = "salmon"`; the separate Casio £40
  target is untouched
  (`tests/monitoring/watch_workflow.py:348-356`).
- **Defect if:** the correction silently discarded or rewrote your target.
- ☐ Accepted · Evidence match (yes / partial / no) + your words: \_\_\_\_\_\_\_\_\_\_

### Cluster J — Exact tracking (US36–40)

#### J1 — Track an exact product from discovery (US36)

- **Do:** Addiesdive → **Track this watch**. Save a £60 delivered target; optionally
  tick webhook (delivery is captured to records only — nothing leaves the fixture).
  Repeat with a £40 target for Casio. Try to track Militado or Merkur.
- **Expect:** "Delivered target saved. Collection remains staged."
  (`frontend/src/components/ExactTracking.tsx:223`); the tracking block shows the
  exact tracked values (reference, dial, movement, strap) and "Saving keeps this exact
  intent … A supplied policy and fresh qualified evidence are required before verified
  delivered alerts." (`frontend/src/components/ExactTracking.tsx:236-245`);
  unresolved identities refuse tracking — "Exact identity must be resolved before
  starting exact tracking." (`frontend/src/components/ExactTracking.tsx:246-248`).
  Legacy saved-search rules are not rewritten by any of this.
- **Defect if:** a target saved against an unresolved configuration; legacy watch
  behaviour changed.
- ☐ Accepted · Evidence match (yes / partial / no) + your words: \_\_\_\_\_\_\_\_\_\_

#### J2 — One alert on a verified crossing · steps `baseline`, `cross` (US37)

- **Do:** Conductor runs `baseline`; reload; conductor runs `cross`; reload. Read the
  tracking status and (if webhook selected) the fixture marker's send count and
  "Load records" delivery records. Repeat with **no** channels selected on the Casio
  target.
- **Expect:** baseline GBP 70.10 → "Above target", no alert, zero sends; crossing
  GBP 58.10 → "Eligible at target" with reason "Verified delivered total crossed your
  target." and exactly **one** alert event. With webhook selected the marker's
  captured sends run 0 → 1 across these steps (recorded: 0/1/1/2 for
  baseline/cross/duplicate/drop, buyer guide "Buyer-assisted target crossing"). With
  no channels selected the crossing is still recorded but nothing is sent ("With no
  selected channels, no target message is sent."
  `frontend/src/components/ExactTracking.tsx:278-281`); the recorded event carried
  status `channels_unset`. Alert events are inspected at `/api/events` and the
  per-channel records at `/api/discovery/tracking/{id}/deliveries`
  (`tests/monitoring/tracking_workflows.py:202-207`; the Event stream page is a
  placeholder at this revision).
- **Defect if:** an alert from an unknown or conditional total; two events for one
  crossing; anything sent without a selected channel.
- ☐ Accepted · Evidence match (yes / partial / no) + your words: \_\_\_\_\_\_\_\_\_\_

#### J3 — Repeat suppression and further drops · steps `duplicate`, `drop` (US38, US39)

- **Do:** Conductor runs `duplicate`; reload; then `drop`; reload.
- **Expect:** the duplicate GBP 58.10 adds nothing — reason "Same offer and price, or
  no further drop; repeat alert suppressed."
  (`frontend/src/components/ExactTracking.tsx:26`); the send count stays at 1. The
  further drop to GBP 56.10 alerts once more — "A further qualifying delivered-price
  drop." (`frontend/src/components/ExactTracking.tsx:25`) — send count 2.
- **Defect if:** duplicate noise; a further qualifying drop that does not alert.
- ☐ Accepted · Evidence match (yes / partial / no) + your words: \_\_\_\_\_\_\_\_\_\_

#### J4 — Restart, recovery and ambiguous sends behave consistently (US40)

- **Do:** On a tracked watch with a delivery record, open "Load records" and read the
  reconciliation controls. (Only attempt a fixture restart if the session was split —
  note that it resets state.)
- **Expect:** ambiguous send states require your explicit resolution behind a
  confirmation ("I have stopped the sending process and confirmed no send is in
  flight.") and "These actions record your resolution and never resend the message."
  (`frontend/src/components/ExactTracking.tsx:152-175`); the UI states that
  exactly-once delivery is not guaranteed
  (`frontend/src/components/ExactTracking.tsx:135-138`).
- **Partial:** restart/recovery non-duplication cannot be shown in one fixture run
  (temporary storage); it is pinned by the guarded suite
  (`tests/test_tracking_workflow.py:39-57`) and the resume receipt
  (`tests/monitoring/watch_workflow.py:403-434`) — recovery produced no duplicate
  alert and no new sends.
- **Defect if:** an automatic resend of an ambiguous delivery; a duplicate alert after
  restart or recovery.
- ☐ Accepted · Evidence match (yes / partial / no) + your words: \_\_\_\_\_\_\_\_\_\_

### Cluster K — Source evidence (US32, 45, 46)

#### K1 — Expandable evidence and exclusion reasons (US32)

- **Do:** Product page → Technical (evidence rows, then "Complete retained record");
  a tracked watch's "Alert eligibility details"; Source coverage's "Source claims:
  review required" block and source receipt for a capture.
- **Expect:** every claim exposes issuer, extraction, retrieval, validity and derived
  lineage (`frontend/src/pages/Discovery.tsx:522-534`); source claims are labelled
  "Source claims: review required" with "Missing evidence: …"
  (`frontend/src/components/discovery/SourceCoverage.tsx:55-113`); every withholding
  decision names its gate in the alert-eligibility list
  (`frontend/src/components/ExactTracking.tsx:20-54`); assessment exclusions and gaps
  are queryable at `/api/discovery/assessments` (`exclusions`, `gaps`).
- **Defect if:** an offer qualified (or withheld) with no inspectable reason.
- ☐ Accepted · Evidence match (yes / partial / no) + your words: \_\_\_\_\_\_\_\_\_\_

#### K2 — Receipts and rights prerequisites stay explicit (US45, US46)

- **Do:** Expand a capture's source receipt "Technical evidence" and the roster's
  "Prerequisites" lines.
- **Expect:** route and host, page/item/detail limits, discovered vs inspected counts,
  "Next page present/not reported", content-truncation state, and the rights line:
  "Use reference …; retention …; history rights unqualified. Retrieval does not grant
  storage or current freshness."
  (`frontend/src/components/discovery/SourceCoverage.tsx:14-52`); per-lane
  prerequisites on the roster (`frontend/src/components/discovery/SourceCoverage.tsx:122-123`).
  Gate outcomes read as deterministic/offline verification, never as live evidence.
- **Defect if:** a successful retrieval presented as continuing-use rights or as a
  gate outcome it is not.
- ☐ Accepted · Evidence match (yes / partial / no) + your words: \_\_\_\_\_\_\_\_\_\_

## 3. Honesty spot-checks (the fail-closed contracts)

Run these as explicit spot-checks and record pass/flag. They are the contracts this
repo treats as defects when broken.

### S1 — Fixture/synthetic provenance is marked, fail-closed

- **API:** at `/api/discovery/assessments`, every price claim (`current_best`,
  `observed_low`, `usual_price`, `personal_price`) carries an explicit
  `"synthetic": true|false`. Every fixture-decided amount must read `true` — the
  marker is re-derived from the underlying paths on every read, so an unmarked stored
  payload is upgraded to `synthetic`, never downgraded
  (`src/pricerecon/models/assessments.py:57-77`; coupon-chain evidence included in
  the derivation, `src/pricerecon/db/history.py:190-196,252-330`).
- **API (history):** observations at `/api/discovery/candidates/{id}/history` carry
  `evidence_kind: "synthetic"` and `market_history_eligible: false`; the envelope's
  `market_history_eligible_count` is 0 for the fixture
  (`src/pricerecon/models/history.py:130-133`).
- **UI:** the session banner "Synthetic session · prices and buying evidence are test
  data." appears on the feed and product pages
  (`frontend/src/pages/Discovery.tsx:627,691-695`). The per-amount warning
  "Synthetic verification data: the claimed amount is decided by fixture evidence,
  not a live market fact." is mounted on the product History view directly beneath
  the current-best amount whenever that envelope claim is synthetic
  (`frontend/src/pages/Discovery.tsx:467-472`), and a coupon block whose supplied
  evidence is retained synthetically surfaces "Synthetic checkout evidence."
  (`frontend/src/pages/Discovery.tsx:419-421`); live claims and minimal-retention
  coupon evidence render no marker (mounted-render coverage in
  `frontend/src/components/__tests__/DiscoveryHierarchy.test.ts`). **Partial:** the
  mounted History view shows only the current-best amount, so the marker beside
  `observed_low`, the per-path markers and the fuller per-claim detail remain in the
  Comparable-prices detail component
  (`frontend/src/components/discovery/PriceAssessments.tsx:7-10`), which is still not
  mounted in the product views — cross-check those on the API envelope or the
  Technical "Complete retained record" JSON, and keep the API check above as the
  cross-check for the mounted marker too.
- **Parser guard:** the frontend refuses any claim payload without an explicit marker
  rather than reading it as live (`frontend/src/lib/assessments.ts:10-12`).
- **Red flags:** a fixture amount without `synthetic: true`; a synthetic observation
  counted as market history; the session banner absent in a fixture session.
- ☐ Pass · Flag · Notes: \_\_\_\_\_\_\_\_\_\_

### S2 — Missing costs block totals

- Pick any candidate with an unknown payable component. Its card and cost scenario
  must read "Total unknown" / "Known subtotal …; incomplete, not a delivered total."
  (`frontend/src/pages/Discovery.tsx:198-210,281-283`). In the API, the scenario's
  `total` is null with state `unknown`; the unknown charge keeps amount null.
  Regression anchors: `tests/test_cost_workflow.py:45,69`.
- **Red flags:** a delivered total containing an unknown component; an unknown charge
  rendered as 0; a known subtotal labelled as a total.
- ☐ Pass · Flag · Notes: \_\_\_\_\_\_\_\_\_\_

### S3 — Savings never render from sparse history

- History view and observations panel must say "Usual price unavailable … No savings
  claim." (`frontend/src/pages/Discovery.tsx:481-483`,
  `frontend/src/components/discovery/ObservationHistory.tsx:36-39`). In the API,
  `savings` is null and `usual_price.state` is `"unavailable"` on both the assessment
  and history envelopes; the frontend parsers reject payloads where either is set
  (`frontend/src/lib/assessments.ts:28`, `frontend/src/lib/history.ts:16`).
  Regression anchors: `tests/test_assessment_workflow.py:27,73`.
- **Red flags:** any percentage-off or "you save" text; an RRP or first capture
  presented as a usual price.
- ☐ Pass · Flag · Notes: \_\_\_\_\_\_\_\_\_\_

### S4 — Expired/conflicting coupons withhold

- A coupon whose terms are expired, ineligible or mutually contradictory must produce
  no reduced payable: no `resulting_cost`, issue text visible, base total unchanged.
  A reproduced receipt yields its own resulting cost **beside** — never replacing —
  the base. Regression anchors: final-review P1 repair ([watch-final-review](watch-final-review.md),
  "P1: lost conflicting coupon terms") and `tests/test_coupon_workflow.py:44-56,82`.
- **Partial:** the fixture step demonstrates the reproduced-vs-base separation (see
  F1/F2); conflicting terms are suite-proven. Record what the deployed fixture shows.
- **Red flags:** a reduced total from an advertised code alone; summed incompatible
  promotions; cashback inside a payable.
- ☐ Pass · Flag · Notes: \_\_\_\_\_\_\_\_\_\_

### S5 — Corrections invalidate dependents and retain lineage

- After the I-cluster correction: totals withdrawn ("Total unknown"), coupon
  invalidated, assessments historical/withdrawn, alert withheld, target retained,
  original observations unchanged, lineage append-only with actor/rationale/time.
  Regression anchors: `tests/test_correction_workflow.py:26-34` and the fixture
  assertions in `tests/monitoring/watch_workflow.py:341-362`.
- **Red flags:** any pre-correction price reused for the corrected watch; lost target;
  overwritten lineage.
- ☐ Pass · Flag · Notes: \_\_\_\_\_\_\_\_\_\_

## 4. Do not conclude (explicitly unproven gates)

Nothing in this session — however it goes — establishes any of the following. A
verdict of "accept" is acceptance of **offline human comprehension only**.

1. **Live offer obtainability.** No live-market capability is proven or claimed
   anywhere. The one bounded live pilot (2026-10-29) returned ten leads, zero
   qualified UK delivered totals and all-unresolved identities; its grant is consumed
   and no further live run is authorised ([live-pilot-first-run](live-pilot-first-run.md),
   [live-pilot-offline-repair](live-pilot-offline-repair.md)).
2. **Delivered totals from live sources.** Every amount in this session is fixture
   arithmetic. Tax/import treatment is synthetic evidence, not validated current law.
3. **Live coupon success.** A fixture reproduction receipt proves the mechanism, not
   that any code will apply at a real checkout.
4. **History and savings calibration.** Sparse synthetic observations create no
   longitudinal history ("Synthetic dates establish no real longitudinal history");
   usual price and savings stay withheld until empirical calibration is accepted.
5. **Operating limits.** The caps/reserves shown are fixture allowances. Measured
   finite request/page/detail/retry limits, storage/log/backup limits, study duration,
   spend and operator-time ceilings, and a named maintenance/stop-resume owner are all
   unmeasured and unassigned.
6. **Release and activation maturity.** Collection remains staged; source
   rights/retention/deletion/backup prerequisites, migration approval and notification
   delivery are separate gates. Captured sends are captured records, not external
   delivery.
7. **Live manufacturer provenance.** The manufacturer-spec reachability path works
   against the shipped registry only, which contains a reserved fixture host
   (`src/pricerecon/connectors/manufacturer_spec.py:30,63`). Real manufacturer hosts
   require an operator registration change; do not read the "supported" state as
   live manufacturer authority. Likewise the live-fact publication contract
   (`require_live`) has no production call site yet
   (`src/pricerecon/core/comparisons.py:149-151`).
8. **Cohort evidence completeness.** Militado and Merkur remain unresolved by design;
   missing evidence is a demonstrated abstention, not a completed cohort.

## 5. Verdict form

Session metadata:

- Date(s): \_\_\_\_\_\_\_\_\_\_ · Sittings: \_\_\_ · Fixture restarted between sittings? \_\_\_
- Deployed instance revision (commit): \_\_\_\_\_\_\_\_\_\_ · Fixture marker id: \_\_\_\_\_\_\_\_\_\_
- Viewports used (desktop 1280 / narrow 375 / keyboard): \_\_\_\_\_\_\_\_\_\_
- Assistance given (if any): \_\_\_\_\_\_\_\_\_\_

Per-story-cluster verdict (accept / flag). "Evidence match" is your judgement of
whether the screen matched the claims in the cluster's tasks.

| Cluster | Stories | Verdict | Evidence match (yes/partial/no) | Notes |
| --- | --- | --- | --- | --- |
| A — Monitoring preservation | US1–2 | ☐ accept ☐ flag | | |
| B — Discovery feed & preferences | US3–5, 7–8 | ☐ accept ☐ flag | | |
| C — Identity & uncertainty honesty | US6, 9–13 | ☐ accept ☐ flag | | |
| D — Seller, condition & cohorts | US14–17 | ☐ accept ☐ flag | | |
| E — UK delivered cost & missing costs | US18–21 | ☐ accept ☐ flag | | |
| F — Coupons & conflict withholding | US22–25 | ☐ accept ☐ flag | | |
| G — Assessments & history honesty | US26–29 | ☐ accept ☐ flag | | |
| H — Coverage & freshness disclosure | US30–31, 41–44 | ☐ accept ☐ flag | | |
| I — Corrections & lineage | US33–35 | ☐ accept ☐ flag | | |
| J — Exact tracking | US36–40 | ☐ accept ☐ flag | | |
| K — Source evidence | US32, 45–46 | ☐ accept ☐ flag | | |
| S1–S5 — Honesty spot-checks | fail-closed contracts | ☐ pass ☐ flag | | |

Overall verdict (tick one):

- ☐ **Accept** — offline human comprehension established; clusters and spot-checks
  clear.
- ☐ **Accept with follow-ups** — comprehension established; the follow-up items below
  are recorded and owned.
- ☐ **Reject** — one or more clusters or spot-checks failed comprehension or honesty;
  describe below.

Follow-up items:

| # | Item (what was unclear, missing or wrong) | Owner | Notes |
| --- | --- | --- | --- |
| 1 | | | |
| 2 | | | |
| 3 | | | |

Acknowledgement (the buyer signs this to bound the verdict):

- ☐ I understand this verdict accepts **offline behaviour and my own comprehension of
  it only**. The gates listed in section 4 — live offers, live delivered totals, live
  coupon success, history/savings calibration, operating limits, release/activation
  maturity, live manufacturer provenance — remain unproven and are not implied by my
  acceptance.

Buyer: \_\_\_\_\_\_\_\_\_\_ · Date: \_\_\_\_\_\_\_\_\_\_

---

Provenance of this kit: written against the source at the recorded revision; every UI
surface named here was cross-checked against the frontend sources cited inline
(`frontend/src/pages/Discovery.tsx`, `frontend/src/components/discovery/*`,
`frontend/src/components/ExactTracking.tsx`, `frontend/src/lib/*`) and the API routes
in `src/pricerecon/api/discovery.py`, `src/pricerecon/api/tracking.py` and
`src/pricerecon/api/corrections.py`. Fixture-specific expectations are cited to
`tests/monitoring/watch_workflow.py` and `tests/monitoring/watch_workflow_ui.py`.
Where only test or component-level proof exists, the task says **Partial** and names
the anchor. Retained screenshots in [the buyer guide](watch-workflow-buyer-guide.md)
are review aids from earlier revisions; they do not prove this one.
