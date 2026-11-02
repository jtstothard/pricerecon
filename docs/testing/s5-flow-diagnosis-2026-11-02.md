# S5 flow diagnosis — correction invalidation + lineage (2026-11-02)

Two jobs: (1) the S5 honesty spot-check of the buyer walkthrough (dependents
invalidate on a correction; lineage appends, nothing overwritten) against a fresh
synthetic fixture, and (2) a first-time-buyer comprehension diagnosis of the
correction flow — the buyer attempted S5 today and reported only "S5 didnt do as
it is confusing". Diagnosis and ranked recommendations only; **no code was
changed** (presentation fixes are proposals in §3). *Update 2026-11-02: the
ranked fixes have since been implemented and re-walked — see §6.*

- Branch `t3/s5-flow-diagnosis-2026-11-02` from `origin/main` @ `9470105`.
- Fresh fixture: `tests.monitoring.discovery_ui_server --workflow` built from this
  worktree (frontend built here; `npm ci --offline` + `npm run build`), served on
  loopback port **8897**. Marker gate before and after: fixture
  `ticket12-connected-ui-v1`, `temporary_storage=true`, `automatic_checks=false`,
  `blocked_edges=[]`, fixture id `37bdcd19a63e4c26a763cfbad1bd773a`. Guard receipt
  at shutdown: same identity, `blocked_edges=[]`, `notifications_sent=3` (captured
  transport only). The buyer's live session (8896) and the reserved fixture ports
  8893–8895 were never contacted, killed or mutated.
- Fixture steps run through the run-bound conductor
  (`tests.monitoring.watch_workflow_ui --port 8897 --step …`) in the kit's
  session-script order: `baseline` → `cross` → `duplicate` → `drop` → `costs` →
  `coupon` (the I-cluster checkpoint). Fixture clock 2026-10-27T12:00:36Z →
  12:04:48Z. Targets were saved through the UI first (Addiesdive £60 delivered
  with webhook, Casio £40) so the S5 items "alert withheld" and "target retained"
  have something to act on. The `stale` step was not needed for S5 and was not run.
- UI driving: headless Chrome via `agent-browser` (unique session
  `s5diag-8897`, `--allowed-domains 127.0.0.1`, 1280×900), plus direct API reads
  against my own fixture. The correction was performed through the UI exactly as
  I1 asks; a second UI correction was made solely to prove append-only lineage.
- Offline throughout: the fixture is zero-outbound by construction and was kept
  that way; the browser was restricted to 127.0.0.1.

## 1. S5 behavioral evidence — **PASS**

Kit S5 (`docs/testing/buyer-walkthrough.md:840-848`): after the I-cluster
correction, totals withdrawn ("Total unknown"), coupon invalidated, assessments
historical/withdrawn, alert withheld, target retained, original observations
unchanged, lineage append-only with actor/rationale/time. Every item was observed
on this fresh fixture.

**Correction performed (UI, I1):** product page → Correction tab → Identity field
`dial` → value `salmon` (via "Other / custom" — see F3) → Reason preset "The
selected variation differs from this watch." → Your name "Automated walkthrough
agent (not the buyer), 2026-11-02" → **Save watch details**. A second correction
(`dial` → `Blue`, reason "The source description conflicts with the watch shown.")
was made to verify the append-only claim.

