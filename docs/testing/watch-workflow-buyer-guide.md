# Parent-run buyer walkthrough: synthetic watch workflow

**Feedback received; acceptance incomplete.** The buyer interview on 2026-10-28
identified a blocking visual-discovery problem. See the [research synthesis](../product/category-discovery/buyer-research-2026-10-28.md).
Further task-level testing is required. The screenshots and automated pass remain review aids; task-level buyer
acceptance must be established separately.
Ticket12 remains open for follow-up design, retesting and acceptance/closure. The
[final two-axis review and verified repairs](watch-final-review.md) are complete.

This is the implemented application running against invented watch evidence in
temporary SQLite. It has no production data, live collection, merchant sessions,
accounts or real notification transport. All five names remain in the feed;
Militado and Merkur remain unresolved. The default private mode displays original remote
Casio, Addiesdive mint, ML05 blue and San Martin review images. ML05B and San Martin
target configurations remain unresolved; Merkur retains an explicit missing image. See the
[image rights and missing-case record](../../tests/fixtures/watch-images/README.md).
The real photo never qualifies the synthetic price or merchant configuration. Positive dimensions and prices are fictional test inputs.

Start a fresh fixture after building this revision. Earlier running sessions and
retained screenshots predate the real-photo assets and do not prove this revision.

## Launch safely

Use the retained integration checkout below. The implementation worktree is
historical provenance and may be removed after its committed history is merged. Build first, with no fixture running. The implementer linked only
this worktree's `frontend/node_modules` to the existing integration dependencies;
no packages or browsers were installed.

```sh
cd /Users/jay/.t3/worktrees/pricerecon/watch-category-integration
env -i PATH=/Users/jay/.nvm/versions/node/v24.14.1/bin:/usr/bin:/bin \
  npm --prefix frontend run build
```

After the build finishes, run in the same directory:

```sh
env -i PATH=/Users/jay/.nvm/versions/node/v24.14.1/bin:/usr/bin:/bin \
  PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PWD/src:$PWD" \
  /Users/jay/.t3/worktrees/pricerecon/t3-7260bb2e/.venv/bin/python \
  -m tests.monitoring.discovery_ui_server --workflow --port 8892
```

Wait for `OFFLINE_UI_READY`. Open **http://127.0.0.1:8892/discover?walkthrough=ticket12** in a clean
local browser session. Before edits, the parent must verify
`http://127.0.0.1:8892/api/offline-verification` returns fixture
`ticket12-connected-ui-v1`, `temporary_storage=true`, `automatic_checks=false`,
`blocked_edges=[]` and zero initial notifications. Also check `images` identifies
`ticket12-private-images-v1`. The image manifest at `/api/offline-watch-images`
lists two registered local Casio files for the optional local-only mode.
`?walkthrough=ticket12` displays original remote URLs directly (outbound browser
image requests, no backend proxy/download). `?walkthrough=ticket12-local` selects
the old local-only resolver, which withholds unmapped images even on failure.
The query flag does not activate collection or change qualification. If the port is occupied or the
marker differs, stop; do not use an existing backend as a fallback. The fixture
binds only 127.0.0.1; outbound application edges stay audit-guarded. Source links are attribution/reference
context; prices seen there must not be blended into this synthetic walkthrough.

The parent advances deterministic time/prices between buyer tasks, from a second
terminal in the same directory. This helper verifies the fixture marker and
per-run identity before posting a bounded fixture action:

```sh
env -i PATH=/Users/jay/.nvm/versions/node/v24.14.1/bin:/usr/bin:/bin \
  PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PWD/src:$PWD" \
  /Users/jay/.t3/worktrees/pricerecon/t3-7260bb2e/.venv/bin/python \
  -m tests.monitoring.watch_workflow_ui --port 8892 --step baseline
```

Replace only the final step name with `cross`, `duplicate`, `drop`, `costs`,
`coupon` or `stale` as directed below. Reload the buyer page after each step.
These controls are test-only endpoints; there is no production collection HTTP
action. They send only to captured transports. Clicking Track alone does not
start polling. Ctrl-C stops the fixture, prints its final guard receipt and removes
its temporary database. Starting again gives a fresh five-case seed; there is no
persisted buyer state to clean from another checkout.

## Image retest scope

