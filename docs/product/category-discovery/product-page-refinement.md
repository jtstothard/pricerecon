# Product page refinement — 2026-10-28

Brief: buyer says comparison is better; product pages need visual hierarchy. Preserve minimal comparison, flat navigation, explicit tracking/correction attribution and honest evidence states. Ticket12 remains open.

## Plan and pre-edit critique

Palette uses existing tokens: Night #0b0f14 (canvas), Slate #111723 (single image surface), Ink #eef2ff (identity/price), Steel #94a3b8 (support), Iris #8796ff (action/focus), Amber #fbbf24 (caution). No new theme, font or dependency.
Existing Geist Variable sans: model title 32–40px/1.1, price 28px, view title 24px, group heading 18px, body 16px/1.6, supporting text 14px. Left aligned; body under 75ch.

Layout: a watch display beside a concise buying brief; flat navigation opens an editorial detail sheet with a distinct view title and ruled fact rows.

```
[ Back to comparison                         ]
[ watch photograph   ][ model / identity      ]
[ reference caption  ][ specs / delivered cost]
[                    ][ condition / Track    ]
[ Overview Costs History Tracking Correction Technical ]
[ View title                                 ]
[ group          | readable fact/value rows   ]
```

On mobile the image, buying brief, navigation and selected sheet stack. The image is the single bold element; no repeated boxed cards or nested disclosures. Price status precedes reasons; technical capture data stays in Technical.

Critique before code: a generic commerce hero alone would leave the rejected details untouched. Revised plan includes explicit view headers, structured offer/condition rows, flattened cost charges and technical lineage rows. Retain uncertainty beside the decision rather than hiding it in provenance. Keep full attribution in Technical and reference warning at the image. No decorative labels, gradients, all-caps or new surfaces. Comparison markup remains untouched.

Verification seam (explicitly requested): mounted direct product route and its navigation/controls; catches content ordering, accessible navigation and continued action routing. Does not prove visual layout, keyboard ergonomics or buyer comprehension. Offline only; no browser/server/live proof authorized.

## Implemented critique and verification

Final pass removed full configuration dumps from the opening brief: only supported dial, case width, movement and strap appear there; complete facts remain in Overview. Specific reference-configuration warnings stay visible. Technical source evidence now uses label/value rows rather than dense paragraphs; original complete records remain available below. One image surface, no new cards, accordions or motion. Product-scoped selectors avoid changing comparison; existing shared token/font system is reused.

TDD: mounted-route test first failed because the buying summary was absent (10 existing tests passed); implementation then passed. It verifies model, condition, primary Track link, summary-before-navigation order, one Overview image, flat views and accessible attribution in Technical. Existing exact target/custom-value/correction attribution/rejection tests remain green.

Final checks: 86 frontend tests across 8 files; TypeScript and Vite production build; git diff --check. Existing >500kB bundle advisory remains. Dependencies installed from lockfile with `npm ci --offline --ignore-scripts`; no new dependency or lockfile edit. No backend or form submission semantics touched, so guarded backend regressions were not repeated. No browser, preview, server, live/network/account, push or PR work. Source and mounted DOM proof only; actual visual/keyboard/narrow usability and buyer acceptance remain pending.

Integration merged before edits (fast-forward to e635f4ad51e0e58faa78e6e00dd7e8dbc8fbc973) and checked/merged again before handoff (already up to date). Integration checkout untouched. Implementation checkout: `/Users/jay/.t3/worktrees/pricerecon/t3-d586f139`, branch `t3/product-page-hierarchy`. Parent owns review, merge and walkthrough rebuild.


## Sole merger product hierarchy review — 2026-10-28

Candidate `23785c6efd85e92da47a8b6ba2300ec0d3958006`, checkout
`/Users/jay/.t3/worktrees/pricerecon/t3-d586f139`, reviewed against expected
integration `e635f4ad51e0e58faa78e6e00dd7e8dbc8fbc973`; merged locally with
`--no-ff` as `569d58984205daf304f8585afca5c4ba9bec6f78`.

Standards: zero blockers against CONTRIBUTING.md and docs/engineering-standard.md.
No unchecked escapes, dependencies, API/source boundaries or backend changes.
Product-scoped CSS uses existing theme tokens with explicit responsive overrides;
mounted-route coverage exercises hierarchy and continued navigation/action routing.

Spec: zero blockers against the product refinement plan/critique, buyer guide and
latest product-only brief. Image/title, supported essential specs, price state,
condition and Track precede flat detail navigation. Comparison markup is unchanged.
Costs, history and technical evidence remain accessible; unknown/conditional and
withdrawn evidence, reference-image warnings and full attribution are retained.
Existing native form controls, arbitrary values and explicit actor/reason behavior
remain intact. No invented specs or nested disclosures/subcards were introduced.
Source review supports responsive intent and specificity coherence, not visual QA.

Independent candidate checks: 86 frontend tests across 8 files, TypeScript/Vite
production build and diff check passed. Merged checks: 21 ProductFlow, Comparison
and IdentityCorrection tests across 3 files plus TypeScript/production build passed.
Node v26.12.1; merged DOM tests used the candidate's installed jsdom through
WATCH_DOM_MODULE without installing dependencies. Existing >500kB bundle advisory
remains. Merge tree exactly equalled candidate before this documentation receipt;
merge diff check passed. Integration started clean with no untracked files and
remained clean after checks; prior tracked receipts were preserved.

Ticket12 remains OPEN: actual buyer retest of product hierarchy/comprehension,
narrow viewport and keyboard usability, tracking/correction and full acceptance
are pending. No browser, preview, server, network/live/account, push, PR, subagents,
reset/clean or sibling writes occurred. Backend checks were not repeated because
backend behavior is unchanged. Parent owns cleanup and walkthrough rebuild.


## Buyer design acceptance — 2026-10-28

After the refined product pages were rebuilt and presented in the existing private
walkthrough, the buyer replied: “Much better, use that”. The current product-page
visual hierarchy and design are accepted and retained as the implementation
baseline (presented integration `914a1a6f12e5367b9529ffaa3483e5ba1d4df1ac`).
This supersedes the pending product-design retest statement above. Preferences/
reload were separately confirmed earlier. Narrow-screen/keyboard testing and the
complete tracking/alert/correction workflow are not established by this design
approval; ticket12 remains open for those remaining checks. No live activation,
production migration, push or publication is authorized by design acceptance.
