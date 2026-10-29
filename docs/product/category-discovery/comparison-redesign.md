# Watch comparison redesign — 2026-10-28

Buyer feedback: too much simultaneous data; a comparison is needed, with details on a product page. Cards/subcards were inconsistent, nesting was unacceptable, and manual forms felt daunting. This supersedes the earlier accordion-based overload treatment. Ticket12 remains open for buyer retest.

The buyer's task is to find their next watch: compare appearance first, then delivered price, fit, movement and strap. The comparison uses one repeated structure, with no subcards: image/caption, model, up to three evidenced specifications, public delivered-price state, concise identity/withdrawal/target warning, and two navigation actions. No source identifiers, correction form, provenance or price-history dump appears there. Missing images remain honestly unavailable; existing real photographs and reference images retain their distinction and provenance. No new imagery or specifications are invented.

Design contract: existing Geist type and theme, left aligned text, quiet borders, no decorative motion. Existing palette tokens supply background #0b0f14, raised surface #111723, text #eef2ff, muted text #94a3b8 and accent #6d7dff (the active theme remains authoritative). Use 12/20/28px spacing, image-led equal columns on desktop, two columns at medium widths and one on narrow screens. Keep the watch image as the distinctive element. Review against the brief removed the previous stack of disclosures and subcards rather than simply relocating it.

Layout sketch:

    Compare watches | Preferences | Saved targets | Source coverage
    [watch image]      [watch image]      [watch image]
    Model              Model              Model
    Strap / size / movement, when supported
    Delivered price + qualification / unknown
    Product details    Track this watch

    Product: model / delivered-price state
    Overview | Costs | History | Tracking | Correction | Technical
    One selected flat view, no nested disclosure controls

Product route: `/discover/product/:id`, selected by the stable candidate ID from `/api/discovery/watches`; loading it directly or reloading fetches the feed and selects that candidate. Unknown IDs and API errors are explicit. `?view=overview|costs|history|tracking|correction|technical` selects the page section. Existing app SPA fallback serves direct routes when the frontend is built. Recognized `walkthrough` image mode persists across links, including local-only mode; these links never silently enable remote images.

Overview curates evidenced watch values, preference fit and offer status. Costs curates payable components, unknown charges, conditions and coupon states. History shows scoped assessment summaries and an explicitly loaded retained-observation table. Tracking retains existing exact-configuration writes, revisions, notification choices, rejection handling and delivery reconciliation. Correction offers known field/state/value/reason choices and explicit custom paths, with the buyer's required name. Choosing a reason explicitly is attribution, never a silently generated explanation. Presets preserve arbitrary saved values. Technical provides source links, capture lineage, the complete retained candidate record and an explicitly loaded complete history record. Technical is intentionally verbose and contains raw provenance; it has no disclosure nesting or card stack.

Backend qualification remains unchanged: observation-time verification is not current freshness; unknown and conditional prices do not become qualified totals; corrections withdraw dependent claims; cashback stays excluded from payable. Legacy Watch monitoring is unchanged.

Verification uses rendered component behavior and the existing guarded application API/execution seam, not private backend methods. DOM tests run with the pinned jsdom dev dependency installed offline; `WATCH_DOM_MODULE` optionally selects an existing local installation. No browser/server/live source/account access was used. Buyer visual usability, keyboard walkthrough at actual viewports, real-source freshness, and shopping acceptance remain unproven; the redesign needs a buyer retest.

Validation result: 85 frontend tests passed across 8 files, including mounted React navigation/form/error tests; TypeScript and Vite production build passed. `npm ci --offline --ignore-scripts` succeeded with the pinned DOM dependency. The 47 guarded discovery/tracking/correction backend tests passed using the existing project virtualenv. `git diff --check` passed. Vite retains its large-chunk advisory (approximately 685 kB main bundle); no bundle limit was weakened. No visual/browser acceptance was performed.