This is a private personal session for Jay, not a publishable asset pack. The
Casio card uses its original manufacturer URL in remote mode. Addiesdive displays
the Mint Green reference; Militado shows original ML05 blue VH31 with the unresolved
ML05B warning; San Martin shows the 39mm blue review reference with target warning.
Each remote reference has attribution, original image and source-context links.
No licence, merchant selection or payable-price claim follows. Merkur has no
identified original image and stays missing; no salmon substitute is used.
Remote servers can refuse requests or disappear: load errors show the unavailable
placeholder while retaining reference context. Optional local-only mode retains
the two Casio views and blocks all other remote requests.
The parent can now retest visual interest across the four references and verify
that unresolved configurations and synthetic/unknown delivered totals are understood.
Record the buyer's words. Do not mark five-case visual browsing accepted
without task-level buyer feedback. Retest desktop/narrow layout, load failure and
keyboard interaction with the buyer; this revision has build/static UI/API proof,
not a new browser session. Earlier screenshot receipts remain historical only.

## Walkthrough tasks and expected observations

Let the buyer describe what they understand before explaining the expected state.
Record their actual words, confusions and preferences; do not fill the feedback
form with automated observations.

1. **Discover and edit preferences.** Find the five watch cases without changing
   the saved Watch queue. Set compact 38mm, colourful mint/salmon and delivered
   budget £150, then reload. Try 375px width as well as 1280px. Militado/Merkur
   dimensions stay unknown; a £1 item lead does not satisfy a delivered budget.
   Ask what the buyer believes is known about fit, price and source coverage.
2. **Explain payable and benefits.** Expand Addiesdive's Price and evidence and
   Delivered cost scenarios. Initial base payable is £70.10: item£68 plus£2.10
   shipping, with quoted VAT already included. Cashback£10 is conditional and
   excluded from payable. There is no ordinary-price or savings claim. Ask the
   buyer which amount they would need to pay and what remains conditional.
3. **Track and see meaningful price changes.** Save an Addiesdive delivered target
   of £60; optionally choose webhook to inspect **captured** delivery records.
   Parent runs `baseline` **after target creation**, then `cross`, `duplicate`,
   `drop`, reloading each time. Baseline£70.10 is above target;£58.10 crosses;
   duplicate£58.10 sends nothing extra;£56.10 is a further drop. With webhook
   selected the marker shows0/1/1/2 captured sends. No actual webhook is sent.
   Ask what would make a target alert eligible and whether the explanation is clear.
4. **Inspect uncertain costs, coupon and scope.** Before changing Addiesdive's
   identity, parent runs `costs`: San Martin moves from a selected-dial trap,
   through missing shipping, to a conditional regional quote; Casio shows an
   evidenced synthetic FX path. Parent then runs `coupon`. Addiesdive's base
   stays £50.10; the separately reproduced synthetic public receipt is £45.10.
   The scoped comparison/dated observed low can show£45.10 while the default
   no-coupon target uses£50.10. Usual and personal prices remain unavailable,
   savings absent. Expand coverage: sixteen source lanes, unchecked real routes
   and synthetic dates do not establish a complete market or a usual price.
   Ask the buyer to explain current-best versus dated-low versus usual price.
5. **Correct identity and inspect consequences.** Open **Wrong watch details?**. Correct Addiesdive dial from
   mint to salmon with an attributed rationale. Reload. Target£60 remains;
   prior prices/coupon/assessments are historical or withdrawn; alerts are withheld
   until independent fresh compatible evidence exists. Expand original evidence
   and history: original mint observations were not relabelled salmon. Repeat
   keyboard interaction at both widths. Ask what they expect the app to do next.
6. **Discuss freshness and errors.** Parent runs `stale`, which advances the
   controlled clock three hours without collecting anything. Reload and inspect
   withholding/age. The retained conflict screenshots show an actual API409
   rendered by the UI, followed by reload and resolution. Ask whether stale,
   disputed, outside-preference and above-target states are distinguishable and
   what additional explanation/noise control they would need.

The automated browser driver additionally exercises an actual competing correction
writer, a rejected stale form, and reload/resolution. To reproduce that entire
script against a **fresh** fixture (it changes the temporary buyer state), use:

```sh
/Users/jay/.t3/worktrees/pricerecon/t3-7260bb2e/.venv/bin/python \
  -m tests.monitoring.watch_workflow_browser --port 8892 \
  --artifacts "$PWD/docs/testing/artifacts/watch-workflow/browser"
```

This uses installed Chrome and agent-browser, a unique owned session, and
`--allowed-domains 127.0.0.1`; it closes its browser in `finally`. The installed
agent-browser lacks the newer skill's `skills get core` command; its installed
`--help` and the retained drivers were used, with no install/update.

## Review images

All images are actual implemented UI screenshots, opened and inspected by the
implementer. Dense evidence panels scroll; the buyer must judge their usability.
They are not mockups or live merchant screenshots.

