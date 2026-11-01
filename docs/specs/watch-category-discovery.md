# Spec: Trustworthy UK watch discovery alongside existing monitoring

**Status:** ready-for-agent  
**Label:** `ready-for-agent`  
**Tracker:** local Markdown; this file is the proposed implementation-spec issue  
**Source:** [accepted category-discovery map](../product/category-discovery/MAP.md)  
**Scope:** first single-user UK watch release; source-only implementation planning

## Problem Statement

The buyer can monitor saved searches, but cannot reliably discover wristwatches from preferences and compare exact available configurations at a defensible UK delivered price. Search results, selected variations, seller claims, coupons and import costs carry different evidence. Treating them as interchangeable produces misleading bargains and alerts. Present snapshots and sparse price-change events do not establish an ordinary price or a complete history.

The buyer needs useful discovery without losing existing monitoring, and needs to see when evidence is insufficient rather than receive a fabricated saving or an unsupported best-deal claim.

## Solution

Preserve existing tracked searches and add independent category/preference discovery through an image-led comparison feed. Retain candidate origins, resolve exact configurations where evidence permits, and show merchant offers with explicit condition, purchase mode, UK cost components, public coupon state, evidence age and checked coverage. Let the buyer edit preferences, correct identities and start exact-item tracking.

Keep uncertain candidates visible and understandable. Withhold qualified comparisons and threshold alerts when identity, availability, cost or freshness is unresolved. Separate verified public delivered totals, conditional totals, unverified benefit opportunities and uncertain cashback-adjusted effective costs. A useful no-coupon path and an unavailable usual price are valid outcomes.

Implement and verify the behavior offline first. Source-specific access/retention, bounded live proof, measured operating limits and activation remain separate acceptance gates.

## User Stories

1. As a buyer, I want my existing saved searches retained, so that discovery does not disrupt monitoring.
2. As a buyer, I want enabled state, source queries, matching rules, targets and notifications preserved, so that upgrades retain my intent.
3. As a buyer, I want category discovery independent of saved searches, so that I encounter products I have not already named.
4. As a buyer, I want editable preferences such as compact, colourful and under £150, so that discovery reflects my buying interests.
5. As a buyer, I want the interpretation of subjective preferences exposed, so that I can correct it.
6. As a buyer, I want unknown dimensions labelled, so that missing evidence does not silently satisfy a constraint.
7. As a buyer, I want simultaneous illustrated candidates, so that I can compare their appearance and price.
8. As a buyer, I want images attributed with permitted provenance, so that illustrations and merchant photos are distinguishable.
9. As a buyer, I want exact reference, generation, movement, size, dial and strap distinctions, so that similar names do not merge different goods.
10. As a buyer, I want selected merchant variations bound separately from product identity, so that a parent listing's cheapest option is not assigned to my watch.
11. As a buyer, I want accessory and component listings distinguished, so that they do not appear as complete-watch bargains.
12. As a buyer, I want unresolved and conflicting identity evidence visible, so that I can judge a candidate without false certainty.
13. As a buyer, I want discovery origins and merchant evidence retained separately, so that copied leads do not become independent confirmation.
14. As a buyer, I want seller, condition, quantity and purchase mode visible, so that comparisons describe what I can actually buy.
15. As a buyer, I want used offers in separate comparison cohorts, so that their prices are not presented as equivalent to new goods.
16. As a buyer, I want auctions distinguished from buy-now offers, so that a current bid is not a guaranteed purchase price.
17. As a buyer, I want visible-condition claims separated from unknown authenticity and internal health, so that photos do not imply unwarranted assurance.
18. As a buyer, I want UK item, shipping, tax/import and other payable components shown, so that I understand the delivered total.
19. As a buyer, I want missing costs exposed alongside a known subtotal, so that unknown charges do not become zero.
20. As a buyer, I want included VAT counted once, so that the comparison does not inflate my cost.
21. As a buyer, I want currency, destination, dispatch and payment assumptions explicit, so that GBP display does not masquerade as UK delivery proof.
22. As a buyer, I want public coupon terms and application status distinguished, so that an advertised code is not mistaken for a verified reduction.
23. As a buyer, I want eligibility, minimum spend, expiry and stack conflicts evaluated, so that incompatible promotions are not summed.
24. As a buyer, I want useful tracking when no applicable coupon is verified, so that coupon availability does not block the core workflow.
25. As a buyer, I want public, personal, payment and cashback scenarios separated, so that conditional or uncertain benefits do not replace a payable price.
26. As a buyer, I want usual price, current best comparable offer and dated observed low explained separately, so that each claim has an honest basis.
27. As a buyer, I want sparse history to show limited evidence without a savings percentage, so that a first observation is not sold as an exceptional discount.
28. As a buyer, I want history to retain unchanged observations and increases, so that a chart is not just a collection of price-drop alerts.
29. As a buyer, I want missing periods and acquisition failures visible, so that gaps do not imply continuous availability.
30. As a buyer, I want coverage and freshness beside comparisons, so that “best” means best within a disclosed checked scope.
31. As a buyer, I want blocked, capped and failed sources distinguished from empty results, so that I understand missing coverage.
32. As a buyer, I want expandable evidence and exclusion reasons, so that I can inspect why an offer qualified or was withheld.
33. As a buyer, I want field/value corrections with retained lineage, so that I can repair a mistaken identity without erasing its history.
34. As a buyer, I want corrections to invalidate dependent totals, histories, comparisons and alerts, so that a wrong variant's price is not transferred to the intended product.
35. As a buyer, I want tracking intent retained after correction, so that fixing evidence does not silently discard my target.
36. As a buyer, I want to track an exact product from discovery, so that I can wait for a defensible delivered-price target such as £60.
37. As a buyer, I want one alert on a verified target crossing, so that uncertainty does not trigger a bargain notification.
38. As a buyer, I want repeat alerts suppressed for the same offer and price, so that duplicate leads and routes do not create noise.
39. As a buyer, I want a further qualifying drop or a fresh crossing after a rise to alert again, so that meaningful new opportunities are not lost.
40. As a buyer, I want restart, recovery, correction and stale evidence handled consistently, so that those events alone do not create duplicate bargain alerts.
41. As a buyer, I want existing tracking and potential-alert verification prioritised under collection caps, so that discovery breadth does not consume their capacity.
42. As an operator, I want shared limits to account for requests, retries and fallbacks, so that resource use cannot silently expand.
43. As an operator, I want degradation and last-good evidence preserved explicitly, so that partial-source failure does not look like disappearance or a current verified offer.
44. As an operator, I want recovery without catch-up bursts, so that resuming a source respects the same limits.
45. As an operator, I want versioned receipts and gate outcomes, so that deterministic verification and live evidence are distinguishable.
46. As an operator, I want source rights, retention, deletion, backup and maintenance prerequisites enforced before activation, so that a successful retrieval does not silently grant continuing use.

