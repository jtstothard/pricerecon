# Local tracker: investigation graph

This is the child-issue index for [the map](../MAP.md). Local Markdown has no native blocking relation; the explicit **Blocked by** named links in each child file are authoritative. All children carry only their `wayfinder:` label. No implementation backlog is created here.

## Wayfinding operations

- Identity: each ticket's `Tracker identity` within this map; link by title in human narration. Each file is one issue, owned by the parent map.
- Create a ticket file first, then wire named blocker links in a second pass; never guess a GitHub issue number. Keep this derived index aligned with child metadata.
- Claim before working: change Assignee from `unassigned` to the actual dev driving the map. Open assigned issues are not available for concurrent sessions. Re-read the file immediately before claiming; local files have no atomic tracker claim API, so coordinate conflicting sessions.
- Frontier query: read child metadata, select Status `open`, Assignee `unassigned`, and all Blocked-by children Status `closed`; preserve index order. `rg -n '^(Status|Assignee|Blocked by):' docs/product/category-discovery/tickets/*.md` exposes the metadata, then check dependencies. Do not infer readiness from list position alone.
- Resolve: append a dated resolution comment with evidence and assets, close the child, then append its named gist/link to the map. One decision ticket per session, except permitted research work. Charting resolves none.
- Research sessions use the research skill and retained ticket-specific authority. No automatic branch creation/push or account operations follow from a skill. Provider prerequisites remain explicit; current-ticket approval must not be lost behind obsolete per-pass user limits.
- Revisit fog after each resolution, graduate only sharp questions, and update invalidated decisions/dependencies. This is a starting graph, not a frozen build plan.

## Dependencies

Read edges as “requires the closed decisions in the last column.” Source qualification, identity evidence, observation history, UK delivered cost, public discounts, baseline policy, experience acceptance, operating envelope and watch protocol acceptance are closed planning decisions. PC generalisation is closed as a research decision, and buyer-approved PC alternatives are accepted as a planning decision. The buyer accepted deferring PC build validation with explicit unchecked compatibility. The buyer accepted **Which staged release and future benefit boundaries should be approved?**. All decision tickets are closed; the frontier is empty. The planning route is complete, with live proof, operational settings and separate execution authority still required as recorded in that resolution.

| Decision ticket | Type / mode | Blocked by |
| --- | --- | --- |
| [Which source routes can support an honest watch discovery claim?](source-qualification.md) | research / AFK | None |
| [What constitutes an exact configuration and sufficient identity evidence?](identity-evidence.md) | research / AFK | [Which source routes can support an honest watch discovery claim?](source-qualification.md) |
| [What observations can support comparable price history?](observation-history.md) | research / AFK | [What constitutes an exact configuration and sufficient identity evidence?](identity-evidence.md) |
| [What evidence makes a UK delivered total defensible?](uk-cost.md) | research / AFK | [Which source routes can support an honest watch discovery claim?](source-qualification.md), [What constitutes an exact configuration and sufficient identity evidence?](identity-evidence.md) |
| [Which public discount applications and stacks can be verified?](public-discounts.md) | research / AFK | [Which source routes can support an honest watch discovery claim?](source-qualification.md), [What constitutes an exact configuration and sufficient identity evidence?](identity-evidence.md) |
| [When is a usual obtainable price defensible?](baseline-policy.md) | research / AFK | [What observations can support comparable price history?](observation-history.md), [What evidence makes a UK delivered total defensible?](uk-cost.md), [Which public discount applications and stacks can be verified?](public-discounts.md) |
| [Can a buyer understand and correct the watch deal explanation?](experience-acceptance.md) | prototype / HITL | [When is a usual obtainable price defensible?](baseline-policy.md) |
| [What collection breadth and freshness are affordable to maintain?](operating-envelope.md) | research / AFK | [Which source routes can support an honest watch discovery claim?](source-qualification.md), [What observations can support comparable price history?](observation-history.md) |
| [What evidence would accept the complete watch workflow?](watch-proof.md) | grilling / HITL | [Can a buyer understand and correct the watch deal explanation?](experience-acceptance.md), [What collection breadth and freshness are affordable to maintain?](operating-envelope.md), [What evidence makes a UK delivered total defensible?](uk-cost.md), [Which public discount applications and stacks can be verified?](public-discounts.md) |
| [Does the shared design survive PC-parts identity and market cases?](pc-generalisation.md) | research / AFK | [What evidence would accept the complete watch workflow?](watch-proof.md) |
| [Should PC discovery include buyer-approved alternatives?](pc-alternatives.md) | grilling / HITL | [Does the shared design survive PC-parts identity and market cases?](pc-generalisation.md) |
| [What PC compatibility promise should the product make?](pc-compatibility.md) | grilling / HITL | [Does the shared design survive PC-parts identity and market cases?](pc-generalisation.md) |
| [Which staged release and future benefit boundaries should be approved?](release-route.md) | grilling / HITL | [Should PC discovery include buyer-approved alternatives?](pc-alternatives.md), [What PC compatibility promise should the product make?](pc-compatibility.md), [Does the shared design survive PC-parts identity and market cases?](pc-generalisation.md), [What collection breadth and freshness are affordable to maintain?](operating-envelope.md) |

The graph unifies foundation, discovery, discounts and experience: source qualification feeds identity; identity feeds history, UK costing and discounts; those converge on baseline policy; experience and operating constraints converge on watch acceptance; PC generalisation challenges that result before the release-route decision. Parallel investigation is possible only after prerequisites close, not as four simultaneous builds.
