# Approved eBay and AliExpress API access probe

Executed **2026-10-27**, after the user approved the [five-request protocol](source-access-actions.md#parent-inventory-after-the-documentation-pass). This is the explicit credential-use exception for this bounded probe, not a new account/DS/buyer OAuth or ongoing collection approval.

Evidence: [redacted structured receipts](source-api-probe-receipts.json), [executed probe](probes/source-api-probe.py). The receipt file records the executed script's SHA-256. UTC timestamps are response/decision completion times; request start times/durations were not separately recorded.

## Result

**Four probe-induced provider requests**, maximum five; **zero retries, followed redirects or fallback requests**. No fifth request was made because no AliExpress detail candidate was established. The count covers this isolated probe, not unrelated scheduled activity in the deployed application.

The probe ran in the deployed PriceRecon container on Proxmox VM 101 using existing environment credentials. Values and the in-memory eBay token were never printed, copied to this repository or saved to a token store. No application startup, scheduler run, notifications, database writes, credential rotation or production config/service change was triggered. API responses were reduced in memory to the allowlisted status/field receipts; raw responses, prices, titles, sellers, images and cookies were not archived.

### eBay Browse: token, UK query and item detail succeeded

| UTC | Request | Observation |
| --- | --- | --- |
| **10:42:05.417489** | OAuth client-credentials token | HTTP 200, nonempty access token received; no API error. Token used only in probe memory. |
| **10:42:06.125871** | Browse item-summary query, `Casio MTP-B145D`, marketplace `EBAY_GB`, `deliveryCountry:GB`, limit 5 | HTTP 200, five items returned, next page present, no API error. No pagination followed. |
| **10:42:06.595506** | Detail for one returned item whose title matched the family reference | HTTP 200, no API error. Presence established for item ID/title, price, condition, buying options, seller, shipping options, ship-to locations, estimated availability, localized aspects, taxes and public item URL. `primaryItemGroup` was absent. |

The public item identifier is retained only as a SHA-256 correlation fingerprint in the structured receipt. No listing content, seller identity or price is reproduced here, and no eBay/non-eBay price presentation was built.

**Accepted:** these credentials were accepted for the production OAuth/Browse requests tested, the bounded UK query returned records, and a returned item's raw detail response supplies the listed field groups. This is a **live point-in-time API access/field-availability receipt**.

**Not accepted:** exact colour/reference suffix or selected variation, actual buying-mode value, condition equivalence, stock quantity, UK postcode-specific delivery/tax inclusion, complete delivered total, stable merchant identity, repeated freshness, historical retention or permission for derived prices. Field presence does not establish any field's correctness or sufficiency. A next-page link makes the five-result coverage explicitly partial. Missing `primaryItemGroup` is not proof that no variations exist. This was a protocol probe, not the full connector's normalisation/executor path.

### AliExpress affiliate: signed query succeeded; detail omitted

| UTC | Request / decision | Observation |
| --- | --- | --- |
| **10:42:08.666365** | Existing connector's signed affiliate `product.query`, `Militado ML05`, target GBP, destination GB, page 1, page size 5 | HTTP 200, four product records extracted, no recognised API error code. |
| **10:42:08.666424** | Select a returned record for detail | No query candidate established by the probe's checked title fields; **no detail request** made. |

**Accepted:** the existing affiliate app credentials and connector signing path produced a live product-query response with records for this request. No DS endpoint/token or browser/search fallback was used.

**Limit:** the selection check examined `product_title` and `title`; the existing connector also supports aliases such as `productTitle` and `itemTitle`. The receipt deliberately does not store returned title values/field names, so it cannot distinguish an off-query response from an unsupported title alias. **Do not report that AliExpress has no ML05 offers or that all four records were irrelevant.** No repeat query was made to repair the probe or spend the remaining allowance. A later approved probe should include supported title aliases and a small field-name/match-diagnostic allowlist before choosing its single detail request.

Requested GBP/GB does not prove returned price currency, UK destination applicability, selected SKU, shipping, VAT, stock or an obtainable offer. Affiliate coverage is not complete marketplace coverage. No product-detail or recurring-monitoring qualification follows from this query.

## Source-inspection finding during probe preparation

The existing [eBay OAuth helper](../../../src/pricerecon/connectors/ebay.py) builds its tracking `cache_key` from app ID and cert ID and includes that key in an INFO log message. That is credential-derived logging in the inspected source. This probe **did not invoke that helper**: it used the same token protocol directly to avoid its logging, persistence and retry behaviour. Existing production logs were not inspected, and no actual exposure in retained logs is claimed here. Correcting this helper is a separate code change before using it for further controlled full-connector qualification; this approval did not authorise that change.

Update: the user subsequently authorised the helper correction. [Deployment and regression receipt](ebay-auth-logging-fix.md) supersedes the pending-fix status above; historical log contents remain unexamined.

## Source gate

The prior credential-access uncertainty is now narrowed for the two tested API lanes. Preserve their separate statuses: **eBay raw Browse access/field availability observed**, **AliExpress affiliate query access observed but detail untested**. Neither is an accepted complete UK watch-offer workflow.

The [remaining access actions](source-access-actions.md) still apply to permitted ongoing use/retention, the other source families and Militado's agent identification. No category-average computation, historical series or deployment was performed. The source ticket remains open and downstream dependencies remain blocked.