## Implementation Decisions

- Preserve the accepted tracked-search model: a **Watch** remains a tracked search, not a wristwatch entity. Display title, fallback query, raw per-source queries, synonym groups and exclusions retain their distinct semantics. Title matching filters candidates; it does not certify product identity. Do not introduce a nested search DSL or revive hardcoded hardware routes as the category model.
- Reuse acquisition connectors, watch execution, SQLite storage, scheduler, connector health and notification dispatch. Extend their contracts where required; do not add a second scheduler, queue, generic evidence platform or parallel notification service merely to implement the new concepts.
- Separate category-owned identity/preference/comparability rules from shared acquisition, evidence, cost, history and assessment behavior. This spec implements the watch category; later PC and pen work must reuse the shared contracts rather than fork the engines.
- Represent discovery leads, exact configurations, selected-variation bindings, merchant offers, acquisition outcomes, observations, cost scenarios and assessments as distinguishable persisted concepts. One listing can contain multiple offers; namespaced source identifiers do not themselves certify identity or comparability.
- Keep field-level subject, value, issuer, extractor, timestamp, retrieval route, evidence pointer, validity context and derivation lineage. Distinguish manufacturer definitions, seller claims, visible observations, AI inference and human correction. Repeated extraction or copied claims do not provide independent confirmation.
- Resolve configuration identity, merchant-selection binding and comparison qualification separately. Required watch dimensions and conflicting claims must be resolved or explicitly withheld; no confidence score, title equality, first-SKU price or generic stock claim bypasses those gates.
- Persist acquisition outcomes independently from presentation filters and notification events. Store initial, unchanged, rising and falling qualifying observations with capture identity, availability, condition, quantity, destination, currency/cost basis, eligibility and policy versions. Keep failure, partial acquisition, cache reuse and missing periods explicit. Replacement listing snapshots and sparse events are not the history ledger.
- Corrections append lineage and invalidate affected bindings, cohorts, costs, assessments and pending alert eligibility. Preserve original observations and tracking intent; do not relabel historical wrong-variant prices as observations of the corrected product. Publish only assessments valid against their evidence/policy versions, including when acquisition and correction overlap.
- Compute UK cost for an exact offer and buyer scenario, separating merchant-payable amounts from additional import, carrier and payment liabilities. Keep quantities, basket/consignment, destination, dispatch and currency/FX context explicit. Use precise monetary arithmetic; do not default missing amounts or currencies, infer zero costs, or double-count included VAT. No speculative tax engine or hardcoded legal rate is accepted here.
- Use verified-at-observation-time, conditional and unknown cost outcomes. Verification requires every payable component evidenced or supported as inapplicable without material conflicts. Conditional assumptions accompany the amount; materially missing or unbounded components produce unknown total and a known subtotal. Item-price filtering is a discovery prefilter, not a delivered-budget proof.
- Separate coupon opportunity, evidenced terms, applicability and reproduced application. Retain exact basket/destination/selection, eligibility, validity, minimum spend and compatibility. Absence of a prohibition does not prove stacking compatibility. Preserve a valid no-coupon scenario and explain only the checked scope of coupon absence.
- Gate usual obtainable price, current best comparable offer, dated observed low and personal eligible price independently. Every supported claim carries its cohort, coverage, window/date, eligibility, method and version. Defer estimator, numerical windows, sufficiency, freshness and change-detection calibration until qualified longitudinal evidence supports them. Until then show unavailable usual price and no inferred savings percentage; RRP, first capture and same-day surveys are not substitutes.
- Build the approved image-led feed with prominent public delivered-price state, simultaneous candidates, expandable evidence, editable preferences/targets and field/value corrections. Show unknown, disputed, stale, above-target, below-target and outside-preference states distinctly. Retired assessments remain clearly historical. Prototype values are editable examples, not permanent buyer defaults.
- Exact tracking must retain an explicit configuration target alongside existing tracked-search intent; it must not silently rewrite legacy rule behavior. API representations must carry qualification, evidence, coverage and invalidation states through to the UI rather than forcing the UI to infer them from absent fields or a single price.
- Implement the accepted verified-target alert policy: alert on a qualifying crossing; suppress the same offer/price; allow a further drop or a crossing after rising above target. Unknown totals, unresolved identity, withdrawn/stale evidence, corrections and source recovery alone cannot trigger verified bargain alerts. Retain deduplication state across restart and shared acquisition routes. Preserve existing non-discovery notification behavior under regression tests.
- Apply shared admission and cap accounting to discovery and tracking, including retries/fallbacks. Prioritise existing tracking and potential-alert verification; reduce discovery first and expose the resulting coverage gaps. Stop or degrade visibly when required evidence cannot be refreshed. Transport health does not certify semantic offer freshness.
- Keep source capability and permission states explicit. AliExpress browser-first and eBay Browse are reviewed lead lanes, not accepted complete monitoring/history routes; other mandatory source families remain visible with their access and semantic gaps. Staged acquisition work is not implicitly activated by implementing this spec.
- Implement additive migration and compatibility behavior against an isolated database copy, preserving saved rules, scheduling intent and notification settings. Do not operate on the live database or infer that existing rows satisfy new evidence contracts. Exact tables, endpoint names and migration mechanics are implementation design work within these behavioral contracts.