| S5 item | Before | After | Verdict |
| --- | --- | --- | --- |
| Totals withdrawn | `public_delivered_total` GBP 50.10 (`verified_at_observation`); card "GBP 70.10"→ step chain ends 50.10 | `amount: null`, `state: unknown`; card "Total unknown" | ✅ |
| Coupon invalidated | "Synthetic TEN opportunity" `reproduced_at_observation`, `resulting_cost` 45.10 | `state: invalidated`, `resulting_cost: null`, `historical_resulting_cost` retains 45.10 | ✅ |
| Assessments historical/withdrawn | coupon-era assessment `historical:false`, `current_best.state:"supported"` 45.10 | **all** assessments `historical:true`; states `supported`/`historical` → `invalidated` with dated amounts retained ("Current comparison unavailable. When this assessment was current, the lowest verified total was GBP 70.10 — a dated record, not a current price.") | ✅ |
| Alert withheld | tracking #1 assessment `eligible` ("A further qualifying delivered-price drop."), 3 `exact_target_crossing` events on record | assessment `withheld`, reason `evidence_invalidated` → "Alert withheld · target £60 delivered" / "Evidence was withdrawn or corrected; intent retained." No new events. | ✅ |
| Target retained | Addiesdive £60 (webhook), Casio £40 | #1 `target_gbp: "60"` retained, `intended_values.dial` now carries the corrected value ("Intended dial: salmon" after correction #1); #2 Casio `target_gbp: "40"` untouched | ✅ |
| Original observations unchanged | 6 observations, all config `dial: mint`, totals 70.10/70.10/58.10/58.10/56.10/50.10 | same 6 observations, still `dial: mint` (nothing relabelled salmon/Blue), totals retained; `validity: invalidated` with invalidation records `"Identity corrected: dial; correction 2c69ade4-…"` | ✅ |
| Lineage append-only (actor/rationale/time) | none | correction #1: `dial | mint → salmon | corrected | actor … 2026-11-02 | 2026-10-27T12:04:48Z | "The selected variation differs from this watch." | prev: None`. Correction #2 **appended**: `dial | salmon → Blue | … | "The source description conflicts with the watch shown." | prev: 2c69ade4-…`. Entry #1 preserved verbatim; `original_configuration.dial` still `mint`; correction revision 2 with both entries. | ✅ |