| Topic | Desktop 1280×900 | Narrow 375×812 |
| --- | --- | --- |
| Feed | [Feed](artifacts/watch-workflow/browser/desktop-feed.png) | [Feed](artifacts/watch-workflow/browser/narrow-feed.png) |
| Preferences | [Editable interpretations](artifacts/watch-workflow/browser/desktop-preferences.png) | [Persisted edits](artifacts/watch-workflow/browser/narrow-preferences.png) |
| Payable/benefits | [VAT and payable](artifacts/watch-workflow/browser/desktop-prices.png), [cashback](artifacts/watch-workflow/browser/desktop-cashback.png) | [Cashback excluded](artifacts/watch-workflow/browser/narrow-cashback.png) |
| Conditional shipping | [Conditional quote](artifacts/watch-workflow/browser/desktop-conditional.png) | [Conditional quote](artifacts/watch-workflow/browser/narrow-conditional.png) |
| Target | [Qualifying further drop](artifacts/watch-workflow/browser/desktop-tracking.png) | [Edited intent retained/staged](artifacts/watch-workflow/browser/narrow-tracking.png) |
| Price claims | [Scoped assessment](artifacts/watch-workflow/browser/desktop-assessments.png) | [Dated low/missing baseline](artifacts/watch-workflow/browser/narrow-prices.png) |
| Coverage | [Sources/gaps](artifacts/watch-workflow/browser/desktop-coverage.png) | [Sources/gaps](artifacts/watch-workflow/browser/narrow-coverage.png) |
| Correction | [Lineage and resolution](artifacts/watch-workflow/browser/desktop-correction.png) | [Saved correction](artifacts/watch-workflow/browser/narrow-correction.png) |
| Error | [Stale writer conflict](artifacts/watch-workflow/browser/desktop-error.png) | [Stale writer conflict](artifacts/watch-workflow/browser/narrow-error.png) |

## Feedback record for the parent

Status: **research interview conducted 2026-10-28; full walkthrough acceptance incomplete**.
The initial interview could not assess visual appeal without meaningful images.
On 2026-10-28, after the real-Casio-photo private walkthrough was presented, the
buyer replied “looks good”. This is positive feedback on that bounded image
slice; four missing image cases and other task-specific outcomes remain open. Preserve the
interview [findings](../product/category-discovery/buyer-research-2026-10-28.md) and
record future task completion, viewport and assistance explicitly.

| Task | Buyer explanation / difficulty / requested change | Acceptance decision |
| --- | --- | --- |
| Casio private image slice | Buyer: “looks good” after walkthrough link; viewport/task details not reported | Positive visual feedback; bounded scope |
| Payable versus conditional/cashback | Task outcome not yet established | Pending |
| Missing baseline/current-best/dated-low | Task outcome not yet established | Pending |
| Source coverage and age | Task outcome not yet established | Pending |
| Preferences and unknown dimensions | Requests fuzzy search, brand/category facets and similarity; visual-first browsing blocked without meaningful images | Follow-up needed |
| Correction and preserved target | Buyer: “What correcting the dial changes” was unclear; later rejected the added text as overwhelming; progressive disclosure repair implemented | Pending buyer retest |
| Alert eligibility/noise and errors | Wants target/restock/significant-bargain alerts and configurable in-app/Telegram/Discord routing; live UI task not confirmed | Follow-up needed |
| Desktop/narrow/keyboard usability | Task outcome not yet established | Pending |

The parent owns feedback, acceptance/closure, final Standards-versus-Spec review
and later cleanup. No live access/retention/freshness/budget/ownership/migration or
activation gate is resolved by this walkthrough.

The initial interview is requirements/usability feedback, not completed acceptance
of all rows above. The unchanged “Pending” rows mean task-level outcomes were not
established, rather than that no buyer conversation occurred.


## Buyer walkthrough feedback — 2026-10-28, remote-image revision

After the parent proposed three checks, the buyer replied:
1. “confirm” to editing preferences and persistence after reload — confirmed.
2. “GBP 70.10” to the tracking demonstration — observed current displayed price;
   saving a GBP60 target and crossing/deduplication are not yet confirmed.
3. “this is not clear”, subsequently specified as “What correcting the dial changes”.
   The reported confusion concerns correction consequences; costs were not reported unclear.

Do not treat this as complete task acceptance. Ticket12 stays open; preserve the
positive visual feedback and the newly confirmed preference/reload result.


## Correction clarity repair — 2026-10-28; buyer retest pending

The parent explained that correction repairs an erroneous watch match (for example,
mint recorded when salmon was intended). Old mint prices do not prove a salmon
price; the saved target stays and price alerts pause until fresh matching evidence.
The UI now puts a labelled example and these buying consequences before the form,
distinguishes correction from choosing a shop option or editing a photo, and explains
withdrawn evidence and the saved state in plain language. Saving promises no new
price, immediate source refresh or reference-image change. Current/original and
intended values and all invalidation behavior remain unchanged.