## Testing Decisions

**Accepted seams — buyer confirmed 2026-10-27:** use the existing application API plus normal execution entry point as the primary integration boundary. Supply deterministic connector outcomes, a controlled clock, isolated SQLite storage and a captured notification transport at external edges. Assert observable API/feed data, retained history, tracking state, coverage and dispatched notifications. Add a small browser acceptance layer for the approved buyer workflow. Narrow contract tests are reserved for acquisition adapters and difficult evidence/cost boundaries that cannot be diagnosed adequately at the application seam.

- Good tests verify externally observable behavior and rejection/withholding outcomes, not private method calls, internal class shape or a mirror of arithmetic implementation. Prefer complete workflows through the primary seam over a separate suite for every new concept.
- Prior art includes REST API CRUD/scheduler tests, execution/filter tests, connector fixtures and mocked HTTP responses, browser readiness/selection contracts, frontend payload validation and Watch form tests. Existing examples are patterns to improve on, not proof of coverage: some API fixtures unlink their configured database, so new verification must use an explicitly temporary database and prevent startup schedulers, real connectors and notification transports from reaching production.
- Test discovery outside saved searches, editable compact/colourful/budget preferences, unknown dimensions and discovery-to-exact-tracking alongside preserved legacy rules. Test both simple and advanced matching semantics.
- Use the named cohort: Militado ML05/ML05B, Addiesdive AD2066 mint, San Martin SN0144, Merkur Lightning salmon and Casio MTP-B145D-2A2VEF. Missing real evidence tests abstention; do not substitute an easier product to claim cohort completion.
- Exercise movement, dial, size, revision, strap, accessory, selected-SKU and reference-suffix traps; duplicated leads, generic stock assertions and repeated AI claims must not certify identity.
- Verify new/used separation, auctions versus fixed price, international delivery, quantity/basket changes, included VAT, missing charges, FX context and unknown delivered totals. Legal rules require current authoritative validation before later live use; fixtures do not establish current law.
- Verify coupon expiry, eligibility, minimum spend, exact basket, incompatibility and application-state transitions, including the complete no-coupon path. Fixture coupon success does not establish live success.
- Verify initial/unchanged/increased/decreased captures, partial-source failures, cache reuse, missing periods and cold starts. No fixture date creates real longitudinal history. Withhold usual price and savings until empirical calibration is accepted.
- Verify correction invalidation across comparison/history/total/alerts while retaining lineage and intent. Include stale/conflicting input, overlapping acquisition/correction and historical assessment presentation.
- Verify target crossing, repeat suppression, further drop, rise-and-recross, duplicate routes, restart, interrupted delivery and recovery. Assert the persisted outcome and captured notification, including absence of notifications when qualification is missing.
- Verify caps include retries and fallbacks, discovery yields to tracking/alert verification, last-good evidence is preserved with its age, budget exhaustion differs from empty results, and recovery causes no unbounded catch-up burst.
- Verify migration on seeded isolated legacy data, enabled/disabled schedules, source query/matching configuration, notification settings and rollback/recovery expectations before any later migration approval. No live database test is part of this spec-writing task.
- Browser acceptance covers the illustrated feed, expandable evidence, preference editing, tracking target and correction flow at desktop and narrow widths, including keyboard use. The buyer must distinguish verified payable, conditional and cashback states, missing baseline and alert eligibility. Prototype approval does not substitute for an implemented walkthrough.
- Follow the accepted watch workflow protocol for deterministic receipts and separate live receipts. Report each gate as passed, failed, blocked or unproven with evidence pointers and limitations. No subset of passing tests implies complete source coverage or production acceptance.

