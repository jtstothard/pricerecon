# Watch discovery prototype: design review

2026-10-27. Analysis using frontend-design of [the disposable walkthrough](experience-prototype.html), its retained 728px render and its HTML/state logic. Design recommendations, not buyer acceptance. No new interaction or accessibility audit was performed.

## Main finding

The prototype exposes evidence rules, but does not yet test the intended buying experience. It leads with instructions, preference prose and scenario navigation, then presents one text-heavy record. A buyer cannot scan competing watches or judge the usefulness and noise of a discovery feed. Using it as the usability acceptance asset would leave the central question untested.

## Priority findings

1. **The discovery experience is absent.** Eight test cases are navigation buttons, not simultaneous candidates. Lead with an illustrated feed containing tracked and newly discovered products, with price and uncertainty visible at a glance. Keep scenario controls in a separate reviewer section.
2. **Information hierarchy puts too much work on the buyer.** Payable price, personal eligibility, cashback, coverage and history compete as paragraphs. The card should answer: which watch, what would I pay, why does it match, what is unresolved, and what can I do? Expand details for arithmetic, exclusions and receipts.
3. **Changed state leaves contradictory evidence visible.** Correction changes the heading but still displays the old payable/benefit text; staleness still leaves current-best wording in the detail. Retain these as explicitly dated previous assessments, visually separated from the current withheld assessment. Do not leave an old verified claim looking current.
4. **Alert qualification is conflated with threshold evaluation.** One hard-coded boolean represents both. The complete £64 public scenario says evidence cannot qualify when it is simply above £60. Distinguish “waiting for price to fall”, “needs verification”, “paused by correction” and “qualifies”. Condition and preference matching also need separate treatment; the width input currently changes copy, not alert eligibility.
5. **Correction is a demonstration button, not a usable correction flow.** It supplies a predetermined 40mm/movement correction. Let the buyer identify the wrong field, enter the correction and see its consequences before confirmation. Show which tracking intent survives, which claims are withdrawn and how requalification happens.
6. **Illustration does not test visual discovery.** The identical small watch schematic cannot communicate dial colour, fit, condition or identity. Use clearly labelled distinct illustrations initially; later test attributable exact-configuration photos. Never let an illustration imply observed product evidence.
7. **Visual language is generic.** Identical rounded outlines give preferences, product, actions and guidance equal weight. Product identity is a dense string joined by separators. Use image-led product rows, quiet metadata, separated price roles and one obvious action. Keep warnings local to the affected claim.
8. **The narrow layout needs deliberate composition.** The definition list remains two columns at all widths; long prose is forced into a narrow value column. Stack detail fields on small screens. The selected scenario has an ARIA state but no designed visual state. Verify focus, contrast and keyboard use during the revision rather than claiming accessibility from markup alone.

## Proposed design direction

A practical collector's comparison desk: watch dials provide the expressive colour; the surrounding interface is quiet and precise. The first view is the actual selection of watches, not a dashboard headline or an explanation of the prototype.

- Palette: paper white #FFFFFF, cool surface #EEF3F5, ink #18333E, secondary text #516873, action blue #215D9C, caution brown #865209. Validate rendered contrast before acceptance; never use colour as the only status signal.
- Type: proposed Source Sans 3 for product names, controls and body, with tabular numerals for prices. Use a local/system fallback until a font asset is available. Suggested scale 13/15/19/28px; left aligned, comfortable line lengths.
- Layout: compact editable request above a feed of product rows; each row pairs a meaningful watch image with exact identity, prominent public delivered total, one match reason, one material caveat and a tracking action. Expand evidence in place. Stack image/title above price/action on mobile.
- Distinction: the watch itself carries the personality. No decorative charts, generic hero numbers, ornamental labels or repeated framed panels.

```text
Compact, colourful, under £150        Edit preferences

[watch] Name / exact configuration     £58 delivered
        36mm · teal · new              Public code applied
        Matches your size limit       Track price
        Checked 12 minutes ago        View evidence

[watch] Newly discovered name          Delivered total unknown
        Orange · size unconfirmed     Check details
        Shipping still needs checking
```

Genericity check: an initial direction based on polished dashboard cards would reproduce the existing hierarchy problem. Revised to a product comparison feed whose expressive elements are watch shape/colour and whose strong typography distinguishes payable money from other benefits. This structure must still support PC parts later; dial-specific decoration must not become shared navigation.

## Next prototype and acceptance

Revise the disposable asset only. Separate the buyer experience from the reviewer controls. Implement feed, expandable price/evidence detail and editable correction, preserving all difficult fixtures. Then ask the buyer to identify payable cost, choose an item, interpret an incomplete candidate and correct an identity without being coached to the intended answer. Observe misunderstandings before asking whether the design is preferred.

The buyer still owns uncertainty placement, used-condition eligibility, compactness meaning, alert frequency and noise tolerance. This review does not settle those choices or close the experience ticket.
