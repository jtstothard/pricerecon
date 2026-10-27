# AliExpress browser-first connector — staged verification

2026-10-27. User agreed to implement browser discovery, inspect discovered ML05 products, distinguish selected configurations from titles, and retain unknown UK costs. This is the implementation follow-up to [the browser access receipts](aliexpress-browser-receipts.md). The new workflow has **not been deployed or enabled for production polling**. Previously deployed browser and eBay fixes remain separate.

## Implemented behavior

When AliExpress has a named shared browser backend, `search()` uses that route authoritatively. It does not silently substitute affiliate, DS, Brave, SearXNG or legacy direct HTTP results when browser inspection fails. Without a named backend, the existing lanes remain available.

`inspect_browser_search(query, filters)` returns a typed `BrowserSearchReport` for review. It follows only validated AliExpress product links from complete discovery content, inspects 1–10 products (default 2), and reports discovered/inspected counts and whether inspection was capped. `browser_product_ids` can select only IDs actually found in that discovery. A direct product ID or accepted AliExpress URL can inspect one item without a search. Redirected, blocked, unrecognised or truncated discovery is degraded rather than interpreted as an empty market.

The report separates title, displayed price, selected controls, selected SKU, explicit SKU-to-price binding, destination, quantity, shipping/VAT claims and total cost. Requested movement/dial/strap/size must each match observed selected evidence before a listing can claim exact configuration. A title or another available option cannot establish the selection. SKU-qualified listing identities include both product ID and SKU ID. Missing shipping or delivered total stays `None`; a VAT sentence is retained as a claim. Total landed cost is deliberately unknown in this read-only workflow.

Ordinary `search()` rejects capped or unresolved reports with structured degradation. Partial offers remain inspectable without inserting misleading prices into monitoring. Controlled fixtures prove the positive qualification path; **no live selected SKU/price binding was established**. Browser search is not yet an accepted monitoring source.

The query tokenizer also now case-folds before extracting tokens: `Militado ML05` previously became `ilitado`, `05` because its regex accepted only lowercase input.

## Fresh live observations

One-off app containers used staged source over the current deployed image, without starting the app scheduler or mounting application data. Existing production browser routes were used; no affiliate API was called, no account profile selected, and no cart, login or purchase action performed.

- Three initial direct Camofox DOM investigations established that the product title's VH31 claim coexists with selected `Color: Grey with logo 2035`. Initial unhydrated DOMs were not treated as evidence of absent options.
- Two staged CloakBrowser search navigations were rejected as `partial_browser_discovery`: both ordinary DOM cloning and a reduced-attribute DOM exceeded the existing 262,144-character limit. That limit was not raised. This optional DOM mode is **not a qualified live AliExpress search route**.
- First complete staged Camofox connector run: **30** distinct item links, one discovered product inspected, capped. Displayed GBP price and VAT claim retained; quoted snapshot labels initially remained unknown.
- One bounded product inspection established the actual snapshot syntax: `- text: "Color: Grey with logo 2035"`. Other VH31 labels were images of available options. The parser was corrected to decode quoted text labels, with a regression fixture that rejects promotion of those other options.
- Final staged connector run: **24** distinct item links, one inspected, capped. The differing counts are separate point-in-time observations, not a freshness or coverage guarantee.

Final inspected product: `1005007071090465`, at `https://www.aliexpress.com/item/1005007071090465.html`. Its title described ML05/VH31; selected evidence was `dial: Grey with logo 2035`, `movement: 2035`. Displayed price **GBP 35.82**, VAT-included claim present. Selected SKU, SKU-bound price, UK destination, unit quantity, shipping and UK total were unknown. Qualification against requested VH31/Grey/Nylon/38mm correctly reported movement and dial mismatch plus unverified fields. “Grey” was not silently equated with the longer combined option label.

The two successful searches and final product inspection establish the integrated browser route, independent of affiliate catalogue filtering. They do not establish non-affiliate eligibility of this product, pagination completeness, all-market coverage, variant availability, permitted ongoing retention or a buyable delivered UK offer.

## Verification and implementation limits