Verification: focused rendered React component regression failed on the old copy
and passed after the repair; saved withdrawn-state rendering is also covered.
All 57 frontend tests, TypeScript/production build, 27 existing guarded public
application correction regressions and `git diff --check` passed. The build retains
its bundle-size advisory. Integration base: `a532ef7774ce6330e491d02ae333ce379317a712`.
No browser, server, live source or account was used. Parent must retest whether the
buyer understands the correction before and after saving; ticket12 remains open.
Preferences/reload are confirmed and GBP70.10 was observed, but target creation,
price crossing and complete workflow acceptance are not established by that feedback.


## Sole merger correction clarity review — 2026-10-28

Candidate `293841168d0c312a785edb2345d6188b521657b7` from
`/Users/jay/.t3/worktrees/pricerecon/t3-c513f13d` was reviewed against integration
base `a532ef7774ce6330e491d02ae333ce379317a712` and merged with `--no-ff` as
`bef526372a008d21eae3b35245da79caf62ee8a7`.

Standards review: zero blockers against `CONTRIBUTING.md` and
`docs/engineering-standard.md`. The narrow diff introduces no unchecked escape
hatches or behavior changes; rendered component regressions cover the copy.
Spec review: zero blockers against ticket12, this guide and the explicit repair
brief. Copy distinguishes an app's wrong watch match from shop selection/photo
editing; original prices/coupons/assessments remain history, withdrawn from the
corrected watch; target stays and alerts pause pending fresh matching evidence.
Blue/green is explicitly an example, not a claim about the active fixture.
The buyer clarified correction consequences; costs were not reported unclear.

Independent checks (all passed):
- Candidate and merged checkout: Node 24 `npm --prefix frontend test -- --run src/components/__tests__/IdentityCorrection.test.ts` (2 tests each).
- Merged checkout: Node 24 `frontend/node_modules/.bin/tsc --project frontend/tsconfig.json --noEmit`.
- Candidate: `git diff --check a532ef7...HEAD`.
- Merged checkout: `git diff --exit-code 293841168d0c312a785edb2345d6188b521657b7 HEAD` (exact tree equality) and `git diff --check a532ef7..HEAD`.

The implementer's reported 57 frontend tests, 27 guarded correction regressions
and production build were not independently repeated for this copy-only repair.
No browser/live/network/account/contact/push/PR or sibling mutation occurred.
Integration was clean before merge and after merged checks. Parent owns fixture
restart, candidate-worktree cleanup and actual buyer retest before/after saving.
**Ticket12 remains open; actual buyer comprehension and full acceptance are pending.**


## Information overload repair — 2026-10-28; retest pending

Actual follow-up: “It's just too much text, i cant comprehend it all”. The earlier
explanation additions did not establish comprehension. The default feed now puts
images/title, short payable state, supported size/movement/material and tracking
first. Source coverage, collection/capture context, image provenance and technical
evidence use closed native details. Unknown/conditional/observation-verified totals,
identity gaps, withdrawn prices and stale alert evidence remain visible when material.

Parent retest: let the buyer browse first, then choose one watch and inspect price
or specs only as needed. Open **Wrong watch details?** only for a correction task:
“Old prices stop applying. Your target stays; alerts wait for a matching offer.”
Name and reason remain required; dispute state and history are secondary controls.
Ask the buyer to perform one task at a time; do not precede each task with the old
explanation paragraphs. Record the actual response before advancing. Existing image
and preference confirmations stand; target/correction/full acceptance remain pending.

Verification: 61 frontend tests and production build pass (existing bundle-size
advisory); rendered tests cover closed controls and all three payable states.
No backend/API behavior changed, so no guarded API regressions were rerun. No
browser/server/live/account/network actions were performed. Narrow CSS and native
keyboard controls have source/rendered proof only; parent owns actual walkthrough.


## Sole merger visual-first review — 2026-10-28

Candidate `9d3a5db31ab4374e184e346d814deb86820b0379`, checkout
`/Users/jay/.t3/worktrees/pricerecon/t3-7a0a4f50`, reviewed against expected
integration `907c9625ed696777891998507a0e01bef76c7cc7`; merged with `--no-ff`
as `6597cc4a894ac7ad836f3addda36f340001fab24`.