## Out of Scope

- PC-parts and fountain-pen delivery, PC build validation and expansion beyond the initial qualified watch cohort/source scope. Later PC discovery retains buyer-approved alternative sets with separate exact histories and explicit unchecked compatibility.
- Personal-benefit execution or account connections: Perks at Work, UNiDAYS, Blue Light, TopCashback/Quidco, gift cards and account credit. Preserve the scenario boundaries without building these integrations for the first release.
- Universal merchant coverage, authentication as evidence of entitlement, authenticity or hidden mechanical-health certification, global/all-time lows, guaranteed cashback or fabricated savings from sparse history.
- Selecting numerical baseline estimators or empirical thresholds without qualified history; inventing request/cost/freshness/retention defaults or operator commitments.
- Source onboarding, credential acquisition, account linking, purchases, seller contact, new infrastructure, live collection, production migrations, activation or deployment as part of spec publication. These require their own concrete authorised scope.

## Further Notes

This spec collapses the accepted planning route into implementation requirements. It does not claim that the system is implemented, the source roster is fully usable, any live UK watch total is qualified, or the complete workflow is proven. `ready-for-agent` means suitable for ticket decomposition/source implementation; it does not grant live operating authority.

Before any live study or recurring activation, present and obtain approval for finite provider/request/page/detail/retry limits, browser concurrency/time, AI usage/spend if applicable, storage/log limits, study duration, spend and operator-time ceilings, source-specific retention/deletion/backup treatment, freshness schedule and a named maintenance/stop-resume owner. Validate entitlements and shared enforcement. The study measures useful coverage, freshness, spend and operator effort; it cannot be assumed to have supplied those numbers already.

Release requires applicable deterministic gates, separately authorised live source/offer/history/cost evidence and buyer walkthrough acceptance. The no-coupon workflow may qualify while coupon-success proof remains explicitly unproven. Missing mandatory source routes keep full-coverage acceptance open. Dates, staffing and capacity remain unset.

The accepted ADR for Watch query/matching remains authoritative. The domain proposal supplies conceptual vocabulary, not a pre-approved physical schema. Closed decision resolutions and their accepted evidence contracts govern detailed qualification; historical proposal text must not override later resolutions.

### Decision and proof references

- [Accepted planning map and decision index](../product/category-discovery/MAP.md)
- [Local decision tracker and resolution records](../product/category-discovery/tickets/README.md)
- [Accepted release scope and deferred operational gates](../product/category-discovery/tickets/release-route.md)
- [Watch workflow acceptance protocol](../product/category-discovery/watch-proof-protocol.md)
- [Source classification and access limitations](../product/category-discovery/source-qualification-decision.md)
- [Identity evidence contract](../product/category-discovery/identity-evidence-research.md)
- [Observation history contract](../product/category-discovery/observation-history-research.md)
- [UK cost evidence contract](../product/category-discovery/uk-cost-research.md)
- [Public discount contract](../product/category-discovery/public-discounts-research.md)
- [Baseline calibration requirements](../product/category-discovery/baseline-policy-research.md)
- [Approved experience and its acceptance limits](../product/category-discovery/tickets/experience-acceptance.md)
- [Disposable experience prototype](../product/category-discovery/experience-prototype.html)
- [Operating study and native reuse](../product/category-discovery/operating-envelope-research.md)
- [Watch query and matching ADR](../adr/0001-watch-query-and-matching-model.md)
