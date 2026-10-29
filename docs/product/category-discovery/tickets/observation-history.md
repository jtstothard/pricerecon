# What observations can support comparable price history?

Tracker identity: `observation-history`  
Parent: [Find the route to trustworthy category deal discovery](../MAP.md)  
Label: `wayfinder:research`  
Type: Research (AFK)  
Status: closed  
Assignee: jtstothard (Codex; 2026-10-27)  
Blocked by: [What constitutes an exact configuration and sufficient identity evidence?](identity-evidence.md)

## Question

Can the current storage/diff/history paths support an auditable time series, and what evidence must each comparable observation retain?

## Evidence required

Trace every actual history writer or confirm the audit gap; distinguish snapshot/event/imported third-party history. Inventory available retained data without assuming access to a running DB. Define comparable observations with configuration, condition, quantity, destination, currency/FX, availability, eligibility, tax/shipping inclusion, timestamps and provenance. Study stale disappearance versus failed sources, duplicates, correction versions and retention terms.

Starting context: [source audit](../audit.md), [domain proposal](../domain.md), [product brief](../brief.md), [slice](../vertical-slice.md). These are inputs, not accepted answers.

Additional input: [prior watch corpus, manifest and proposed cases](../watch-research-context.md). Use the source conflicts as investigation cases; do not accept the prior evidence labels or prices without reconciliation.

## Decision and acceptance gate

Propose the smallest change boundary and data acquisition plan, including cold start and missing periods. Explain which historical claims are supportable and which withheld. Do not infer historical lows from present snapshots or count duplicated leads as independent observations. No migration or collection service execution.

## Resolution comments

### 2026-10-27 — Resolution: accept the proposed comparable-observation planning contract

Accept the [storage audit and observation evidence contract](../observation-history-research.md) as the history input for downstream planning. Parent review checked the actual diff/event writer, executor failure/filter boundary, repository `price_history` references and chart reader. The inspected application has replacement snapshots and sparse events, not an auditable comparable time series: no application history writer was found; increases, unchanged captures and initial observations are absent from persisted events. Failure or filtering can masquerade as disappearance. This is a source finding, not a claim about deployed rows or external writers.

Retain per-acquisition outcomes and versioned observations separately from alert events and presentation filters. Comparable series require qualified configuration, condition, quantity, destination, monetary/cost basis, eligibility, availability, clocks and provenance. Preserve independent capture identity and shared derivation lineage; corrections invalidate dependent results. Failed/partial/cached sources and missing periods remain explicit gaps. Reuse the existing executor, SQLite and scheduling boundary; an INSERT into the narrow history table alone is insufficient.

Cold start begins with a dated qualified observation, with no usual-price or savings claim. Future observed-low wording must name its retained window and checked coverage; global/all-time lows, continuous availability, completed sale prices and fabricated normal-price savings remain withheld. Source-specific retention permission is a prerequisite for durable collection; no qualifying longitudinal cohort is certified here.

The gate is met for a proposed planning contract and bounded acquisition plan. Deployed inventory, permission-cleared acquisition, cadence, empirical history, UK-cost arithmetic, discount compatibility and baseline sufficiency remain separate gates. No new sharp question falls outside the existing tickets/fog: operating-envelope investigation is now unblocked, while baseline policy still waits on UK cost and public discounts. No implementation, migration, runtime/DB operation, collection, account connection, commit or push was performed by this ticket.

