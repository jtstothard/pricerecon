# Ticket12 bounded discovery image support — 2026-10-28

Implementation base: integration/watch-category-discovery
`dd43df3a4575c426465fcfcb408d13e3167f4c02`, fast-forwarded into the T3-created
`t3/ticket12-watch-image-support` checkout before edits. Only this isolated
checkout was changed; no integration merge, push, PR, source retrieval, account,
production storage, activation, deployment or browser preview was performed.

## Asset inspection and remaining acceptance gate

Inspected tracked raster/vector paths and existing discovery fixtures. Retained
watch images are UI screenshots; the existing feed uses PriceRecon's generic
original SVG placeholder. No retained exact-watch photograph/illustration with
both justified reuse rights and depiction identity was found. Screenshots are
not repurposed as product assets. No named-product depiction was fabricated.

**Meaningful permitted assets and actual buyer visual-first retest remain open.**
This delivery provides a contract/rendering path, not visual buyer acceptance.
No existing connector is newly authorized or taught to acquire images. The
synthetic URLs/metadata in tests prove only contract transport, not assets,
rights, exact real-product identity or successful remote image loading.

## Contract and behavior

`NormalizedListing.discovery_image` is an optional untrusted depiction report.
Normal discovery execution validates it independently, requiring photo or
illustration kind, attribution, provenance, nonblank permission and depiction
references, an explicit exact-watch assertion and matching source listing ID.
The connector/operator supplying a report must justify those references for the
exact depicted selection; this schema does not independently adjudicate rights.
A bare existing `image_url` remains insufficient and ignored for this purpose.

Only unsigned HTTPS image URLs without credentials, whitespace, query or fragment
are admitted. Unsupported, incomplete, unsafe or mismatched reports retain the
buying lead with an explicit generic placeholder. No backend image fetch/proxy
was added. Valid reports persist with the capture and reach the existing feed API.
The feed decoder checks the contract again. The UI labels photographs versus
product illustrations, shows attribution/provenance and permission/identity
references, uses lazy loading and no referrer, and replaces failed loads with an
explicit unavailable-product-image placeholder. Image presence grants no buying,
identity qualification, payable-price, comparison or alert eligibility claims.

## Verification

Approved seams: real API plus normal execution inside the existing fresh-process
MonitoringHarness (marked temporary SQLite, controlled connector/time edges,
paused scheduling, captured notifications); focused UI static rendering tests.
No new seam approval was needed under the dispatch.

TDD: the first API test failed on unsupported `discovery_image`, then passed
through execution, GET feed and session restart. The first UI test failed on the
missing DiscoveryImage module, then passed. Added negative API controls preserve
all eight rejected leads and a valid illustration control; pre-existing bare
unpermitted image URL coverage remains passing.

Commands use the retained project Python environment at
`/Users/jay/.t3/worktrees/pricerecon/t3-7260bb2e/.venv/bin/python` and Node24 at
`/Users/jay/.nvm/versions/node/v24.14.1/bin`. Frontend dependencies were installed
from local npm cache with `npm ci --offline --ignore-scripts`.

- API discovery workflow: 7 passed (photo persistence, illustration and rejection
  controls, existing no-permission fallback and earlier discovery behavior).
- Broader discovery/watch/final-review/correction regression selection: 60 passed
  in 112.67s; see retained `workflows.log`.
- Frontend: 28 tests passed, including photo/illustration/placeholder rendering.
- Frontend build passed; existing large-chunk advisory remains.
- Focused Ruff passed; uncached three-source mypy passed; `git diff --check` passed.

Final integration re-merge reported already up to date at the same full SHA.

[Raw command results](artifacts/watch-images/) are retained. Build and static UI
rendering do not prove browser load-error interaction, narrow layout or keyboard
usability; those and buyer task completion remain retest gates. No full-suite,
live-source, asset-rights or release acceptance claim follows from these passes.