UI corroboration: card caution "Old prices withdrawn · matching offer needed";
Costs "Historical item lead (withdrawn)", "Historical cost withdrawn. Not a
current payable price.", "Historical coupon result withdrawn; unavailable as a
current payable scenario."; History table rows "invalidated · withdrawn" with
their original totals; Tracking "Evidence withdrawn · target retained"; the
correction tab's history panel lists the lineage entries with
`dial: mint → salmon (corrected)` / `dial: salmon → Blue (corrected)`, actor,
time and rationale. The rejected-write path (409 → "Reload the feed before
retrying.", never a success message) was verified in the 2026-10-31 agent run and
is not re-tested here.

**S5 behavioral verdict: PASS.** The honesty machinery does exactly what the kit
says. Which is precisely why the buyer's confusion is a *presentation* problem —
and the rest of this document is about that.

## 2. Friction-point inventory (first-time buyer walk)

Each point: screen/step → what the buyer sees (exact strings) → why it confuses →
a presentation-only fix. Nothing below proposes a behavior change.

### F1 — Discoverability: the correction form is hidden and misnamed (severity: high)

- **Where:** feed card and product page → looking for the way to fix "wrong watch
  details"; also the path the buyer was pointed at ("product → Technical record →
  correction form").
- **What the buyer sees:** the feed card offers only "Product details" and "Track
  this watch" (later "Edit delivered target"). The product tab bar is
  "Overview / Costs / History / Tracking / Correction / Technical"
  (`frontend/src/pages/Discovery.tsx:598`) — the tab is named the noun
  "**Correction**", which reads like a price adjustment or an order fix, not "tell
  us the watch details are wrong". The kit's own handle for the form, "**Wrong
  watch details?**", is an `h3` *inside* the form
  (`frontend/src/components/discovery/IdentityCorrection.tsx:61`) — you must find
  the form to find the words that tell you the form exists. The Technical tab
  (heading "**Technical evidence**", not "Technical record") contains no form and
  no link to one; the only cross-reference points the opposite way ("Full original
  evidence and revisions are retained in Technical.",
  `IdentityCorrection.tsx:173`). A buyer following "product → Technical record →
  correction form" hits a dead end full of raw JSON ("Complete retained record").
- **Why it confuses:** the buyer is looking for an *action* ("report wrong
  details") and finds only *record* tabs; the vocabulary they were given ("Wrong
  watch details?", "Technical record") matches nothing on screen at the moment
  they need it.
- **Fix:** entry points at the point of need — a "Wrong watch details?" link on
  the feed card and product hero (and a one-line pointer in Technical: "Details
  wrong? Correct them on the Correction tab."); consider renaming the tab to
  "Wrong details?" so the action is named after the buyer's thought.

### F2 — The promised original-vs-intended preview lags one save behind (severity: high)

- **Where:** correction form, the paragraph under "Identity field"
  (`IdentityCorrection.tsx:99-102`).
- **What the buyer sees:** before typing anything:
  "**Original acquired dial: mint. Intended value: mint.**" — both values
  identical, so the promised "before saving, the form shows original vs intended
  values" (kit I1 Expect) shows no change at all. Then, after typing `salmon` in
  "Correct value", the line **still** reads "Intended value: mint." It updates to
  "Intended value: salmon." only *after* the save. On the second correction I
  selected `Blue` while the line still said "Intended value: salmon."
- **Why it confuses:** the one element meant to let the buyer verify the change
  before committing is silently wrong at exactly the moment of decision. It reads
  as the form not registering the input (a plausible reading of "S5 didnt do").
- **Fix:** make the preview live and explicit: "You are changing **dial** from
  **mint** to **[whatever is in the value field]**", greyed out until a value is
  chosen; rename the stale version to "Last saved value" if it is kept.

### F3 — The value picker cannot express the task ("Change the dial … to salmon") (severity: high)

- **Where:** "Correct value" select (`IdentityCorrection.tsx:103-125`,
  `frontend/src/components/discovery/ChoiceValue.tsx:35-41`).
- **What the buyer sees:** "Not set / Blue / Green / Pink / Purple / Multicolour /
  Black / White / **Other / custom**". Neither the current value (`mint`) nor the
  value the kit tells the buyer to enter (`salmon`) is in the list; the presets
  are Capitalized while the recorded values are lowercase (`mint`), so even the
  "same" value looks different. To enter salmon the buyer must notice the
  "Other / custom" escape hatch, select it, and then fill the text box that only
  then appears ("Correct value custom value").
- **Why it confuses:** a first-time buyer reasonably concludes the allowed values
  are the listed ones — and either picks "Pink" as the nearest match (recording a
  false fact) or gives up believing the flow "didnt do". The kit's canonical S5
  task is literally inexpressible without prior knowledge of the custom path.
- **Fix:** make the current value visible in the picker ("mint (current)") and the
  escape hatch self-describing ("Type another value…"); better, use a text input
  with the presets as suggestions so any value is obviously allowed. (Suggestion
  lists may change; persisted values must remain arbitrary — the component's own
  contract: "Presets never replace arbitrary persisted values.")

### F4 — Post-save feedback never shows the honesty behavior it just performed (severity: high)

- **Where:** after **Save watch details** (`IdentityCorrection.tsx:48-50`); then
  the rest of the app.
- **What the buyer sees:** one sentence — "Correction saved. Old prices stop
  applying. Your target stays; alerts wait for a matching offer." — rendered under
  the "Correction state" heading where it reads as part of that section. Nothing
  else on screen changes. The three dependent effects S5 asks the buyer to verify
  are each somewhere else, worded differently, and none names the correction as
  the cause: feed card "Total unknown" + "Old prices withdrawn · matching offer
  needed" (`Discovery.tsx:273-275,293-295`) with the title still reading
  "Addiesdive AD2066 **mint**"; Costs "Historical cost withdrawn. Not a current
  payable price." (`Discovery.tsx:197`) and "Historical coupon result withdrawn;
  unavailable as a current payable scenario." (`Discovery.tsx:448-452`); History
  "Historical assessment / Current comparison unavailable…" (all eight, nothing
  saying why they became historical); Tracking "Alert withheld" / "Evidence
  withdrawn · target retained" (`ExactTracking.tsx:18,68-70`). The lineage entry —
  the centerpiece of "nothing overwritten" — is in "Correction history and
  provenance" below the form, which the success message never points to.
- **Why it confuses:** the buyer is asked to confirm that dependents invalidated
  and lineage appended, but the UI shows either "nothing happened" (one sentence,
  form still empty) or "data was lost" (prices gone, identity unresolved) —
  never "this happened *because you corrected the dial*, and here is the entry we
  appended". This is the direct mechanism behind "S5 didnt do".
- **Fix (proposed copy):** a post-save summary naming each effect with a jump
  link, e.g.:
  > Correction saved — a history entry was added below.
  > Because **dial** changed (mint → salmon):
  > · the delivered total is withheld → "Total unknown" (was GBP 50.10)
  > · the TEN coupon result was invalidated (kept as a dated record)
  > · 6 old observations were marked withdrawn — kept, unchanged, in History
  > · your £60 target stays saved; alerts wait for evidence for the corrected watch
  > · 1 entry appended to the correction history (nothing is overwritten)

### F5 — One event, seven words: "withdrawn / stop applying / invalidated / historical / no longer apply / withheld / required" (severity: high)

- **Where:** everywhere the correction's consequence is described.
- **Exact strings:** "Old prices stop applying. Your target stays; alerts wait for
  a matching offer." (form + success message); "Old prices withdrawn · matching
  offer needed" (card) vs "Old prices withdrawn; matching offer needed." (hero,
  `Discovery.tsx:644` — same sentence, two punctuations); "Old prices, coupons and
  buying assessments no longer apply." (history panel); coupon state
  "**invalidated**"; "Historical item lead (withdrawn)"; "Historical cost
  withdrawn. Not a current payable price."; "Current comparison unavailable";
  "Evidence withdrawn · target retained"; observation status "invalidated ·
  withdrawn"; and the history-panel heading "**Identity corrected · required**"
  (`IdentityCorrection.tsx:176-178`) where `required` is the raw `requalification`
  enum (`frontend/src/lib/corrections.ts:10`) — "required" *what*? A watch buyer
  also reads "withdrawn" as *the seller withdrew the listing*.
- **Why it confuses:** a non-expert cannot tell whether data was deleted, hidden,
  or kept-but-deprecated — and S5's whole point is "kept, not overwritten". The
  vocabulary assumes the internal model (requalification, invalidation, withheld).
- **Fix:** one plain phrase everywhere ("kept on record, no longer used for
  pricing") plus a one-line gloss the first time each state appears; replace enum
  leaks ("Identity corrected · required" → "Corrected — waiting for fresh
  evidence"; the bare "supported" paragraph in the Costs coupon block,
  `Discovery.tsx:430`, → "Coupon applicability: supported at observation").

### F6 — Form fields speak the model, not the buyer (severity: medium)

- **Where:** the form top-to-bottom (`IdentityCorrection.tsx:64-141`).
- **Exact strings:** "Observed configuration" (a select of raw configuration ids —
  shown only when >1, but then unexplained); "Identity field" (options "maker,
  reference, generation, movement, case width mm, dial, strap, date display,
  product kind" — fine as a list, but "identity field" is internal vocabulary);
  the section "**Correction state**" whose only control is "Identity state" with
  options "Corrected; fresh evidence required" / "Disputed; withhold
  qualification" — two `h3`s ("Wrong watch details?", "Correction state") for one
  small form, and "withhold qualification" is unexplained jargon whose consequence
  (buying qualification paused) is invisible. After saving, the history panel lists
  **all nine** fields as "Intended product kind … Intended date display"
  (`IdentityCorrection.tsx:184-191`) for one dial change, and the "needs" list
  reads "Fresh compatible configuration and selected merchant variation evidence"
  / "New history/comparison qualification and target assessment".
- **Why it confuses:** the buyer must already know what "identity", "state",
  "requalification" and "qualification" mean to make a two-minute factual fix;
  the nine "Intended" rows make a single-field correction look like the whole
  watch was redefined.
- **Fix:** plain labels ("What's wrong?" / "What should it be?" / "How sure are
  you?" with option text "It's fixed — re-check prices" vs "Not sure — pause
  buying qualification"); history summary shows only the changed field
  ("dial: mint → salmon") with the full intended configuration behind a
  "Show full intended configuration" disclosure; drop the "Correction state"
  wrapper heading.

### F7 — "Reason" mechanics are unexplained ("Not set" on a required field) (severity: medium)

- **Where:** "Reason" select (`IdentityCorrection.tsx:153-164`, `ChoiceValue.tsx`).
- **What the buyer sees:** options "Not set / The selected variation differs from
  this watch. / The source description conflicts with the watch shown. / The
  recorded specification is incorrect. / Other / custom". "Not set" is offered on
  a **required** field — selecting it passes visual inspection and then fails
  browser validation with no explanation. Nothing says the reason is *permanently
  recorded beside your name* in the lineage; the buyer only discovers this after
  saving, when it appears under the entry.
- **Why it confuses:** the buyer doesn't know why a canned sentence is needed, what
  it will do, or where it will go; the natural first pick ("Not set") is a trap.
- **Fix:** label "Reason (recorded with your name in the correction history)";
  required selects start at "Choose a reason…" with no "Not set" option; free text
  as the primary affordance with the presets as examples.

### F8 — Button and pre-form copy mis-sell the action (severity: medium)

- **Where:** submit button "**Save watch details**" (`IdentityCorrection.tsx:165-167`)
  and the paragraph shown before any input: "Old prices stop applying. Your target
  stays; alerts wait for a matching offer." (`IdentityCorrection.tsx:62`).
- **What the buyer sees:** the button sounds like saving ordinary edits (vs. the
  honesty-critical act it is); the consequence copy is shown *before* the buyer has
  done anything and speaks of "your target" and "alerts" — which a buyer without a
  target or alerts cannot map to anything ("what target?"). The kit's promised
  "promises no new price or refresh" sentence is absent at this revision (already
  recorded as D-6 in `walkthrough-agent-run-2026-10-31.md`).
- **Fix:** button "Save correction — old prices will be withdrawn" (or at least
  "Save correction"); move consequence copy to the pre-save summary (F4) so it is
  specific to the pending change; restore/replace the "no new price or refresh"
  promise ("Saving records your correction; it does not fetch new prices.").

### F9 — After the correction the watch looks broken, and the fix is invisible (severity: medium)

- **Where:** feed card and product hero after saving.
- **What the buyer sees:** title still "**Addiesdive AD2066 mint**" (the reported
  title is retained as evidence — correct behavior, unexplained), while "Identity
  supported" flips to "**Identity unresolved**", the price becomes "Total unknown",
  cautions stack up ("Old prices withdrawn · matching offer needed"). The corrected
  fact (dial = salmon) appears nowhere on the card or hero. Tracking's editor now
  says "Exact identity must be resolved before starting exact tracking."
  (`ExactTracking.tsx:247`) directly under the retained £60 target — which reads
  like the target is blocked.
- **Why it confuses:** to a first-time buyer this is either "it ignored my change"
  (title unchanged) or "it lost my price" (everything else). The causal chain — you
  corrected the dial, so pre-correction evidence stopped applying — exists only in
  the model, never on screen.
- **Fix:** card/hero banner after a correction: "Details corrected (dial mint →
  salmon) · old prices withdrawn to History, awaiting evidence for the corrected
  watch"; consider showing the corrected spec beside the reported title ("dial:
  salmon (was: mint, as listed)").

### F10 — Minor dead-ends and leaks (severity: low, cumulative)

- The retained-observation table — the clearest "nothing was overwritten" evidence
  ("invalidated · withdrawn" rows with original totals) — sits behind a "Load
  retained observations" button (`ObservationHistory.tsx:24-26`); a buyer
  verifying "did my history survive?" sees a button, not the answer.
- Costs reads "**Total unknown — Total unknown**" (the `costStateLabel` repeats the
  dd text, `Discovery.tsx:389-393`) — reads like a rendering bug, undermining
  trust in exactly the screen that explains the withdrawal.
- Costs coupon block prints a bare paragraph "**supported**" (raw enum,
  `Discovery.tsx:430`).
- "Correction" is an *action* tab among five *record* tabs — mixed mental model;
  also `Value` presets vs record casing ("Blue" saved where "mint" was lowercase)
  makes lineage entries read inconsistently ("salmon → Blue").
- The Technical tab's "Complete retained record" is a wall of raw JSON
  (`Discovery.tsx:564`) — overwhelming for the buyer told to read "Capture
  lineage"; the human-readable part above it is fine.
- The success message renders visually inside/adjacent to the "Correction state"
  section, so it can be misread as describing that dropdown's state.

## 3. Ranked clarity fixes (presentation only — no behavior change)

Ranked by how much first-time-buyer confusion each removes.

1. **Post-save "what just changed" summary** (F4) — name each dependent effect and
   the appended lineage entry, with jump links to Costs/History/Tracking and the
   history panel. Copy in F4. This single change converts the S5 experience from
   "something vanished" into "the honesty contract just fired, visibly".
2. **Live before→after preview** (F2) — "You are changing dial from mint to
   salmon" while typing; never show a stale "Intended value".
3. **Discoverability** (F1) — "Wrong watch details?" entry points on the card,
   hero and Technical pointer; rename the tab toward the buyer's thought ("Wrong
   details?").
4. **A value input that can express the task** (F3) — current value visible,
   "Type another value…" escape hatch self-describing, suggestions not a closed
   list.
5. **One vocabulary for the withdrawal** (F5) — "kept on record, no longer used
   for pricing" everywhere; replace enum leaks ("Identity corrected · required",
   the bare "supported"); unify "Old prices withdrawn ·/; matching offer needed."
6. **Plain-language field labels and an honest button** (F6, F8) — "What's wrong?
   / What should it be? / How sure are you?"; "Save correction — old prices will
   be withdrawn"; single-field history summary with the nine-field intended config
   behind a disclosure; restore the "no new price or refresh" promise (D-6).
7. **Reason mechanics** (F7) — "Reason (recorded with your name in the correction
   history)"; "Choose a reason…" placeholder instead of "Not set" on required
   selects.
8. **Card/hero shows the correction and its cause** (F9) — "Details corrected
   (dial mint → salmon) · old prices withdrawn to History" so the unchanged
   reported title is not misread as the change failing.
9. **Minor polish** (F10) — auto-load or label the retained-observation table as
   the "kept, not overwritten" evidence; fix the doubled "Total unknown — Total
   unknown"; reword the tracking "Exact identity must be resolved…" line when a
   target is already retained.

None of these touches the correction API, the invalidation machinery, the lineage
record or any tested behavior; all are labels, copy, disclosure and placement.

## 4. What confused the buyer (one paragraph)

S5 asks the buyer to "make a correction … dependents (totals/history/alerts)
invalidate; lineage appends (actor/rationale/time) — nothing overwritten", but the
UI never uses those words and never shows those events happening. The form is
hiding behind a tab named "Correction" whose self-description "Wrong watch
details?" exists only inside it, while the buyer was steered toward a "Technical
record" that is actually called "Technical evidence" and contains no form — so the
walk started at a dead end. Inside the form, the task's own value ("salmon") was
not in the dropdown, the promised original-vs-intended preview showed two identical
values before saving and a stale value after (so it looked like the input wasn't
registering — the most literal reading of "S5 didnt do"), and required selects
offered "Not set" as an option. After saving, the only feedback was one generic
sentence about prices/targets/alerts, while the surrounding app appeared to lose
data — "Total unknown", "Identity unresolved", every assessment "Historical",
every observation "invalidated · withdrawn", the title still saying "mint" —
without a single "because you corrected the dial" anywhere. The very thing S5 asks
them to verify (the appended lineage entry, nothing overwritten) sat below the
fold under "Correction history and provenance" with entries headed "Identity
corrected · required". In short: the honesty machinery worked perfectly and
presented as either nothing happening or data being lost, in vocabulary
(withdrawn, invalidated, requalification, withhold qualification, "Intended …")
that assumes the model the buyer hasn't learned yet.

## 5. Boundaries

- Docs only; no code changed, no fixes implemented (proposals in §3) — at
  diagnosis time. §6 records the fixes applied later the same day.
- My fixture only (port 8897, started and stopped by me; guard receipt
  `blocked_edges=[]`); the buyer's live session (8896) and ports 8893–8895 were
  never contacted; `~/.local/state/pricerecon/watch-pilot-2026-10-28.consumed` not
  touched. Zero outbound maintained.
- This session establishes offline human-comprehension findings and fixture-scope
  behavior only — the kit's "Do not conclude" gates (§4 of the kit) stand.
- Minor UI bugs noticed and reported, not fixed: doubled "Total unknown — Total
  unknown" (F10), raw enum leaks ("required", "supported"), inconsistent card/hero
  caution punctuation, casing mismatch in lineage values ("salmon → Blue").
- `python3 scripts/check_public_markers.py` passes; `git diff --check` clean.

## 6. Clarity fixes applied — 2026-11-02

The ranked fixes from §3 were implemented on this branch (commits `8b44edb`,
`3403df7`, `ddb49af`, plus this addendum), presentation-only, TDD red-first
(`CorrectionFormClarity.test.jsx`, `CorrectionFlowClarity.test.jsx`; updated
copy assertions in `IdentityCorrection.test.ts`, `ProductFlow.test.jsx`,
`DiscoveryHierarchy.test.ts`; no assertion weakened). Per-fix confirmation:

- **F1 — discoverability.** "Wrong watch details?" links now sit on the feed
  card and the product hero; the correction tab is labelled "Wrong details?"
  (URL param `view=correction` unchanged); the Technical tab opens with "The
  walkthrough guide calls this page the 'technical record'. Details wrong?
  Correct them on the 'Wrong details?' tab." — bridging the kit's "Technical
  record" wording and ending the raw-JSON dead end.
- **F2 — live preview.** "You are changing dial from mint to [live field
  value]", greyed out until a value is chosen; a previously saved value is
  named "Last saved value: …" instead of posing as current. Verified live
  while typing on the fixture.
- **F3 — value picker.** The current recorded value is offered and marked
  ("mint (current)"); the escape hatch is self-describing ("Type another
  value…"); presets remain suggestions, never a closed list ("Presets never
  replace arbitrary persisted values" contract untouched).
- **F4 — outcome feedback.** Post-save summary names each effect *because of*
  the correction — total withheld ("now 'Total unknown' (was GBP 50.10)"),
  each invalidated coupon (kept as a dated record), observations kept
  unchanged in History, each retained target with its £ amount, and the
  appended lineage entry (nothing overwritten) — each with a jump link to
  Costs/History/Tracking and an anchor to the history panel.
- **F5 — vocabulary.** One family across the flow: "kept on record, no longer
  used for pricing" (card, hero, Costs, coupons, history panel, observations);
  precise internal terms (`invalidated`, `withdrawn`, `requalification`,
  identity_state, coupon state/applicability) remain available as `title`
  tooltips. "Identity corrected · required" → "Corrected — waiting for fresh
  evidence"; the bare "supported" paragraph → "Coupon applicability: supported
  at observation"; card/hero caution copy is now one identical string.
- **F6 — form labels.** "What's wrong?" / "What should it be?" / "How sure are
  you?" ("It's fixed — re-check prices" / "Not sure — pause buying
  qualification"); the "Correction state" wrapper heading is gone; the history
  panel leads with only the changed field ("dial: mint → salmon") and keeps
  the nine-field intended configuration behind a "Show full intended
  configuration" disclosure; the needs list gets a "Waiting for:" lead-in.
- **F7 — reason mechanics.** Label "Reason (recorded with your name in the
  correction history)"; required selects start at "Choose a reason…" with no
  "Not set" option anywhere on a required select (browser validation now has
  an honest surface); custom escape hatch "Write your own reason…".
- **F8 — button and timing.** Button "Save correction — old prices will be
  withdrawn"; the pre-form consequence paragraph is gone — consequence copy
  appears only once a value is pending, and restores the missing promise
  (D-6): "Saving records your correction; it does not fetch new prices."
- **F9 — post-correction card/hero.** "Details corrected (dial mint → salmon)
  · old prices kept on record, no longer used for pricing · awaiting fresh
  evidence"; corrected value shown beside the retained reported title ("dial:
  salmon (was: mint, as listed)"); "Identity unresolved — awaiting fresh
  evidence"; the tracking editor under a retained target reads "Your saved
  target is retained. Alerts wait for fresh evidence for the corrected
  watch." instead of "Exact identity must be resolved before starting exact
  tracking."
- **F10 — minor.** Retained observations auto-load (no button) with caption
  "Retained price observations — kept unchanged, never overwritten" and human
  status ("withdrawn after correction — kept on record"); doubled "Total
  unknown — Total unknown" fixed in Costs **and** (found during this walk) in
  the hero state sentence; bare enum paragraphs replaced.

Copy deviations from §3's proposals, with reasons:

- The F4 summary omits the observation count ("6 old observations"): the
  count lives in the History API, and fetching it from the save path would
  couple the form to a second endpoint for a number the History link shows
  immediately. The line names the mechanism ("kept, unchanged, in History").
- F5's canonical phrase replaces "withdrawn" in state descriptions, so F9's
  banner says "old prices kept on record, no longer used for pricing" rather
  than the proposal's "old prices withdrawn to History" — same information,
  one vocabulary (History is still named via the F4 link and the card's
  discovery-specs line). The F8 button keeps the proposal's exact wording
  "old prices will be withdrawn" (a warning, not a state description).
- With two corrections on one field the card/hero banner lists both lineage
  steps ("dial mint → salmon · dial salmon → Blue") — verbose but accurate;
  no fix proposed for multi-entry banners in the diagnosis.

### Post-fix S5 walk (fresh fixture, port 8897)

Same recipe as §"Fresh fixture": frontend rebuilt in this worktree, fixture
`ticket12-connected-ui-v1`, id `c45a312c4a9146a38c406928418f28d9`,
`temporary_storage=true`, `automatic_checks=false`, marker gate clean before
and after; steps `baseline → cross → duplicate → drop → costs → coupon`
through the run-bound conductor (clock 12:00:36Z → 12:04:48Z); targets saved
through the UI first (Addiesdive £60 + webhook, Casio £40). Headless Chrome
session `s5fix-8897`, loopback only. One environment note: the diagnosis
session's Python venv no longer existed, so the fixture environment was
rebuilt offline from the local pip wheel cache (no network; the fixture
stayed zero-outbound, `blocked_edges=[]` at start and in the shutdown guard
receipt, `notifications_sent=3`, captured transport only).

Correction #1 through the UI exactly as I1 asks: Wrong details? tab → dial →
"Type another value…" → `salmon` → reason preset "The selected variation
differs from this watch." → name → **Save correction — old prices will be
withdrawn**. Correction #2 (dial → `Blue`, reason "The source description
conflicts with the watch shown.") to re-prove append-only lineage.

- **Behavioral verdict: PASS, unchanged.** Total `public_delivered_total`
  unknown/null (was GBP 50.10); coupon `invalidated` with the historical
  result retained; 8/8 assessments historical; tracking #1 withheld
  (`evidence_invalidated`) with the £60 target retained, Casio £40 untouched;
  6 observations still `dial: mint` with original totals retained and
  `validity: invalidated`; correction revision 2 with lineage `mint → salmon`
  (prev None) **and** `salmon → Blue` (prev #1's id) — append-only, actor/
  rationale/time on both; `original_configuration.dial` still `mint`.
- **Presentation verdict: every §3 fix observable.** Preview live while
  typing ("You are changing dial from mint to salmon"); "Last saved value:
  salmon." on the second correction before saving; the F4 summary rendered
  verbatim after both saves; feed card and hero show "Details corrected
  (dial mint → salmon · dial salmon → Blue) · old prices kept on record, no
  longer used for pricing · awaiting fresh evidence" with "dial: salmon (was:
  mint, as listed)"; Costs shows "Total unknown" once, "Historical cost —
  kept on record, no longer used for pricing.", "Synthetic TEN opportunity:
  Invalidated — kept on record…", "Coupon applicability: supported at
  observation", "Historical coupon result — kept on record…"; History's
  retained-observation table is on screen without a click; Tracking shows
  "Alert withheld · target £60 delivered", "Evidence corrected — kept on
  record, no longer used for alerts · target retained", "Your saved target is
  retained."; Technical carries the pointer line. Screenshots retained at
  `/tmp/s5fix-{before-save,after-save,final-correction,final-feed}.png`.
- Browser validation correctly blocked an incomplete submit during the walk
  (empty required name) — the F7 "trap" fix behaving as intended.

Verification: `npx vitest run` 109/109 green (95 baseline-equivalent + 14 new);
`npm run build --prefix frontend` clean (tsc + vite); `python3
scripts/check_public_markers.py` passes; `git diff --check` clean. No backend,
API, parser or test-logic changes beyond the copy surfaces above; the
correction payload (`field/value/actor/rationale/state`) is byte-identical.
This addendum cross-references the buyer-session record on branch
`t3/buyer-session-2026-11-02` (`docs/testing/buyer-session-2026-11-02.md`,
untouched — it lives on that branch). The kit's "Do not conclude" gates
(§4) still stand: this is offline fixture-scope presentation work only.
