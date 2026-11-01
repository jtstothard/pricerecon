# San Martin retailer: bounded category and product receipts

Observed 2026-10-27 after the user instructed continuing source qualification following the [browser fixes](browser-fix-deployment.md). This pass used existing deployed browser services, no account login, basket, checkout, source API, monitoring run or production configuration change.

## Scope and access interpretation

Host: **`www.sanmartin.watch`**, an independent retailer, not the manufacturer. Current [terms](https://www.sanmartin.watch/pages/terms-of-service), updated 16 October 2026, were reviewed on this exact domain. They differ from older terms found on another retailer domain. Do not transfer that other domain's restrictions or ownership to this source. The current terms restrict misuse and protected-material reproduction; they do not establish an ongoing collection/archive licence. This was a small personal investigation retaining factual operational receipts, not a raw-content/image archive or legal clearance for repeated collection.

The exact-host robots response was checked through the repaired CloakBrowser route: HTTP 200, final URL unchanged, not truncated. Its generic rules restrict `/search`, transaction/account-related paths and specified API paths; they do not blanket-disallow the clean category/product paths below. No forbidden search, cart or API path was requested. No custom identity was set to impersonate an allowed crawler.

Bound: one category, at most two product details; five browser navigations total (robots, category through each of two content routes, two product pages). Category requests and product requests were separated by at least five seconds per host. No pagination, sorting, public-country selector, variant change, address entry or purchase action occurred. Browser subresources were not individually counted. End-to-end source qualification remains open.

## Route receipts

| UTC / route | Observation | Acceptance and limit |
| --- | --- | --- |
| **10:32:13.288755**, repaired CloakBrowser → [robots](https://www.sanmartin.watch/robots.txt) | Main status 200; final URL unchanged; untruncated rules. | Current rules readable through this lane. This supersedes only the earlier ordinary-HTTP inspection failure, not the access rules themselves. |
| **10:32:35.956923–10:32:40.595679**, repaired CloakBrowser → [classic collection](https://www.sanmartin.watch/collections/classic-collection) | Main status 200; final URL unchanged; exactly 262,144 returned HTML characters, `html_truncated=true`. No heading or product links found in that received prefix. | **Partial**, not a zero-result catalogue. The bounded HTML prefix ended before usable product content. No cap increase or completeness claim. |
| **10:33:56.025427–10:33:58.861936**, Camofox snapshot → same classic collection | Final tab URL matched requested URL; snapshot 29,129 characters. Found distinct product links naming 39 mm Miyota 90S5 and 39 mm Miyota 9132 SN0144 watches. | A usable **point-in-time discovery path** for those two leads. Links were relative and resolved against the observed host. Not all catalogue cards were inspected; no total coverage, page completeness or maximum-inventory claim. Camofox does not expose main-document HTTP status through this adapter. |
| **10:34:55.797383–10:34:59.172277**, Camofox → [39 mm / Miyota 90S5 SN0144](https://www.sanmartin.watch/products/san-martin-new-39mm-original-design-sunburst-jianzhan-dial-miyota-90s5-automatic-mechanical-sn0144) | Same-host final tab URL confirmed before snapshot reading; adapter degradation `none`; snapshot 36,704 characters. Product heading names the movement/size, a dial option is checked, quantity is 1, and an add-to-cart price is present. | **Partial merchant evidence**, not a qualified UK offer. See the field receipt below. No cart button was clicked. |
| Second and final product-detail navigation, after the five-second gap, Camofox → [39 mm / Miyota 9132 SN0144](https://www.sanmartin.watch/products/san-martin-39mm-original-design-miyota-9132-mens-watch-sn0144) | The retained tool result includes a description identifying SN0144-DG and Miyota 9132, distinct from the first product. The diagnostic output was overwhelmed by script text and truncated, so its complete metadata/top-of-page selection and price are not retained here. | **Incomplete diagnostic receipt**. Do not infer a selected colour, price, SKU, source status or exact timestamp. No refetch was performed to repair the logging mistake or exceed the two-detail cap. |

These were direct public-browser requests through PriceRecon's deployed shared adapter, not a qualified site-specific connector's search/parser. The Camofox create-tab API response was observed in the isolated probe process to verify final host before requesting its snapshot. That backend observation is not merchant-network interception.

## First product: limited field receipt

| Field | Observed value / limit |
| --- | --- |
| Merchant/source | `www.sanmartin.watch`; retailer identity is the merchant's documented claim, not manufacturer verification. |
| Product-family / title claim | SN0144, 39 mm, Miyota 90S5. These are displayed merchant claims. |
| Checked dial option | **Sunburst Gray Blue**. Other displayed choices are not the selected offer. |
| Quantity | **1** displayed. |
| Displayed item amount | **428.00**, with **`$`** symbol, including the add-to-cart label. ISO currency was not independently established. Do not relabel this as GBP or assume USD from the symbol alone. |
| Availability | Add-to-cart control present. Exact SKU inventory, fulfilment, basket acceptance and deliverability **unverified**. |
| SKU / bracelet / clasp | No accepted selected-SKU identifier or complete selected bracelet/clasp configuration in this receipt. |
| Destination / dispatch | UK destination and warehouse **not selected or verified**. |
| Shipping / tax / delivered total | **Unknown**; no basket/checkout reproduction. |
| Discount | A strike-through/percentage was displayed. It is excluded from accepted savings: no comparable usual-price history or validated discount application exists. |
| Evidence / freshness | Dated source-page observation above; no repeated monitoring or retained price series. No production price alert generated. |

## Findings and cleanup

1. SN0144 family-name matching would combine materially different movement configurations. The two observed leads demonstrate why exact configuration remains a downstream identity decision; no equivalence is accepted here.
2. Bounded HTML can consist mostly of the page head. Its truncation flag must prevent treating missing body links as an empty category.
3. Accessibility snapshots can contain long inline-script text. The probe mistakenly printed complete long lines while trying to inspect a small product section. Future diagnostics must cap each line/field and return a small field allowlist before emitting output. No merchant-page refetch or new production fix was made during this pass.
4. Source status is **provisional**: one-off discovery and partial product fields are observed; UK offer qualification, selected-SKU completeness, repeated freshness and collection/retention rights remain unaccepted. No mandatory source family was removed to close the gate.

The only Camofox context used for this host was the newly derived anonymous source-qualification identity. It was closed by exact ID after the pass; no assigned account profile was selected. Raw snapshots, HTML and images were not saved into the repository. Tool responses remain in the conversation and are not a licensed content archive.
