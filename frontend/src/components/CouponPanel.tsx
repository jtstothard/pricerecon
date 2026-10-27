import type { ReactNode } from 'react'
import type { DiscoveryCoupon } from '../lib/discovery'

const labels = {
  unverified_opportunity: 'Unverified opportunity', conditional_eligibility: 'Conditional eligibility',
  applicable_not_reproduced: 'Applicable; application not reproduced', reproduced_at_observation: 'Reproduced at observation',
  rejected: 'Rejected', invalidated: 'Invalidated',
}

type Evidence = DiscoveryCoupon['opportunity_evidence']
function EvidenceList({ claims }: { claims: Evidence }) {
  return <details><summary>Coupon evidence and provenance ({claims.length})</summary><ul>{claims.map((claim, i) => <li key={`${claim.id}-${i}`}>
    {claim.retention === 'synthetic' && <strong>Synthetic checkout evidence. </strong>}
    {claim.issuer} ({claim.issuer_kind}); {claim.extractor} ({claim.extractor_kind}); observed {claim.observed_at ?? 'unknown'}; retrieved {claim.retrieved_at}; route {claim.route}; capture {claim.capture_id}; locator {claim.locator}.
    <p>Derivation: {claim.derived_from.join(', ')}; input claims: {claim.input_claim_ids.join(', ') || 'none'}. Permission {claim.permission_reference}; retention {claim.retention}.</p>
    {claim.pointer && <a href={claim.pointer} target="_blank" rel="noreferrer">Coupon evidence source</a>}
  </li>)}</ul></details>
}

export function CouponPanel({ coupons, renderCost }: {
  coupons: DiscoveryCoupon[]
  renderCost: (cost: NonNullable<DiscoveryCoupon['resulting_cost']>) => ReactNode
}) {
  const reproduced = coupons.some(coupon => coupon.category === 'public' && coupon.state === 'reproduced_at_observation')
  return <details className="discovery-coupons"><summary>Public coupons and conditional benefits ({coupons.length})</summary>
    <p>The public no-coupon delivered total remains available above. Only supplied acquisition evidence was checked; freshness is unvalidated.</p>
    {!reproduced && <p>No verified applicable public coupon in supplied acquisition evidence. Other routes and live checkout remain unchecked.</p>}
    {coupons.map(coupon => <section key={`${coupon.id}-${coupon.revision}`}>
      <h4>{coupon.label} · {coupon.category} · {labels[coupon.state]}</h4>
      {coupon.resulting_cost?.total && <p><strong>Separate coupon payable: {coupon.resulting_cost.total.currency} {coupon.resulting_cost.total.amount}</strong> · {coupon.resulting_cost.context.purchase_scope === 'whole_basket' ? 'whole basket commitment' : 'exact selected scenario'} · verified at observation only.</p>}
      <p>Applicability {coupon.applicability}; lineage {coupon.lineage}. Captured {coupon.captured_at}; coupon revision {coupon.revision}; offer {coupon.offer_revision}; selection {coupon.binding_revision}; configuration {coupon.configuration_revision}; policy {coupon.policy_version}.</p>
      {coupon.category !== 'public' && <p>Separate conditional {coupon.category} scenario; excluded from public payable. Cashback is uncertain and is not checkout cash.</p>}
      <ul>{coupon.issues.map((issue, i) => <li key={i}>{issue}</li>)}</ul>
      {coupon.terms && <>
        <p>{coupon.terms.literal}</p>
        <p>Codes in application order: {coupon.terms.codes.join(' → ')}. Compatibility {coupon.terms.compatibility}: {coupon.terms.combination_rule ?? 'unknown'}. Silence does not establish stack compatibility.</p>
        <p>Minimum spend: {coupon.terms.minimum_currency ?? 'unknown currency'} {coupon.terms.minimum_spend ?? 'unknown'} ({coupon.terms.minimum_inclusive === null ? 'boundary unknown' : coupon.terms.minimum_inclusive ? 'inclusive' : 'exclusive'}); basis {coupon.terms.minimum_basis ?? 'unknown'}. Quantity {coupon.terms.min_quantity ?? 'unknown'}–{coupon.terms.max_quantity ?? 'unknown'}.</p>
        <p>Validity: {coupon.terms.starts_at ?? 'start unknown'} ({coupon.terms.start_inclusive === null ? 'boundary unknown' : coupon.terms.start_inclusive ? 'inclusive' : 'exclusive'}) to {coupon.terms.ends_at ?? 'expiry unknown'} ({coupon.terms.end_inclusive === null ? 'boundary unknown' : coupon.terms.end_inclusive ? 'inclusive' : 'exclusive'}); source zone {coupon.terms.time_zone_literal ?? 'unknown'}.</p>
        <p>Channel {coupon.terms.channel}; new customer {coupon.terms.new_customer}; membership {coupon.terms.membership}; redemption {coupon.terms.redemption}.</p>
        <EvidenceList claims={[...coupon.terms.evidence, ...coupon.terms.compatibility_evidence]} />
      </>}
      {coupon.eligibility && <><p>Eligibility: {coupon.eligibility.reason}. Eligible base {coupon.eligibility.currency} {coupon.eligibility.eligible_base}; eligible lines {coupon.eligibility.eligible_members.join(', ')}; excluded lines {coupon.eligibility.excluded_members.join(', ') || 'none'}.</p><EvidenceList claims={coupon.eligibility.evidence} /></>}
      {coupon.application && <>
        <p>{coupon.application.evidence.some(claim => claim.retention === 'synthetic') && 'Synthetic checkout evidence. '}Reproduction receipt {coupon.application.result}; {coupon.application.currency} {coupon.application.before_total} before → {coupon.application.quoted_total} quoted. Applied {coupon.application.applied_codes.join(' → ')}; other promotions {coupon.application.other_promotions.join(', ') || 'none'}.</p>
        <ul>{coupon.application.lines.map((line, i) => <li key={i}>{line.member} × {line.quantity}: {line.currency} {line.before_item_total} → {line.after_item_total}; {line.eligible ? 'eligible' : 'excluded'}; {line.applied_codes.join(', ') || 'no code allocation'}</li>)}</ul>
        <EvidenceList claims={coupon.application.evidence} />
      </>}
      {coupon.resulting_cost && renderCost(coupon.resulting_cost)}
      {coupon.historical_resulting_cost && <p>Historical result retained: {coupon.historical_resulting_cost.total?.currency} {coupon.historical_resulting_cost.total?.amount}. Invalidated; unavailable as a current payable scenario.</p>}
      <details><summary>Exact coupon basket and destination</summary><dl>{Object.entries(coupon.context).map(([field, value]) => <div key={field}><dt>{field.replace(/_/g, ' ')}</dt><dd>{Array.isArray(value) ? value.join(', ') : value ?? 'unknown'}</dd></div>)}</dl></details>
      <EvidenceList claims={coupon.opportunity_evidence} />
    </section>)}
    <p>Application evidence describes the observed basket and time. It does not establish current availability or usual-price savings. No bargain alerts are enabled.</p>
  </details>
}