Standards: zero blockers against CONTRIBUTING.md and docs/engineering-standard.md.
No new unchecked escapes, source boundaries or backend changes. Native details
and rendered regressions provide bounded presentation proof.
Spec: zero blockers against the latest buyer guide, ticket12 and overload brief.
Default copy is substantially reduced around image/title/price, supported essential
specs and Track. Evidence and attribution remain accessible in native details;
material unknown/conditional, withdrawn and stale states remain visible. One
Wrong watch details? path retains required, empty-by-default actor/rationale,
original/intended values and dispute/history controls. Exact-target save behavior
and correction payloads are unchanged. Synthetic buying evidence is labelled once
at session level; unresolved/reference image labels remain accessible.

Independent candidate checks: all 61 frontend tests, TypeScript/production build,
and diff check passed (existing bundle-size advisory). Merged checks: 6 focused
clarity/correction tests, TypeScript noEmit, diff check and exact candidate tree
equality passed before this documentation receipt. Integration was clean before
merge and after checks; no untracked files existed to preserve. Existing receipts
were retained. Backend tests were not repeated for this presentation-only diff.
No browser, server, live/network/account, push, PR or sibling edits performed.
Parent owns cleanup and actual walkthrough refresh. Ticket12 remains open:
buyer comprehension, narrow/keyboard use, target/crossing and full acceptance
remain pending; source/rendered proof is not buyer acceptance.


## Expanded hierarchy follow-up — 2026-10-28; buyer retest pending

Actual buyer feedback: “That's much clearer, i just think the collapsible sections
could use simplifying too. Put the data in hierachical order, make it easy to glance
over and understand.” This is positive feedback on the simplified default, not
acceptance of the remaining tasks or the expanded presentation.

The default image/title/price/specs/tracking layout is retained. The large Price
and evidence accordion is replaced by compact Price breakdown, Watch details,
Price history and Sources disclosures. Expanded facts use responsive label/value
rows; results, conditions and missing data precede detailed evidence. IDs,
revisions, policies, extractor records and lineage sit in deeper Technical evidence
controls. Correction fields precede correction history; required name/reason,
original/intended values, dispute controls and consequences remain available.
Unknown/conditional/observation-verified payable states, withdrawn history,
synthetic warnings, excluded cashback, source gaps and tracking eligibility remain
represented. No totals, specifications or reasons were invented.

Verification: 67 frontend tests passed, including rendered grouping/order,
comparison withdrawal/synthetic warnings, source gaps, cost states/liabilities/
benefits and existing default/correction regressions. TypeScript noEmit,
production build and git diff --check passed; the existing bundle-size advisory
remains. Presentation only: no backend/API behaviour changed, so guarded backend
checks were not rerun. No browser, server, live/network/account, push or PR work.

Parent owns merge and walkthrough refresh. Let the buyer choose a watch, open one
relevant group, and locate the result, conditions and supporting evidence without
a narrated data dump. Expanded comprehension, actual narrow/keyboard usability,
target/crossing, correction and full acceptance remain pending. Ticket12 stays open.


## Sole merger expanded-hierarchy review — 2026-10-28

Candidate `bb054bacf3647e8fa29383ec50f06181e6a30dbe`, checkout
`/Users/jay/.t3/worktrees/pricerecon/t3-a9f0e260`, reviewed against expected
integration `b77e4beba6831ec0e6ccd1a72d19e99d06d4671c`; merged with `--no-ff`
as `26066381b2eaf2a46f5b715733fc8ab7841ab38f`.

Standards: zero blockers against CONTRIBUTING.md and docs/engineering-standard.md.
No new unchecked escapes, backend changes or source-boundary behavior changes.
Spec: zero blockers. Simplified default preserved; expanded groups put results,
conditions and missing data before technical provenance. Unknown, conditional,
withdrawn and observation-only costs, excluded cashback, source gaps, history,
correction/dispute controls and original evidence remain accessible. No fabricated
values found. Native details/summary semantics, focus-visible rules and heading
nesting have no obvious source-level regression; responsive rows stack below
480px. Rendered tests provide bounded markup proof, not actual keyboard/mobile QA.

Independent candidate checks: 67 frontend tests across 6 files, TypeScript noEmit,
production build and diff check passed. Existing bundle-size advisory remains.
Merge tree exactly equals candidate tree before this receipt; merge diff check
passed. Integration started clean with no untracked files; prior receipt contents
were preserved. Backend tests were not repeated for this presentation-only change.
No browser, preview, server, network/live/account, push, PR or sibling edits.

Ticket12 remains open, pending buyer retest of expanded comprehension, actual
narrow/keyboard use, target/crossing, correction and complete acceptance. Parent
owns worktree cleanup and rebuilding the running walkthrough. Source/rendered
proof does not establish buyer acceptance.