- **66 focused Python tests passed** across AliExpress workflows/fallbacks, shared browser behavior and the earlier eBay logging correction. Existing Pydantic/datetime deprecation warnings remain.
- Narrow mypy check passed for `aliexpress.py`, `aliexpress_browser.py`, `external_browser.py`.
- Ruff passed for the new evidence module and workflow tests. Existing AliExpress/shared-adapter files retain 20/19 diagnostics respectively, with no introduced diagnostic code/message counts compared with HEAD.
- Two Node wrapper contract tests passed.
- A real installed Chromium, with container networking disabled, passed `services/cloakbrowser/dom.integration.mjs`: current radio/select state was retained, stale checked attributes corrected, scripts/presentation state and unrelated input/textarea values removed. No binary was installed or downloaded. This controlled fixture does not qualify the live merchant DOM route.

During the first red tests, the connector's own HTTP client was not mocked even though the shared browser client was. This accidentally attempted legacy Brave/SearXNG/direct-HTTP fallback requests. The test harness was corrected to route **every** connector request through MockTransport and reject any host other than the synthetic browser. The passing checks above use that corrected isolation. No monitor, credential, saved listing or token persistence was involved in those test attempts.

Camofox metadata now retains final URL and explicit snapshot truncation/completeness; absent completeness is rejected. Staging merged these additions into the deployed adapter while retaining its existing concurrency semaphore, rather than overwriting it with this worktree's older base. CloakBrowser's optional `renderMode: dom`/`readySelector` leaves normal HTML behavior unchanged and still advertises truncation honestly. DOM filtering is not a general secret scrubber.

## Review and next gate

Use an explicitly scoped anonymous backend and call `inspect_browser_search("Militado ML05", {"browser_max_products": 1})` for diagnostics. To qualify a listing, supply explicit `browser_variant` movement/dial/strap/size and obtain actual selected SKU/price, UK destination and unit quantity evidence. Synthetic `data-sku-id`/SKU-control fixtures test the contract; those fields have not been established on the live ML05 page. The next source gate is obtaining that binding and delivered-cost evidence, not enabling alerts from the observed title/price.

Source qualification remains open and downstream blockers unchanged. No commits, pushes, global browser defaults, live scheduler changes or new polling were made by this follow-up.

## Staging identities and cleanup

Final staged app image: `sha256:a3eeafa9862d51d1b39927174d9504e1fae93842a44e9c52e1a021dc2feaa0d4` (`pricerecon-ali-stage-app`). Final staged wrapper: `sha256:200da420eafa5cd96896f390d739b7e9aa04a90685f87494f5fb2bd207279547` (`pricerecon-ali-stage-browser`). These tags retain reviewable built artifacts, not running services.

Staged source SHA-256:

| File | Hash |
| --- | --- |
| `aliexpress.py` | `1869f447fac7115bb2878f6c9aeaecc4dbe1ab3059ebd0e7f6586e9408b60990` |
| `aliexpress_browser.py` | `962d1f81bdf512087063e434a16f3dc3edc0dda93e24318d38af185b6c6ec706` |
| merged production `external_browser.py` | `bec5405b0b2a69081926ef58fa2ab550500938dcb13f7dfcf8944b9b70aa43a8` |
| `server.mjs` | `8f027e94ab68e7ff5bd20b665a2873a9723e5005ff2a6cb59021831e30b49424` |

The exact owned Camofox test context `pricerecon-ali-workflow-20261027` was closed through the protected cleanup endpoint: HTTP200/ok. Its existing key was used only inside its own container and never exported. Temporary wrapper containers were removed, and the final filtered container inventory was empty. Temporary staging source files were removed after these receipts; source and fixture code remain in this worktree and built artifacts under the tags above.

Production readback remained running on PriceRecon `sha256:90c84edd8d69d2bcacf6b433601a0de230d457622503f520c447f8b15f6f745d` and CloakBrowser `sha256:9962badf9a04500590d1c02a191e98749e275a5f492e9d5f0ce601f1e667930d`. No production compose/source file was changed in this follow-up.
