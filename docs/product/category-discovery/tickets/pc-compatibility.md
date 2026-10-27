# What PC compatibility promise should the product make?

Tracker identity: `pc-compatibility`  
Parent: [Find the route to trustworthy category deal discovery](../MAP.md)  
Label: `wayfinder:grilling`  
Type: Grilling (HITL)  
Status: closed  
Assignee: jtstothard (Codex; 2026-10-27)  
Blocked by: [Does the shared design survive PC-parts identity and market cases?](pc-generalisation.md)

## Question

Should the first PC scope promise compatibility with a supplied build, or expose specifications and explicit compatibility unknowns without a suitability promise?

## Evidence required

Use grilling and domain-modeling with the buyer. Review socket/firmware, RAM generation/form factor, GPU power/clearance and SSD interface examples in [the PC challenge](../pc-generalisation-research.md). Decide the promise, required buyer context, evidence and abstention behavior, or explicitly defer build validation. No compatibility guarantee follows from exact product identity.

## Decision and acceptance gate

Record the buyer's actual scope choice or explicit deferral, with required evidence and limits for the later implementation brief. Planning acceptance authorises no implementation or live execution.

## Resolution comments

### 2026-10-27 — Claimed; buyer scope discussion open

Reviewed the closed PC generalisation and buyer-approved alternatives decisions. Exact product identity and approved alternative membership do not establish build compatibility. Awaiting the buyer’s choice on the initial compatibility promise; no resolution or implementation authority is inferred.


### 2026-10-27 — Resolution: defer build validation

The buyer answered “yes” to the recommendation that the first PC version show product specifications and explicit compatibility unknowns while deferring build validation. Initial scope supports discovery and price tracking; “compatibility not checked” must remain visible wherever relevant. Exact identity and buyer-approved alternative membership do not establish suitability for a supplied build.

The reviewed examples distinguish an exact GPU/approved alternative from checked case clearance and power requirements, and a matching CPU socket from checked motherboard firmware support. The same boundary applies to RAM generation/form factor and SSD interface/form factor from [the PC challenge](../pc-generalisation-research.md): specifications may inform the buyer, but do not produce a build-fit claim.

Supplying a complete build is not a prerequisite for initial discovery or tracking. Any later build-validation feature requires supplied build details and evidence for each compatibility claim; its detailed validation policy is deferred with that feature. Missing context or checks must remain explicit rather than imply compatibility.

The later implementation brief must demonstrate visible unchecked status and preserve the separation between identity, approved alternatives and build compatibility. This is planning acceptance only, with no implementation or live execution authorised. No new in-scope decision emerged; the existing release-route ticket is now unblocked.
