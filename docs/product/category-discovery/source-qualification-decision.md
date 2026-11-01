# Source qualification decision: a bounded roster, with explicit unavailable routes

Resolved 2026-10-27 for [Which source routes can support an honest watch discovery claim?](tickets/source-qualification.md). This decision accepts a research roster and the operation-specific classifications below. **It does not accept a complete UK offer, recurring collection, historical-price database or best-deal claim.** A source can supply a useful lead while failing selected-configuration, destination, cost or use-rights gates.

The user's latest approval covered everything needed for this ticket, superseding earlier per-pass user limits. Existing services and credentials were reused. No source account was created, provider contacted, purchase made, credential exported, price history started or production polling enabled. Blocked outcomes are retained as coverage gaps rather than deleted source families.

## Smallest useful cohort

Retain five contrasting cases: Militado ML05/ML05B; Addiesdive AD2066 mint; San Martin SN0144; Merkur Lightning salmon; and **Casio MTP-B145D-2A2VEF**. The first four are conflict/incompleteness cases from the [retained corpus](watch-research-context.md); their prior prices and exact configurations are not accepted. The Casio suffix is now pinned by [Casio UK](https://www.casio.com/uk/watches/casio/product.MTP-B145D-2A2V/), not a family-level keyword. Retailer colour aliases and cross-region references still require identity evidence.

This is the smallest useful investigation cohort, not a claim that all five currently have qualifying offers. Missing Merkur identity and Addiesdive selected-colour proof are deliberate abstention cases, not reasons to substitute unrelated watches.

## Accepted coverage classification

D = discovery; E = enrichment; V = selected-offer verification; M = repeated monitoring. “Qualified” is confined to the named tested operation. No row is qualified for complete V or M. “Provisional” rows can supply reviewed leads, with missing fields retained. “Blocked” rows require the named prerequisite before acquisition/activation; “unsupported” applies to the proposed use rather than every capability of the provider.

| Mandatory family and route | Accepted operation/status | Evidence, bounds and remaining gate |
| --- | --- | --- |
| AliExpress browser wholesale search → product page, Camofox | **D/access and bounded product inspection live-tested; provisional E/V** | Integrated staged runs returned 30 then 24 distinct links, one inspected each, explicitly capped. Product/selection/display-price conflict retained. One page is not pagination completeness. Stable selected SKU, SKU-bound stock and UK delivered cost remain missing. [Workflow](aliexpress-browser-workflow.md), follow-up below. |
| AliExpress affiliate query/detail; DS separately | Affiliate query **provisional E**; DS **unsupported as an assumed existing entitlement** | Signed query returned four records. Affiliate inventory is narrower than browser discovery; detail/DS were not qualified. No silent substitution for wider browser coverage. Existing query access does not prove archive rights. [API receipt](source-api-access-receipts.md). |
| eBay UK Browse search/detail, new and used queried separately | **D/raw-field access live-tested; provisional E/V** | Five-result pages with next links, no pagination followed. This follow-up examined two general-query details and two used-only details; full reference, condition, buying mode, availability and shipping/tax fields were distinguished. No postcode, accepted final total, condition equivalence or historical licence. [Follow-up below](#additional-live-results). |
| Chrono24 specialist used-market route | **Blocked automated D/M; provisional manual lead** | Retained preflight/access/first-party FAQ evidence, no approved automated/API/retention route. Dealer/private seller and custom shipping quotes remain separate. No contact used to fill gaps. [Research matrix](source-qualification-research.md), [access review](source-qualification-access-resolution.md). |
| Militado brand/store-direct candidate | **Blocked D/E on verified operator identity** | Fresh guidance/robots both HTTP200 explicitly provide read-only product/collection routes with remote Web Bot Auth identification. No recognized signer was found in inspected PriceRecon source/config fields. This is not proof none exists elsewhere. Cloudflare programme enrollment and Shop account linking are not necessary prerequisites. Store/manufacturer ownership remains unproven. [Signing prerequisite](source-qualification-access-resolution.md#signing-the-smallest-concrete-route). |
| Watch Shop / WatchGecko UK retail | **Provisional public-reading candidates; current selected offers unqualified** | Existing access stops and current use/delivery documentation retained. WatchGecko restricts assumed archival reuse/deep-link publication; Watch Shop current product-specific delivery can require checkout. No retailer coverage or total inferred from generic delivery tables. [Access review](source-qualification-access-resolution.md). |
| Sakura Watches international UK-shipping candidate | **Provisional clean-path reading; blocked/unresolved automated retention** | UK exports/help are documented; stock versus orderable stock and buyer import charges remain separate. Clean category is distinct from disallowed search/paging routes. No selected current UK offer qualified. [Route analysis](source-access-followup.md). |
| `sanmartin.watch` international/regional independent retailer | **D/access live-tested; provisional E/V** | Category and two SN0144 movement configurations observed in earlier bounded receipts. Explicitly independent retailer, not manufacturer-direct. Selected SKU, fulfilment origin, availability and UK fees remain unverified. [Merchant receipts](san-martin-source-receipts.md). |
| Brave API / SearXNG search leads | **Brave runtime/storage access unresolved; SearXNG transport healthy, D unqualified** | No Brave key found in the two inspected PriceRecon fields; no plan/storage entitlement inferred. Existing SearXNG `/healthz` and `/config` return200 from PriceRecon; engine configuration is not successful or permitted merchant discovery. No upstream search query executed in this follow-up. [Access review](source-qualification-access-resolution.md), follow-up below. |
| Google Shopping aggregator leads | **Blocked/unqualified automated D/E** | Prior redirect/preflight stop retained; current exact search-route robots check below. An aggregator is a lead, not the seller or selected-price authority. Merchant verification and reuse rights remain separate. No new Shopping content acquired. |
| Google Custom Search JSON API | **Unsupported new dependency** | Closed to new customers, existing service ends 1 January 2027. This does not describe Google Shopping. [Official notice](https://developers.google.com/custom-search/v1/overview). |
| HotUKDeals watch deals; Reddit r/ChineseWatches / r/Watches | **Blocked automated D/M pending source access/use prerequisites** | HUKD terms and robots fresh GETs403; no feed automation/storage grant established. Reddit requires approved API use including personal/non-commercial apps; an RSS/browser fallback is not approval. No community content collected. [Fresh primary-source review](source-qualification-access-resolution.md). |

Registered PC-oriented marketplaces/retailers remain **unsupported as evidence of this cohort's coverage**. They were not deleted from the repository inventory or declared universally watch-free.

## Additional live results

### AliExpress: public destination and variant controls

One new anonymous Camofox product tab, no affiliate API, account, address, cart or checkout. Initial header was `Other/EN/GBP`, with selected `Grey with logo 2035`, displayed GBP35.82. This confirms that GBP display alone cannot establish UK applicability.

The public shipping-settings control opened successfully. Its visible country was United Kingdom, with default region/city England / Bath and North East Somerset. Saving those settings succeeded, and the header changed to the displayed region / EN / GBP. These were site-default geographic settings, **not the user's address or a verified delivery destination**.

Selecting the already displayed `Grey with logo VH31` option succeeded. Selected label changed from 2035 to VH31; displayed price changed from GBP35.82 to **GBP48.52**, and quantity control displayed1. The DOM's `data-sku-col` changed from `14-29` to `14-350850`. Those are option-control identifiers, **not accepted seller SKU IDs**. No `sku_id` was added to the URL. Public Product JSON-LD had an Offer with GBP and an InStock claim but no SKU binding. Consequently selected configuration/display price is observed; stable selected SKU, SKU-specific stock, shipping and complete UK tax/total remain unknown. Do not promote the generic Offer to proof of that selected SKU.

The final owned context was deleted through Camofox's protected endpoint, HTTP200/ok. Existing service key stayed inside its own container. Individual browser-request timestamps were not captured by these diagnostics; observations are dated 2026-10-27 and are not a freshness-SLA measurement.

### eBay: exact-reference and used-market separation

Two isolated no-retry probes used existing environment credentials inside PriceRecon, each capped at four provider calls: token, one five-result query, two details. Marketplace EBAY_GB, deliveryCountry GB, fixed-price filter; the second probe additionally used `conditions:{USED}`. This filter separates broad new/used states, not every granular condition. [Official filter semantics](https://developer.ebay.com/api-docs/buy/static/ref-buy-browse-filters.html).

- General-query receipt completed **11:36:53 UTC**. One detail described MTP-B145D-3AVEF; another explicitly described **MTP-B145D-2A2VEF**, quartz, 35mm case, steel bracelet, seller-described blue dial. Both were new with box/papers and fixed-price. The exact-suffix item reported in-stock quantity4 and two GBP delivery options. Tax array was empty for that item: **unknown**, not tax-free or proof of an all-in total.
- Used-only receipt completed **11:37:36 UTC**. One detail was Pre-owned–Good but lacked an exact reference in the inspected aspects; the other was Pre-owned–Excellent with reference **MTPB145D2A1V**, not the pinned 2A2VEF. Both exposed fixed price/best offer and in-stock quantity1. One had a VAT-not-included flag; the other VAT-included and calculated international shipping. They are useful condition/reference counterexamples, **not exact comparable alternatives**.

Each query returned five records and a next page. No pagination followed. No postcode, buyer identity, order or seller contact was supplied. No app scheduler, database writer, saved-token store or notification was invoked. Tokens remained in probe memory. Only minimal public reference/field sufficiency facts are retained here, not seller identities, raw API responses or a price series. These are access/semantic receipts, not a display of current eBay prices or a grant for category baselines.

### Search/signing inventory

Existing SearXNG container `searxng-ldr` is attached to `media_back` with alias `searxng`. PriceRecon can reach `/healthz` and `/config` on port8080, both HTTP200. Thus earlier local-test DNS failures do **not** establish production SearXNG unavailability. General-engine metadata includes multiple upstreams; no upstream acquisition or storage permission is inferred.

The inspected PriceRecon environment had neither `BRAVE_API_KEY` nor `BRAVE_SEARCH_API_KEY`, and none of the three inspected Web Bot Auth identity/key fields. Source search found no signer implementation in PriceRecon `src`, `services` or dependency manifest. This bounded inventory does not search every account/secret store or claim that no plan/operator identity exists elsewhere. Do not purchase/register a duplicate by default.

### Exact-path access metadata refresh

Four no-retry ordinary robots GETs from the deployed PriceRecon environment, 2026-10-27; no merchant content followed:

| Host | Result | Narrow interpretation |
| --- | --- | --- |
| Google | robots HTTP200; generic rules reject `/search?tbm=shop&q=Casio+MTP-B145D` | The actual Shopping-search candidate is disallowed. This is a source-path limitation, not the obsolete original user allowlist restriction. |
| Watch Shop | ReadTimeout | No retry; no current rule inferred from failure. |
| Sakura | robots HTTP200; generic rules allow `/watches` | Clean category crawlability is established, not selected stock, retention or unrestricted paging. |
| Chrono24 UK | robots HTTP200; generic rules allow `/` | Root crawlability is established; do not describe the whole host as robots-blocked or infer permission for search/API/archive use. |

These checks concern the generic user-agent group and actual named paths, not a spoofed crawler identity. They do not override other applicable terms or prove what a different named group may do.

## Permission, freshness and activation decision

Use browser-first AliExpress and eBay Browse as the smallest **review-lead** investigation lanes, and the observed San Martin retailer as a contrasting retail case. Keep every mandatory family visible with its limits. Do not enable unresolved routes, create a longitudinal archive, calculate category averages, or claim a UK best offer from these results.

The refreshed [access resolution](source-qualification-access-resolution.md) names source-specific prerequisites. In particular: recognized signing identity for Militado; provider-approved Reddit use; readable HUKD feed/use conditions; actual Brave plan/storage authority; and a demonstrable grant for the intended eBay retention/derivation. Successful retrieval, user's approval and solver health are not substitutes for these source conditions. No new signer service was built without an operator identity to register, and no provider application was submitted.

No repeated freshness or complete pagination experiment is accepted. Each report must retain its time, cap, missing fields and failure state; source absence is different from no offers. Recurring cadence, quotas, maintenance cost and degradation are inputs to [the operating-envelope investigation](tickets/operating-envelope.md), not established production facts.

## Why the research ticket can close

The ticket requires a coverage matrix that includes qualified, provisional, blocked and unsupported outcomes. Its required live/access evidence is now attached as positive operation receipts or explicit access failures/prerequisites for each mandatory family; it does not require successfully enabling every provider. Closing records that source decision, **not passage of later identity/history/UK-cost or end-to-end gates**. No mandatory family has been removed to make the matrix pass.

New facts are routed to existing sharp questions rather than duplicated into new tickets: selected option versus SKU and eBay full-suffix/condition conflicts to [identity/evidence](tickets/identity-evidence.md); retention and comparable observations to [history](tickets/observation-history.md); UK/default-region/tax gaps to [delivered cost](tickets/uk-cost.md); permission/cadence and missing integrations to [operating envelope](tickets/operating-envelope.md). The next frontier is **What constitutes an exact configuration and sufficient identity evidence?** No downstream answer is resolved here.