## P1 malformed image repair — 2026-10-28

The merger reproducer showed that `urlsplit` did not validate an unread port:
`https://assets.invalid:999999/control.jpg` persisted as a photo and the browser
URL constructor then rejected the entire feed. Backend validation now applies
Pydantic's HTTP URL grammar and explicitly reads the urllib port, retaining the
existing unsigned HTTPS policy and rejecting backslashes/control characters.
The frontend catches only depiction parsing failures and returns an explicit
unavailable-product-image placeholder; candidate qualification parsing remains
strict outside that boundary.

Red/green receipts are retained under `artifacts/watch-images/repair-*.log`.
The guarded normal execution/API rejection loop failed before the repair and
passed afterward (7 focused workflows), including out-of-range/nonnumeric ports,
backslash host confusion, invalid host escapes and invalid numeric hosts. All
14 leads survive with only the valid illustration admitted; attribution and
permission references survive API/session restart. The existing photo control
also retains its attribution contract. No network/image loading is involved.

The frontend regression uses a minimized synthetic captured feed from the supplied
review fixture (two leads, no source coverage, captures or evidence collections).
Against the original decoder it reports 10 failures and 30 passes; the repaired
decoder passes all 40 tests. Valid photo/illustration attribution survives;
malformed reports cannot escape as photos, and an invalid qualification still
throws. Frontend build passes with the existing large-chunk advisory. Focused
Ruff, uncached three-source mypy and whitespace checks pass. The broader guarded
discovery/watch/final-review/correction selection passed 63 tests in 62.67s. The trailing blank
line in the retained original frontend log was removed.

Ticket12 remains open for meaningful permitted assets and buyer visual-first
retest. These offline controls do not establish rights, actual remote image
loading, browser usability or buyer acceptance. No integration checkout edits,
push, PR, live access, production action or browser run were performed.

Final local merge of `integration/watch-category-discovery` at
`dd43df3a4575c426465fcfcb408d13e3167f4c02` reported already up to date.

## Independent merger recheck and acceptance — 2026-10-28

Reviewed candidate `6741d4aba823d8bfe8b198ac6a435714503511cb` against
`dd43df3a4575c426465fcfcb408d13e3167f4c02` in the clean, pinned candidate
checkout `/Users/jay/.t3/worktrees/pricerecon/t3-e17dc593`. Read this receipt,
the engineering standard and CONTRIBUTING, ticket12 and the 2026-10-28 buyer
research. No delegation, browser, network, live source, account, production,
push or PR work was performed.

**Standards:** zero blocking findings. Depiction validation isolates failures at
the image boundary; no new unchecked typing escape or qualification bypass was
found. Focused Ruff passes. Including `models/listings.py` reports 22 existing
findings; independently linting its base content produces the same 22 findings.
These baseline findings were not silently presented as a clean whole-file pass.

**Spec:** zero blocking findings for this bounded contract/rendering slice.
Valid photo/illustration attribution and identity/permission references persist;
invalid reports preserve leads and valid siblings. The UI labels illustration,
photo and unavailable imagery. No asset or buyer-acceptance claim follows.

Independently reran the supplied `/tmp/pricerecon-image-review/probe.py` with
only its output redirected to `recheck-feed.json`, preserving the original
reproducer/feed. Both leads now publish placeholders. A separate decoder check
against the candidate consumed that API feed successfully, injected malformed
persisted image metadata without losing either lead, and confirmed that setting
`alert_eligible=true` still throws `Unsupported qualified discovery claim`.
The candidate regression controls cover valid photo and illustration metadata,
14-lead API survival/restart, malformed URL cases and strict qualification.

Verification used the retained project Python environment and Node 24.14.1:

