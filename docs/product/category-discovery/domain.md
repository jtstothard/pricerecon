# Proposed domain concepts and ownership

Proposal for investigation, not an accepted schema or ADR. Existing vocabulary lives in [CONTEXT.md](../../../CONTEXT.md); do not redefine its **Watch** (tracked search) as a wristwatch. Use **Tracking rule** in discussion as a possible user-facing term; compatibility/migration remains undecided.

| Concept | Meaning and owner |
| --- | --- |
| Category policy | Category-owned identity dimensions, accessory exclusions, preferences, condition descriptors and comparability rules. Watches, PC parts and pens supply policies to shared services. |
| Product / exact configuration | Product family plus identity-defining configuration. Shared identity service stores category-validated keys, aliases, unresolved alternatives and correction lineage. |
| Merchant offer | Seller's offer for a configuration, condition, quantity and purchase mode in a destination context; distinguish listing, seller, SKU and source IDs. One listing may contain multiple offers. |
| Discovery lead | Search/aggregator/community pointer and claimed information, with origin and timestamp. Shared discovery service follows it to merchant evidence; no authority promotion by copying. |
| Observation / evidence claim | Time-stamped captured assertion, subject, field, value, issuer, retrieval route, evidence pointer and validity context. Shared evidence boundary preserves manufacturer specs, seller claims, extracted observations, AI inferences and human corrections separately. |
| Comparison cohort | Offers whose exact configuration, condition, quantity, destination and eligibility policy permit comparison. Category policy decides equivalence; shared pricing applies it and reports exclusions. |
| Usual obtainable price | Defensible account of repeated comparable genuinely available offers over a recent period; method, coverage, exclusions and sufficiency disclosed. Not RRP, first observation or a chosen formula yet. |
| Current best comparable offer | Lowest defensible current comparable total within explicitly checked supported coverage, with freshness and eligibility. Not market-wide certainty. |
| Observed historical low | Lowest qualifying retained observation within stated coverage/window, date and eligibility. Not an all-time global record. |
| Benefit opportunity / validated application | Discovered discount terms versus a reproducible application to an exact offer and basket. Shared benefit evaluation owns eligibility, compatibility, expiry and evidence status. |
| Cost scenario | Destination, currency/FX observation, item/quantity, discounts, shipping, tax inclusion, import/duty/carrier components and payment assumptions; unknown components remain unknown. Shared costing service owns arithmetic and trace. |
| Deal assessment | Versioned comparison, sufficiency, explanation and uncertainty referencing evidence and policy. Shared ranking cannot turn low-confidence identity into a precise saving. |
| Preference profile / alert rule | Buyer constraints, soft preferences, eligible benefits and desired alert policy, owned by experience/preferences; public and personal comparisons remain separate. |
| Coverage observation | What routes, queries, pages and merchants were attempted, succeeded, capped, blocked or stale, owned by collection/operations. |

## Boundaries to investigate

Reuse connectors as acquisition adapters, the existing scheduler as scheduling substrate, and health/notification machinery where evidence supports reuse. Do not introduce a second scheduler or generic evidence platform merely to name these concepts. Determine whether current SQLite storage and API boundaries suffice before proposing replacement infrastructure.

Acquisition preserves raw claims and context; it does not certify identity. Identity resolves or withholds matches. Costing never fills an unknown with zero or converts currency implicitly. Pricing consumes only qualified comparable observations and records policy versions. Discount evaluation produces alternative compatible scenarios, not a sum of all advertised benefits. Presentation carries these distinctions through feeds and alerts.

Category logic must not fork the collection, cost or provenance engine. Watch identity: reference, generation, case size, movement, dial and strap/bracelet, complete watch versus accessory. PC identity: exact model/generation/capacity/configuration, condition, complete product versus components. Pen identity: model, nib size/material, filling system, finish, pen versus replacement nib. Different condition cohorts can be displayed side by side without treating used as the same market as new.

AI can propose identities, extract specifications and assess visible listing condition. Store the evidence span/image, model/run and uncertainty, conflicts and corrections. Photos do not establish authenticity, hidden mechanical health or invisible specifications. Repeated inference must reference the original claim, not create independent confirmation. Corrections should invalidate affected cohorts, prices and alerts rather than silently rewrite past evidence. Exact retention/versioning design is an open decision.

## Discount and cost presentation contract

Keep four independently labelled outputs: **verified total reproduced** for exact variant/destination/conditions; **conditional total** requiring eligibility; **unverified discount opportunity**; **potential cashback-adjusted effective cost**. The last is uncertain until paid and never a guaranteed checkout reduction. Personal eligible price is user-contextual, with proof/status of eligibility; it need not replace the public comparable price.

A cost trace distinguishes merchant-collected VAT from any additional import liability, UK dispatch from currency, and item-level from consignment/order thresholds. Public coupons may conflict with cashback, membership terms or payment-method offers. Gift cards/account credit are separate payment scenarios, preserving acquisition cost, face value, remaining balance and eligibility implications for later investigation. Do not presume stacking compatibility from absence of a prohibition.
