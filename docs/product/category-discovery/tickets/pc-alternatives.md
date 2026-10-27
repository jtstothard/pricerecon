# Should PC discovery include buyer-approved alternatives?

Tracker identity: `pc-alternatives`  
Parent: [Find the route to trustworthy category deal discovery](../MAP.md)  
Label: `wayfinder:grilling`  
Type: Grilling (HITL)  
Status: closed  
Assignee: jtstothard (Codex; 2026-10-27)  
Blocked by: [Does the shared design survive PC-parts identity and market cases?](pc-generalisation.md)

## Question

Should the first PC discovery scope compare only exact configurations, or also offer named buyer-approved alternative sets?

## Evidence required

Use grilling and domain-modeling with the buyer. Review concrete GPU board and RAM-kit cases in [the PC challenge](../pc-generalisation-research.md). Decide the first scope, who approves membership/exclusions and how alternatives are explained. Exact histories must remain distinct; approval of alternatives cannot establish identical goods or pooled usual-price claims.

## Decision and acceptance gate

Record the buyer's actual scope choice or explicit deferral, with required evidence and limits for the later implementation brief. Planning acceptance authorises no implementation or live execution.

## Resolution comments

### 2026-10-27 — Resolution: buyer-approved alternatives included

The buyer explicitly accepted all three proposals in the live exchange:

- Initial PC discovery includes named buyer-approved alternative sets alongside exact configurations. Each member retains its exact identity and separate price history; prices are never pooled into one usual-price or savings claim.
- The product may suggest candidates, but only explicit buyer approval adds membership. The buyer controls exclusions and requirements, such as GPU dimensions or factory-matched RAM kits.
- Approved alternatives may qualify for alerts when the buyer enables tracking for the set. Each alert names the exact product, explains why it qualifies and uses that product's own price evidence. Adding a candidate alone does not trigger a deal alert.

Concrete cases reviewed: several approved RTX 4060 Ti 16GB board models may be alternatives while 8GB models remain excluded; a 2×16GB RAM kit remains distinct from one 32GB module. These illustrate the approved policy, not actual approved product membership. Explanations must preserve product differences and the buyer's acceptance requirements.

The later implementation brief must demonstrate suggestion versus approved membership, buyer exclusions, distinct exact histories, product-specific explanations and alert evidence, enabled-set tracking and suppression of membership-only alerts. Existing identity, UK cost, baseline and alert evidence gates continue to apply. Alternative-set approval establishes neither identical goods nor compatibility with a build; [What PC compatibility promise should the product make?](pc-compatibility.md) remains a separate decision.

Terminology: [Buyer-approved alternative set](../../../../GLOSSARY.md). This is planning acceptance only; no implementation or live execution is authorised or proven. No new sharp decision emerged beyond the existing compatibility and release-route tickets; the map's remaining fog is unchanged.