- `python -m pytest -q tests/test_discovery_workflow.py tests/test_watch_workflow.py tests/test_final_review_workflow.py tests/test_correction_workflow.py tests/test_correction_target_ownership.py`: **63 passed in 68.03s**.
- `npm test -- --run`: **40 passed**; `npm run build`: passed (includes TypeScript).
- `python -m mypy --no-incremental src/pricerecon/models/discovery_images.py src/pricerecon/models/discovery.py src/pricerecon/core/discovery.py`: three source files passed; existing unused-override note.
- `python -m ruff check src/pricerecon/core/discovery.py src/pricerecon/models/discovery.py src/pricerecon/models/discovery_images.py tests/monitoring/discovery_workflows.py tests/test_discovery_workflow.py`: passed.
- `git diff --check dd43df3...HEAD`: passed.

An initial concurrent build/API run had 62 passes and one import failure when
Vite temporarily removed `frontend/dist/assets`. This was a reviewer scheduling
error, not an image assertion failure. The complete 63-test run above was repeated
after the build finished, with no build or checkout changes during the run.
Candidate HEAD stayed pinned and its tracked/untracked status remained clean.

Merged with `--no-ff` in the initially clean sole integration checkout, creating
`2abafb0b1a630efcde45fe5f5643a6e08f7588ef`, first parent
`dd43df3a4575c426465fcfcb408d13e3167f4c02`, second parent the full candidate SHA.
Merged tree `29370fa0437e27f7922b10008bccb5e5968010dc` exactly equals the
candidate tree (`git diff --exit-code candidate HEAD` passed). On that stable
merged checkout, all seven guarded discovery workflows, all 40 frontend tests,
frontend build/types, focused Ruff, uncached three-file mypy and whitespace
checks passed. Build retains the existing large-chunk advisory. API checks
finished before the merged frontend build began.

**Ticket12 remains open:** actual meaningful permitted exact-watch assets,
remote-load/browser usability and buyer visual-first/remaining-task retesting
are not established. No rights adjudication, live acquisition or activation
acceptance is implied. Original and sibling worktrees were not edited or cleaned;
parent retains cleanup ownership. This receipt and tracker update are a separate
local documentation commit after the history-preserving merge.

## Real private-use asset slice — 2026-10-28

Base integration tip `d14506a75692ba61641f8a578208b65321bf8929` was merged
into the implementation worktree before changes. No integration checkout was
modified. The task authorized finite public source/terms research and image
retrieval; no accounts, source price ingestion, contacts, production DB,
deployment, activation, push, PR, browser preview or server launch occurred.

This slice retrieves and retains **two actual unchanged Casio images**, rather
than treating test URLs as assets. Both files were opened with the local image
viewer. The front photograph and wrist photograph show the exact named blue
Casio base model; the UK manufacturer page supplies the VEF heading. Regional
packaging/merchant SKU/offer identity remain separate. Europe-hosted copies and
Europe terms are the reuse basis: section 1 excepts solely private copying from
its written-permission requirement. UK terms contain additional restrictive
other-website wording, so the initial UK-hosted candidate was replaced rather
than silently relying on only its permissive paragraph. No UK-only lifestyle
file remains in the committed assets.

The [rights/identity/hash manifest](../../tests/fixtures/watch-images/manifest.json)
and [source findings, alternatives and missing-case decisions](../../tests/fixtures/watch-images/README.md)
limit these copyrighted files to Jay's solely private non-commercial local
walkthrough. They are not repository-licensed or publishable product assets.
The source records supply actual links and restrictive terms for Militado,
Addiesdive and San Martin; no matching open-licensed alternative was found in
the finite searches. Merkur's exact Lightning reference remains unresolved;
other salmon Merkurs were explicitly rejected. The minimum next step is owned
photos or permission for the other cases, plus exact variant/reference selection
where missing. No seller or rights holder was contacted.

