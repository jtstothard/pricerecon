# Assumptions, risks and decisions requiring the user

Recommendations below are pending unless explicitly marked confirmed; silence does not accept them. The supplied product requirements stay intact regardless of initial release staging.

## User decisions

| Decision | Recommendation | Consequence / when needed |
| --- | --- | --- |
| Initial audience — confirmed | User selected single-user first during charting | First release serves their own UK buying decisions. Public expansion remains a later decision and brings access/licensing, moderation, privacy and multi-user eligibility boundaries forward. |
| Evidence-collection access envelope | Public/read-only evidence first; list any essential source requiring an account as a blocker for explicit later authorisation | Some coupons/checkout totals cannot be verified. Does not remove AliExpress or personal benefits from scope; avoids assuming credentials exist or may be used. Required before live qualification. |
| Ongoing budget and maintenance tolerance | Set a monthly cost ceiling and operator time envelope after a bounded cost study, then choose cadence/coverage trade-offs | No defensible amount yet. Higher freshness and breadth cost collection, rechecks and maintenance. Required before collection at scale/release; do not invent a budget. |
| Buyer acceptance priorities | Evaluate initial watch cards and uncertain cases together; retain conservative delivered-price alerts | User must decide tolerable noise, condition/risk preferences and how uncertain candidates appear. Agent can prepare evidence, not accept product usability on user's behalf. |

## Risk register

| Risk / assumption | Evidence status and impact | Investigation / mitigation gate |
| --- | --- | --- |
| Access and account requirements | Registry exists; current successful access is unverified. Affiliate/DS/OAuth/browser lanes can need approval, credentials or incur quotas | Source qualification records permitted routes, credential prerequisites, limits, regional/account context and blocked coverage; no credential acquisition in this task. |
| Source drift and unsupported inventory | July receipts are old; some docs overstate readiness, search methods cap results | Route-specific receipts, pagination/cap tests, source-health and coverage reporting; maintenance ownership and retirement policy. |
| History cold start / retention | Table/API present, writer not located; repeat availability evidence absent from audit | Observation design and baseline research must establish actual usable data before discount claims. Sparse history is a visible output state. |
| Identity contamination | Title heuristics can assert exactness; first-SKU extraction and generic spec regexes | Evidence-backed category identity and conflict/correction corpus; independent uncertainty dimensions. |
| False cheap offers | Zero/GBP defaults, unknown shipping, auction/variant ambiguity | Reject unknown monetary/variant context from verified comparisons; qualify adapters before £ delivered alerts. |
| Tax/currency liability | Model is item+shipping, no complete import treatment established | Current authoritative UK rules plus merchant inclusion evidence; no double VAT, no GBP-dispatch inference. |
| Discount compatibility | Coupon text exists, checkout validity/stacking not established | Terms and reproduced exact-basket evidence; alternative scenarios for incompatible benefits; cashback remains uncertain until paid. |
| Sampling bias / market shifts | Search ranking, repeated duplicate merchants and promotion bursts can distort observations | Baseline method comparisons with availability, time gaps, seller diversity, outliers and structural-change cases. |
| Cost and maintenance burden | No measured current per-offer browser, API, AI, storage or operator cost | Bounded measurement plan; propose budgets and graceful degradation before scale. |
| AI inference laundering | Confidence fields lack field-level authority | Evidence lineage, issuer/source distinctions, corrections and dependent-assessment invalidation; photos limited to visible claims. |
| Images, access terms and personal data | Retention/use permission not audited | Research API/merchant terms and lawful evidence/image retention, redaction and deletion needs before storing/sharing receipts or serving public feeds. |
| Preservation of current jobs | Category discovery could overload Watch semantics or change alerts | Compatibility inventory, migration decision if needed and proof of existing tracked-search behaviour in later implementation work. |

## Open questions are not impossibility claims

No live source qualification, reusable historical dataset, watch-direct merchant roster, accepted baseline formula, operating budget or benefit integration is established here. These are investigation gates. The audit does not conclude that any is impossible.
