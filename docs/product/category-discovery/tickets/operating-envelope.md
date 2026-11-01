# What collection breadth and freshness are affordable to maintain?

Tracker identity: `operating-envelope`  
Parent: [Find the route to trustworthy category deal discovery](../MAP.md)  
Label: `wayfinder:research`  
Type: Research (AFK)  
Status: closed  
Assignee: jtstothard (Codex; 2026-10-27)  
Blocked by: [Which source routes can support an honest watch discovery claim?](source-qualification.md), [What observations can support comparable price history?](observation-history.md)

## Question

What operating envelope can sustain discovery, evidence, rechecks and history for the initial user without duplicating native infrastructure?

## Evidence required

Inspect reuse of scheduler/rate limiting/health; estimate only from explicit measurements or current quoted primary-source prices. Design a bounded study of request/page/browser/AI calls, storage/retention, recheck frequency, quotas, failure recovery and operator minutes. Identify secret/account/privacy boundaries, maintenance ownership, drift detection and graceful degradation. No infrastructure installs, service changes or paid experiments.

Starting context: [source audit](../audit.md), [domain proposal](../domain.md), [product brief](../brief.md), [slice](../vertical-slice.md). These are inputs, not accepted answers.

## Decision and acceptance gate

Return costs as measured ranges or unknowns with assumptions, bottlenecks and the learning needed before estimates. User must later choose spend/time limits. Explain how coverage/freshness degrades visibly when capped; separate source transport health from semantic offer qualification.

## Resolution comments

### 2026-10-27 — Research resolution

Accept the [native reuse audit, explicit-unknown accounting model and bounded measurement design](../operating-envelope-research.md) as the planning answer. Reuse the existing scheduler, connector execution, SQLite, health, browser and notification components; no duplicate infrastructure is justified. Sustainable breadth/cadence, monetary costs, storage growth and operator minutes remain unknown, rather than zero or an invented estimate.

The research covers provider/page/browser/AI accounting, retention, quotas, failure recovery, visible capped degradation, privacy and maintenance ownership. Parent review spot-checked scheduler immediate execution, limiter call sites, failed-source handling and snapshot replacement against the working tree. Transport health/watch timestamps do not establish qualified offer freshness; shared limiter enforcement, history writing and safe partial-source preservation are not established. These are later verification/implementation gates, not fixes performed here.

The acceptance gate permits unknown costs with explicit assumptions and learning needed. It is met by this research result; affordability, enforced caps, source rights, live history and production readiness are not accepted. The proposed study requires separate execution authority and finite ceilings. User choices on spend/time, breadth versus freshness, study duration/limits, retention and maintenance ownership remain for the [watch evidence protocol](watch-proof.md) and [staged release boundaries](release-route.md), before any operational activation. No service actions, paid experiments, commits or pushes were performed.
