# What evidence would accept the complete watch workflow?

Tracker identity: `watch-proof`  
Parent: [Find the route to trustworthy category deal discovery](../MAP.md)  
Label: `wayfinder:grilling`  
Type: Grilling (HITL)  
Status: closed  
Assignee: jtstothard (Codex; 2026-10-27)  
Blocked by: [Can a buyer understand and correct the watch deal explanation?](experience-acceptance.md), [What collection breadth and freshness are affordable to maintain?](operating-envelope.md), [What evidence makes a UK delivered total defensible?](uk-cost.md), [Which public discount applications and stacks can be verified?](public-discounts.md)

## Question

Does the proposed watch evidence protocol demonstrate the complete path and preserve current monitoring, or what remains unproven before implementation planning?

## Evidence required

Use grilling and domain-modeling with the buyer. Review the vertical-slice protocol, source coverage, contracts and difficult cases. Require a plan for deterministic boundary tests and later live receipts, including history, a verified public-discount case where available, no coupon and unresolved evidence. Separate evidence-protocol acceptance from actually passing it.

Starting context: [source audit](../audit.md), [domain proposal](../domain.md), [product brief](../brief.md), [slice](../vertical-slice.md). These are inputs, not accepted answers.

Experience handoff: the buyer approved [the image-led feed and correction/alert explanation](experience-acceptance.md). Confirm notification frequency/deduplication and the resulting noise policy here after operating constraints are known. Prototype approval does not establish measured usability, permanent condition preferences or live workflow proof.

Operating handoff: [the operating-envelope resolution](operating-envelope.md) accepts native reuse and an explicit-unknown [measurement plan](../operating-envelope-research.md), not an affordable cadence. In the protocol, distinguish required evidence from a later authorised study: user spend/operator-time ceilings, breadth-versus-freshness priority, finite acquisition limits, retention and maintenance ownership must be settled before execution/activation. Require verification of shared cap enforcement, partial-source/last-good preservation, recovery without bursts and semantic freshness separately from transport health. Do not infer these behaviors from existing code or research closure.

## Decision and acceptance gate

User accepts the bounded protocol and claim boundaries, or records changes. No code, mock test pass or discussion closes live proof gaps. Missing coupon success or source access remains explicit. Result is a verification-ready specification, not a statement that the end-to-end workflow already works.

## Resolution comments

### 2026-10-27 — Buyer decisions; protocol discussion remains open

The buyer answered “yes” to each of these recommendations:

- **Two-stage acceptance:** protocol acceptance completes this planning decision and permits the PC-parts challenge; workflow proof requires later deterministic tests and separately authorised live checks. Required proof includes preserved existing tracking, real history, exact UK totals, correction handling and safe failure/recovery. Missing source access, history or reproducible coupon success remains an explicit proof gap. Protocol acceptance does not authorise collection.
- **Alert noise:** one alert on a verified UK delivered total crossing the target; suppress repeats for the same offer/price. Alert again after a further price drop or after the price rises above target and later crosses back below. Corrections, stale evidence and source recovery alone do not trigger bargain alerts. Uncertain discoveries remain visible in the feed.
- **Capacity priority:** existing tracking rules and verification of potential alerts precede discovery breadth. Reduce discovery first, disclose coverage gaps, and withhold alerts whose evidence cannot be refreshed within the cap.

The buyer also answered “yes” to **existing-tracking regression proof**: test saved rules, enabled/disabled state, targets, scheduled checks and notifications, including restart and partial-source failure. Discovery must not silently change those rules, erase last-good evidence or create duplicate alerts. This is a required future proof, not a reported test pass.

The buyer answered “yes” to **operational settings as a mandatory pre-execution gate**: approve finite collection limits, spend/operator-time ceilings, retention, maintenance ownership and freshness schedule before live study or recurring monitoring. Unsupported numerical defaults are not selected now.

Consolidated [the draft watch acceptance protocol](../watch-proof-protocol.md), including deterministic cases, later live receipts, monitoring regressions, coverage and explicit claim limits. Final buyer confirmation is pending.

The ticket remains open pending remaining protocol decisions and final buyer confirmation. Numerical freshness/cadence, spend/operator-time ceilings, finite study limits, retention and maintenance ownership are not approved by these answers. No collection, implementation or activation was performed.


### 2026-10-27 — Resolution: buyer accepted the watch protocol

The buyer answered **“yes”** to final acceptance of [the consolidated watch acceptance protocol](../watch-proof-protocol.md) as the planning specification, with live proof and operational approval outstanding. Accept its required verification cases, evidence receipts, two-stage acceptance, existing-monitoring regression gate, target-crossing/deduplication policy and tracking-first capacity priority. This closes the protocol decision and unblocks the PC-parts design challenge.

The protocol does not report passing implementation tests, live history, complete source coverage, exact current UK totals or coupon success. Numerical operational settings, source rights and separately authorised live execution remain gates. No implementation, collection, activation, commit or push was performed for this decision. Reviewed the remaining fog: no additional sharp decision needs a new ticket; operational choices remain prerequisites in the protocol and existing release-route decision, while category findings await the PC challenge.
