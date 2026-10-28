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
5. **Correct identity and inspect consequences.** Correct Addiesdive dial from
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
| Correction and preserved target | Buyer: “What correcting the dial changes” was unclear; copy repair implemented | Pending buyer retest |
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
