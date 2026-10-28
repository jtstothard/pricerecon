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
