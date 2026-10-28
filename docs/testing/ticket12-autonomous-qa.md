# Ticket12 delegated browser acceptance — 2026-10-28

Base: `a8b1599e8c45cf19fa820ea5096bc671c76a8272`, isolated branch
`t3/ticket12-browser-qa`, checkout `/Users/jay/.t3/worktrees/pricerecon/t3-b645c5ab`.
Integration was fast-forwarded before work and checked again before handoff;
the integration checkout was not modified. Parent owns independent review/merge.

Authority: buyer explicitly delegated remaining checks: “keep going doing all the
checks yourself”, including browser QA and controlled fixture changes. This
supersedes the historical requirement for the buyer personally to perform each
keyboard task. It does not turn agent observations into human comprehension feedback.

Prior actual feedback is separate: buyer approved preferences/reload, then the
refined product design with “Much better, use that” (presented integration
`914a1a6f12e5367b9529ffaa3483e5ba1d4df1ac`). Buyer saved target £60; parent
demonstrated baseline/cross/repeat and authorized mint-to-salmon correction in
run `e94f6a6651dd49d788aafe9ac415c6fa`. Those are historical parent/buyer
observations, not this agent's UI actions. No new buyer quotations were invented.

## Expected and observed

| Check | Expected | Observed |
| --- | --- | --- |
| Build and frontend | Types/build and current 86 tests pass | Passed before and after CSS repair; existing large bundle advisory |
| Guarded regressions | Normal API/execution with marked temporary SQLite | 50 passed: watch, tracking, correction and discovery modules; includes rise/re-cross and stale/replayed evidence controls |
| Viewports | Actual CSS 1280×900 and 375×812, no horizontal overflow | All six Addiesdive flat product views: document and content scroll widths equal viewport/client widths; comparison and preferences fit both widths |
| Visual review | Preserve approved design, readable evidence | Inspected comparison and all 12 final product screenshots; repaired Technical attribution contrast only |
| Desktop preferences | Preset and custom values save/reload | 38mm/£150 presets and mint, salmon custom persisted; 37.5 custom accepted |
| Narrow preferences | Arbitrary values persist, keyboard submit | 37.5mm, mint/salmon, £150 saved with Tab/Enter and survived full route reload |
| Tracking | Save exact £60 target and selected captured webhook | Saved by real Tab/Space/Enter at desktop, repeated at narrow width; preserved after correction/reload |
| Captured alerts | Baseline/cross/repeat/further drop sends 0/1/1/2 | Exact expected counts, no blocked edges; API fixture steps used normal execution seam |
| Keyboard navigation | Visible focus and Enter selects peer sections | Narrow Costs→History→Tracking→Correction→Technical traversal passed with 3px Iris focus; desktop preference/target controls also passed |
| Direct/back context | Direct product reload and back preserve walkthrough | All six direct routes render; Back to comparison retains `walkthrough=ticket12` |
| Four remote images | Original remote requests load; no qualification inference | Militado, Casio, San Martin and Addiesdive image elements complete with naturalWidth >0; browser network entries HTTP200 |
| Image failure | Real decode error yields placeholder | Replaced owned QA hero image src with invalid data bytes; React error handler displayed explicit unavailable placeholder; reload restored source |
| Missing/conditional costs | Unknown distinct from conditional and cashback | Unresolved candidates show Total unknown; San Martin costs step shows Conditional shipping; Addiesdive £70.10 payable excludes conditional £10 cashback |
| Coupon/history | Synthetic public coupon separate from no-coupon target | Coupon fixture action succeeded; loaded retained history after correction shows original observations invalidated/withdrawn; usual price and savings unavailable |
| Correction | Attributed custom salmon invalidates old claims, retains intent | Narrow form saved via Tab/Enter; original mint and intended salmon shown separately, public total unknown, £60 target withheld and salmon intended_values retained in API |
| Freshness | Controlled three-hour advance never creates fresh evidence | Stale step succeeded; corrected evidence remains withdrawn, no last-good evidence/current availability claim |

Evidence: [browser receipt](artifacts/ticket12-autonomous/browser-receipt.json),
[alert steps](artifacts/ticket12-autonomous/alert-steps.json), build/frontend/guarded
logs and final screenshots alongside them. Narrow screenshots are 750×1624 device
pixels at device scale 2; measured CSS viewport is 375×812. No emulated phone UA
or physical-device claim follows.

## Defect and regression

Technical hides the duplicate image and removes its pale figure background, but
inherited caption `#29414f` remained dark. Actual browser readback and
`1280-technical.png` reproduced unreadable attribution before editing. The narrow
product-only selector now uses existing `--text-secondary`, 14px text and left
alignment. Browser computed colour is now `rgb(203, 213, 225)`; both final
Technical screenshots were inspected. The retained `technical-caption-check.js`
assertion passes in the rebuilt Technical route. No API, design hierarchy,
qualification, source connector, dependency or lockfile changed.

## Containment and disposition

Own T3 preview tab only: `tab_u_03e9b6a7-411b-479d-83a4-d3868ed829e9`.
Port8895 and the parent's tab were not mutated. Initial own-tab GET on8895 was
read-only; all changes used8897. First own fixture run
`b83029f140eb45e5ab0255004dc34aec` produced captured alerts and was stopped
before rebuilding. Fresh rebuilt run `9f867996c0474c759a46a1746afcf254`
handled final views/costs/coupon/correction/preferences. Both used
MonitoringHarness marked temporary SQLite, paused scheduler, controlled time,
controlled connectors and captured notification transports. Both ended with zero
blocked application edges. Remote public browser image loads were authorized.
No production/account/source collection/real notification/push/PR occurred.

Ticket12 is accepted for **offline autonomous technical scope**, using the prior
actual design approval plus explicit delegation of remaining mechanical checks.
Parent independent review/merge remains required. Actual task-by-task buyer
comprehension research is unproven, and is not asserted by this disposition.
Merkur remains an honest unresolved abstention, not a substitute success or an
automatic offline blocker. Source access/rights, real longitudinal history,
usual-price calibration, full market coverage, real freshness, migration,
operating policy and live activation/release remain separate unresolved gates.

Commands: Node24 `npm --prefix frontend ci --offline --ignore-scripts`,
`npm --prefix frontend run build`, `npm --prefix frontend test -- --run`;
shared existing Python environment with clean environment and local PYTHONPATH:
`python -m pytest -q tests/test_watch_workflow.py tests/test_tracking_workflow.py tests/test_correction_workflow.py tests/test_discovery_workflow.py`.
Build/frontend logs have terminal trailing whitespace trimmed; content retained.
Screenshots and receipts have SHA256 manifest. Own preview tab closed and own
fixture stopped with `OFFLINE_UI_STOPPED`; final guard receipt retained. Original
buyer fixture and integration checkout remain untouched.