The existing original HTTPS depiction contract still passes normal discovery
execution, persistence and the public feed API. Its unsigned URL validator is
unchanged. A **test fixture only** router loads two hash-verified files into a
fixed allowlist, with no caller-controlled file paths, fetch, proxy or production
mount. Only `/discover?walkthrough=ticket12` opts the UI into the marked local
manifest. It validates hash-shaped local paths and never falls back to remote
images on pending/failed/missing mapping. The ordinary app retains original
HTTPS behavior. Notices remain beside the card and gallery. Fixture cost
updates retain the image; restart retains its original provenance. No image
field enters cost, qualification, history or alerts. The Casio seed still has
no known delivered total and is not alert eligible.

Approved TDD seams were supplied in the dispatch: existing public API + normal
execution under MonitoringHarness; focused rendered UI. API red failed on the
missing fixture image module, green verifies actual served content/hash/MIME,
no-store, traversal/unknown-path rejection, five preserved leads, four explicit
placeholders, independent withheld price, normal cost progression and restart.
UI red failed on the missing private resolver; green uses the real asset
manifest to verify local rendering, copyright attribution, unsafe-route rejection
and abstention without remote fallback. No private-method/DB assertion was used.
All API work uses marked temporary SQLite, paused scheduling, controlled
connector/time edges and captured notifications; guard/delivery lists are empty
in the dedicated image workflow. Source retrieval was separate from that guard.

[Raw red/green/check logs](artifacts/watch-image-walkthrough/):

- Broader discovery/watch/final-review/correction/ownership selection: **64 passed**.
- After final Europe asset/manifest replacement, discovery + connected watch
  selection: **10 passed**. These include the real-image workflow.
- Frontend: **42 passed**; TypeScript and Vite build passed (existing chunk-size advisory).
- Focused Ruff passed; uncached existing image/discovery/core model mypy passed.
- `git diff --check` passed.

Commands use the retained `t3-7260bb2e/.venv/bin/python` and Node 24.14.1.
Only this worktree's ignored `frontend/node_modules` symlink points to existing
integration dependencies. The built `frontend/dist` is present locally; rebuild
from the committed sources after parent integration, before launching the
[updated walkthrough](watch-workflow-buyer-guide.md). No running fixture was
left behind. Build/API runs were sequential after the initial regression run.

**Acceptance remains open.** Two views of one model make a real single-product
visual check possible, not a meaningful five-watch comparison. Four missing
cases, actual browser load/failure/keyboard/narrow behavior and the buyer's
visual-first/remaining-task feedback remain unproven. No live buying-price,
source coverage, general redistribution right or release claim follows.

Final re-merge before handoff: `integration/watch-category-discovery` remained at
`d14506a75692ba61641f8a578208b65321bf8929`; merge reported already up to date.
Parent retains integration ownership.


## Sole merger private-image review — 2026-10-28

Independently reviewed candidate `cae6d04610ca7b24f5044595b3787d58fa9a9e28`
on `t3/watch-image-walkthrough` in the clean pinned `t3-ad24f213` checkout,
against integration `d14506a75692ba61641f8a578208b65321bf8929`. Read the latest
image receipt, fixture README/manifest, buyer guide, ticket12, originating spec,
engineering standard and CONTRIBUTING. Both axes were reviewed directly by the
sole reviewer, without subagents, as dispatched.

**Standards: zero blocking findings.** Test-only routing reads the repository
manifest at startup, verifies SHA256, and serves only preloaded allowlisted
names. Caller input cannot select a filesystem path or upstream URL. Unknown and
encoded traversal routes return 404 in the guarded API workflow. No production
source imports/mounts this router; the frontend query flag cannot mount it or
activate collection. The private resolver permits only same-origin hash-shaped
asset routes and abstains while missing/loading/failed, without remote fallback.
No new qualification, cost, history or alert bypass was found.

**Spec: zero blocking findings for the bounded private single-model slice.**
The existing Casio feed card resolves the original persisted HTTPS depiction to
local bytes, with attribution/provenance beside it. The separate expandable
gallery supplies two views of that same model; it is not five-watch completion.
The four other feed candidates remain explicit placeholders. Synthetic delivered
cost and alert eligibility remain independent, including withheld Casio total.
Actual buyer visual-first acceptance and remaining task retest are still open.

