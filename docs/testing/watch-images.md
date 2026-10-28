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
