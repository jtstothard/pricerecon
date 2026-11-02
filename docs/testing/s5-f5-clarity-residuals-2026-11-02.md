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
