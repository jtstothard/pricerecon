# S5/F5 clarity residuals — implementation receipt (2026-11-02)

Agent-only presentation work from `origin/main` @ `fd2fe49`. The existing Discovery React and API-fixture interfaces are unchanged; no correction payload, invalidation behavior, dependency, or WatchForm change is included.

Each residual was implemented as a separate red→green slice in `CorrectionFlowClarity.test.jsx`: the focused test failed on the original rendering, then passed after its presentation change.

- Card target state: “alert withheld” plus retained-evidence wording; technical state and reasons remain in a tooltip.
- Costs/F5 leftovers: the named cost, coupon, freshness and charge-state codes have buyer wording and technical tooltips.
- Repeated corrections: card and hero show one current value per field from the original observation; full lineage remains in correction history.
- Tracking retained values: original observations and corrected details are separately labelled.
- History: assessment blocks explain correction-driven invalidation and retain technical reasons in a tooltip.
- Feed: candidates render in deterministic title/ID order for normal and reversed fixture responses.

Agent verification on this branch:

- Focused `CorrectionFlowClarity.test.jsx`: 11/11 passed after the slices.
- Full `npx vitest run`: **122/122 passed** across 11 files.
- `npm run build --prefix frontend`: passed; existing chunk-size advisory only.
- `python3 scripts/check_public_markers.py`: passed.
- `git diff --check`: passed.

Scope boundary: deterministic fixture/rendered checks only. No live provider or merchant test, live pilot/discovery activation, browser walkthrough, or deployed-system access was performed. This receipt records agent verification, **not new human comprehension or buyer acceptance**; the historical S5 receipts are unchanged.

## Independent review fixes — 2026-11-02

Rebased first onto `origin/main` @ `b0f7e95`; final verification below was repeated after rebasing onto newer main @ `b1c9029` and restoring its lockfile with `npm ci --offline`. Seven review findings each received red-first regression coverage at the existing component/API-fixture seams:

1. Disputed corrections no longer render as established corrections on the card, Costs, History, or Tracking; mixed journals use neutral “changed” wording.
2. Current-value summaries follow `previous_correction_id` within each `configuration_id` journal, independent of array order; independent journals never collapse together and retained history remains complete.
3. Missing data has exactly one terminal period in rendered DOM text.
4. Overview shares the Costs missing-data gloss and tooltip.
5. Card and detailed tracking share `trackingStateLabel` for eligible, above-target, and withheld states.
6. Cost and charge tooltips use the established `Technical state: …` prefix.
7. Tracking renders the matching journal's `original_configuration`, tested through `ProductContent` with a reversed repeated-correction fixture and a latest-value `candidate.configurations` entry.

Review-fix verification:

- Focused `CorrectionFlowClarity.test.jsx`: **17/17 passed**.
- Full `npx vitest run`: **129/129 passed** across 12 files.
- `npm run build --prefix frontend`: passed; existing chunk-size advisory only.

These remain agent-executed deterministic checks, not buyer acceptance or live-source evidence.

## Second independent review fixes — 2026-11-03

Four further findings were implemented from the PR head `3723c58`, each with regression coverage written and run red on the unfixed code first (three tests carried over from an interrupted worker were re-verified red before any production edit). No API, payload, backend, lineage, WatchForm or dependency change; historical receipts are unchanged.

1. **Neutral retained-evidence wording.** `TrackingStatus` now says “Prior evidence no longer applies — kept on record, no longer used for alerts · target retained” instead of “Evidence corrected …”, so disputed saves and a bare `evidence_revision_withdrawn` are not described as corrections. The post-save outcome in `IdentityCorrection` now says “alerts wait for fresh evidence for this watch”. Tests assert the complete phrases at `TrackingStatus`, `ProductContent` (Tracking) and a real form-submit of a disputed save.
2. **Missing data punctuation.** Entries drop their own terminal period, are joined by “; ”, and the list ends with exactly one “.” in Overview and Costs. Multi-entry tests put a glossed entry in the middle, an unmapped entry last (one with its own trailing period), and a glossed entry last.
3. **Technical-state convention.** Historical-assessment tooltips read `Technical state: historical; reasons: …` instead of `Technical reasons: …`. The existing assertion that encoded the old title was updated accordingly.
4. **Mixed corrected+disputed journal.** The correction-tab heading now uses the shared `correctionPresentationState` over the journal's current values, so it reads “Changed” on a mixed journal like the card (“Details changed”), hero and Tracking (“Changed details”). Per-entry `(corrected)` / `(disputed)` states in the history list are unchanged. One test covers all four surfaces through the real components.

Two earlier markup-fragment assertions that included the final period of the Freshness gloss now assert the phrase without it, because the period is rendered once for the whole list; the rendered-text tests assert the period.

Agent verification (run sequentially):

- Focused `CorrectionFlowClarity.test.jsx` + `CorrectionFormClarity.test.jsx`: **31/31 passed**.
- Full `npx vitest run`: **135/135 passed** across 12 files.
- `npm run build --prefix frontend`: passed; existing chunk-size advisory only.
- `python3 scripts/check_public_markers.py`: passed.
- `git diff --check`: passed.

These remain agent-executed deterministic checks, not buyer acceptance or live-source evidence.