Official public-page checks: the Europe product page links precisely the front
and wrist source URLs in the manifest. Both local images were independently
viewed and decoded as 1200×1200 PNG/JPEG; hashes exactly match the manifest.
The official Europe terms were independently fetched directly after the web
reader timed out: section 1 excepts solely private copying from its prior-written-
permission requirement. This supports the documented narrow private-use
assessment, not an open or redistribution licence. UK official terms were also
read and their restrictive other-website wording confirmed. Refreshing the UK
product page failed (web-reader timeout; direct response was an error page), so
the full VEF suffix is retained as implementer-recorded identity evidence rather
than independently refreshed proof. Europe independently establishes base-model
identity; no regional packaging or merchant SKU qualification follows.

Sources: [Europe terms](https://www.casio.com/europe/terms/),
[Europe product](https://www.casio.com/europe/watches/casio/product.MTP-B145D-2A2V/),
[UK terms](https://www.casio.com/uk/legal/terms-of-use/).
Copyright/trademark notices are retained on card and gallery; repository licence
does not cover these files. No broader distribution is accepted.

Independent candidate checks on a stable checkout:

- Guarded discovery/watch/final-review/correction/ownership pytest selection:
  **64 passed in 74.19s**.
- Frontend `npm test -- --run`: **42 passed**; `npm run build`: passed.
- Ruff over all five changed Python workflow/test files: passed.
- Uncached mypy over discovery_images, discovery and core/discovery: passed
  (existing unused-section note); `git diff --check`: passed.

Merged locally with `--no-ff` as `95ec1e6957018fe65932d024c7a06ee851515e6a`,
first parent the integration SHA above, second parent the candidate. Merge tree
`333ecc6d53f028ff08b7db97d67e5945b15496d1` exactly equals the candidate tree.
On the stable merged checkout, discovery + watch pytest passed **10 tests in
11.30s**, frontend passed **42 tests**, build/types passed, and the same Ruff,
uncached three-source mypy and whitespace checks passed. API tests finished
before either build began; no checkout moved during a test run. Existing Vite
large-chunk advisory remains. Candidate and integration were clean before the
merge; candidate remained pinned and clean afterward. This receipt/tracker is a
separate local documentation commit. No sibling files were edited or cleaned.

**Ticket12 stays open.** Four usable assets still require owned photographs with
retention/display permission or separately authorized rights-holder contact.
Militado needs exact ML05/ML05B/dial/finish selection; San Martin needs exact
size/dial/revision; Merkur needs its original Lightning reference/link and photo
permission; Addiesdive needs permission for the mint AD2066 depiction. Browser
load/failure, desktop/narrow keyboard usability and actual buyer visual-first/
remaining-task retest remain unproven. No browser preview, external messages,
accounts, price acquisition, production database, activation, push, PR or public
distribution occurred. No live/release acceptance follows.


## Buyer feedback on private Casio image walkthrough — 2026-10-28

After being given the running private walkthrough at
`http://127.0.0.1:8893/discover?walkthrough=ticket12`, the buyer replied:
“looks good”. Record this as positive visual feedback on the presented Casio
image slice, not task-by-task acceptance of the full workflow. The session marker
was `ticket12-connected-ui-v1`, run `ed68a1dd2ed14dec81a0cdd7cf982477`, with
`ticket12-private-images-v1`, temporary storage, automatic checks disabled,
zero blocked edges and zero initial captured notifications. Presented integration
HEAD was `a2f7c174bbef03078a899cefbcedab8de11d2133`.

Viewport, keyboard use, image-load failure behavior and completion/understanding
of the remaining tasks were not reported. Four missing image cases and their
permission/variant/reference decisions remain unresolved. Ticket12 stays open;
no production, live-market or full five-watch acceptance follows from this feedback.
