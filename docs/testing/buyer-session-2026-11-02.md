# Buyer comprehension session record — 2026-11-02

**The human-comprehension gate is NOT fully cleared by this session.** The buyer
(Jay) ran a **compressed** comprehension pass against the ticket12 synthetic
fixture: the trust-essential honesty spot-checks **S1–S5 plus the four trust
clusters** received direct buyer judgment this session. **S5 was not completed**
(the buyer stopped at it — see the verdicts and triage below) and the **full
33-task session (clusters A1–K2) per the
[buyer walkthrough kit](buyer-walkthrough.md) remains with the buyer.** Nothing
here signs for more than the buyer actually judged; the acknowledgement slots at
the end are left for him to complete.

## 1. Session setup

- **Application under test:** served from **main @ `9470105`** ("Adversarial
  walkthrough: run record + fixes for the honesty-contract breaches it found").
- **Fixture:** the ticket12 synthetic walkthrough fixture — **zero outbound**
  (no live provider or remote image requests), **temporary SQLite**, **paused
  scheduler**, marker-gated edges. This is the same guarded fixture mode the
  [kit](buyer-walkthrough.md) prescribes; all amounts, evidence and prices in
  the session were fixture data, and the session banner marked them as such.
- **Fixture service:** the long-running fixture instance on reserved port
  **8896** served the session and was **left running untouched** afterwards (the
  buyer may still have been using it). Ports 8893–8895 were likewise untouched.
- **Session shape:** compressed — the buyer drove the UI himself and reported
  verdicts in his own words, recorded verbatim below. This was not the full
  kit script; fixture-step order and the verdict form were not exercised.

## 2. Buyer verdicts — verbatim

Preserved exactly as the buyer wrote them, including wording and typos.

| Spot-check | Buyer's verdict (verbatim) |
| --- | --- |
| S1 — fixture/synthetic provenance is marked, fail-closed | "only one watch has a price claim, the rest are Total unknown" |
| S2 — missing costs block totals | "as above, this seems aggressively conservative" |
| S3 — savings never render from sparse history | "Looks fine" |
| S4 — expired/conflicting coupons withhold | "Looks fine" |
| S5 — corrections invalidate dependents and retain lineage | "didnt do as it is confusing" |

**Noticed by the buyer (verbatim):**

> "i noticed a few problems too, only 1 watch had a photo, the rest placeholder.
> the technical tab changes the background colkour too"

## 3. Triage — 2026-11-02

**(a) S2 ("aggressively conservative") — judged stark-but-correct; recorded as
buyer feedback, not a defect.** Fail-closed withholding is working as designed:
in an evidence-sparse fixture the honest answer to "what does this cost" is
"Total unknown", and showing less than the evidence supports is the contract.
The buyer's reaction is still signal: a softer presentation that leads with
*what we do know* (the known-subtotal lines) before the withheld total could
make the same withholding read less blunt. That is a presentation idea for a
future pass — **not a contract change**; the fail-closed behaviour stays.

**(b) Photos mostly placeholder — session mode, not a product defect.** The
zero-outbound fixture mode blocks remote image fetches by design, so only the
one locally-provided watch photo loaded and the rest showed the honest
placeholder ("Product image unavailable. Generic placeholder; does not depict
this watch."). In live use the attributed merchant images load. No fix
required; the placeholder behaviour is the correct fail-closed surface.

**(c) Technical-tab background change — real cosmetic defect; fixed in this
branch.** Reproduced and root-caused: the `.app-shell` decorative radial
gradients used unsized `circle` layers whose farthest-corner extent scales with
the element box, so the ~4× taller Technical tab stretched the corner washes
over the whole page and visibly shifted the background colour. Fixed with
explicit fixed-size gradient radii — styling only, no content change — in
commit **`0c4ca57`** on `t3/buyer-session-2026-11-02`, with a regression test
(`frontend/src/components/__tests__/ProductTabBackground.test.jsx`) locking
container consistency across all six product tabs and fixed-size wash layers.

**(d) S5 "didnt do as it is confusing" — recorded as a comprehension finding,
not a pass and not a contract failure.** The buyer found the correction flow
confusing and did not complete the S5 spot-check. The S5 fail-closed contracts
themselves remain suite-proven and adversarially exercised (see the
[adversarial run of 2026-11-01](walkthrough-adversarial-run-2026-11-01.md));
what is missing is the buyer's own comprehension of that flow. A clarity fix
is **pending the buyer's description of what specifically confused him**; no
change is made speculatively.

## 4. Gate status after this session

- **Received direct buyer judgment this session (compressed pass):** S1–S4 and
  the four trust clusters.
- **Still open with the buyer:** **S5** (not completed — correction flow found
  confusing) and the **full 33-task session (A1–K2)** with its per-cluster
  verdicts and the signed overall verdict form.
- This record therefore **does not claim full human-comprehension gate
  clearance**. It records a real, buyer-worded data point on the trust-essential
  surface plus three triaged observations, one of which produced the styling fix
  in commit `0c4ca57`.
- As always, per the kit's "do not conclude" list: nothing here establishes live
  offer obtainability, live delivered totals, live coupon success, history or
  savings calibration, operating limits, release maturity, or live manufacturer
  provenance.

## 5. Acknowledgement

The buyer acknowledges that the verdicts in section 2 are his own words from
his own session against the ticket12 synthetic fixture, and that the triage in
section 3 records his observations accurately (including which spot-checks he
did and did not complete).

- Buyer (Jay): signature / acknowledgement: ____________________  Date: __________
- Recorded by: agent session, 2026-11-02 · Application revision: main @ `9470105` ·
  Fix commit: `t3/buyer-session-2026-11-02` @ `0c4ca57`
