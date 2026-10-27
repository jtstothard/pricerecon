import { useEffect, useState } from 'react'
import { loadHistory, type ObservationHistory as History } from '../../lib/history'

const label = (value: string) => value.replace(/_/g, ' ')
const stamp = (value: string) => new Date(value).toLocaleString()
const money = (value: Record<string, string>) => Object.entries(value).map(([currency, amount]) => `${currency} ${amount}`).join('; ') || 'none evidenced'

export function ObservationHistory({ candidateId }: { candidateId: string }) {
  const [open, setOpen] = useState(false)
  const [history, setHistory] = useState<History | null>(null)
  const [error, setError] = useState('')
  useEffect(() => {
    if (!open) return
    const controller = new AbortController()
    setError('')
    loadHistory(candidateId, controller.signal).then(setHistory).catch((failure: unknown) => {
      if (!controller.signal.aborted) setError(failure instanceof Error ? failure.message : 'History unavailable')
    })
    return () => controller.abort()
  }, [candidateId, open])
  return <details className="discovery-history" onToggle={event => {
    if (event.target === event.currentTarget) setOpen(event.currentTarget.open)
  }}>
    <summary>Observations and acquisition gaps</summary>
    {error && <p role="alert">{error}</p>}
    {open && !history && !error && <p role="status">Loading retained observations…</p>}
    {history && <>
      <p>Limited retained history. Usual price unavailable. No savings claim. Observations are separate from alert events and acquisition failures.</p>
      <p>{history.coverage_reason}</p>
      <p>As of {stamp(history.as_of)}. {history.last_good
        ? `Last good evidence observed ${stamp(history.last_good.observed_at)}; age ${Math.floor(history.last_good.age_seconds / 3600)} hours. Freshness unvalidated; current price and availability unknown.`
        : 'No qualifying last-good evidence. Current price and availability unknown.'}</p>
      <ol className="discovery-history-observations">{history.observations.map(observation => <li key={observation.id}>
        <h3>{label(observation.change)} · {label(observation.validity)}</h3>
        <p>{observation.evidence_kind === 'synthetic' ? 'Synthetic test evidence; no real longitudinal history. ' : ''}Captured {stamp(observation.captured_at)}; observed {observation.observed_at ? stamp(observation.observed_at) : 'time unknown'}; acquisition {label(observation.acquisition_state)}.</p>
        <p>{observation.offer.seller ?? 'Seller unknown'} · {observation.offer.condition ?? 'condition unknown'} · {observation.offer.purchase_mode ?? 'purchase mode unknown'}; quantity {observation.offer.quantity ?? 'unknown'}; availability at observation {observation.offer.availability ?? 'unknown'}; destination {observation.offer.destination ?? 'unknown'}.</p>
        {observation.duplicate_of && <p>Duplicate acquisition lineage: {observation.duplicate_of}. Does not count as an independent observation.</p>}
        <p>{observation.reasons.map(label).join('; ')}</p>
        {observation.invalidations.map(invalid => <p key={invalid.id}>Qualification withdrawn: {invalid.reason}; {invalid.target.kind} revision {invalid.target.revision}; {stamp(invalid.recorded_at)}; correction {invalid.correction_reference}.</p>)}
        {observation.costs.map(cost => <section key={`${cost.id}:${cost.revision}`}>
          <h4>{label(cost.kind)} · {label(cost.state)}: {cost.total ? `${cost.total.currency} ${cost.total.amount}` : 'Total unknown'}</h4>
          <p>Merchant payable {money(cost.merchant_payable)}; additional liabilities {money(cost.additional_liabilities)}; known subtotal {money(cost.known_subtotal)}. Freshness unvalidated.</p>
          <details><summary>Retained monetary, eligibility and context basis</summary>
            <p>Assumptions: {cost.assumptions.join('; ') || 'none stated'}. Issues: {cost.issues.join('; ') || 'none stated'}.</p>
            <dl>{Object.entries(cost.context).map(([key, value]) => <div key={key}><dt>{label(key)}</dt><dd>{Array.isArray(value) ? value.join(', ') : value ?? 'unknown'}</dd></div>)}</dl>
            <ul>{cost.components.map((component, index) => <li key={index}>{label(component.kind)}: {label(component.state)}; {component.currency ?? ''} {component.amount ?? 'unknown'}; {component.basis}; included in {component.included_in ?? 'no other component'}; payer {component.payer}; collector {component.collector}. {component.reason} {component.assumptions.join('; ')}</li>)}</ul>
            <ul>{cost.benefits.map((benefit, index) => <li key={index}>{benefit.kind}: {benefit.state}; {benefit.currency} {benefit.amount}; excluded from payable. {benefit.reason}</li>)}</ul>
            <ul>{cost.fx_quotes.map((fx, index) => <li key={index}>{fx.purpose}: {fx.from_currency} to {fx.to_currency}; rate {fx.rate}; {fx.direction}; converter {fx.converter}; quantum {fx.quantum}; rounding {fx.rounding}; spread {String(fx.spread_included)}; {fx.state}; {fx.assumptions.join('; ')}</li>)}</ul>
            <ul>{[...cost.context_evidence, ...cost.components.flatMap(c => c.evidence), ...cost.fx_quotes.flatMap(fx => fx.evidence), ...cost.benefits.flatMap(b => b.evidence)].map((claim, index) => <li key={index}>{claim.issuer}; {claim.extractor}; {claim.route}; observed {claim.observed_at ?? 'unknown'}; retrieved {claim.retrieved_at}; capture {claim.capture_id}; lineage {claim.derived_from.join(', ')}; retention {claim.retention}; permission {claim.permission_reference}. {claim.pointer && <a href={claim.pointer} target="_blank" rel="noreferrer">Evidence source</a>}</li>)}</ul>
          </details>
        </section>)}
        <details><summary>Exact revisions, policies and field evidence</summary>
          <p>Capture {observation.capture_id}; configuration {observation.configuration.state}; selection {observation.binding.resolution.state}; offer {observation.offer.qualification.state}.</p>
          <ul>{observation.dependencies.map(ref => <li key={`${ref.kind}:${ref.id}:${ref.revision}`}>{ref.kind} {ref.id}; revision {ref.revision}</li>)}</ul>
          <ul>{Object.entries(observation.policy_versions).map(([key, version]) => <li key={key}>{key}: {version}</li>)}</ul>
          <ul>{observation.offer.evidence.map((claim, index) => <li key={index}>{claim.subject} / {claim.field}: {claim.value} ({claim.assertion_state}); {claim.issuer_kind}: {claim.issuer}; {claim.extractor}; {claim.route}; observed {claim.observed_at ?? 'unknown'}; capture {claim.capture_id}; lineage {claim.derived_from.join(', ')}. {claim.pointer && <a href={claim.pointer} target="_blank" rel="noreferrer">Field evidence source</a>}</li>)}</ul>
        </details>
      </li>)}</ol>
      <h3>Acquisition attempts, separate from observations</h3>
      <ul className="discovery-history-attempts">{history.attempts.map((attempt, index) => <li key={`${attempt.capture_id}:${index}`}>{stamp(attempt.captured_at)}: {attempt.source} {label(attempt.state)}; {attempt.reason}; {attempt.listing_count} leads; completeness {label(attempt.completeness)}; query “{attempt.query}”. {attempt.reused_capture_id && `Reuses capture ${attempt.reused_capture_id}.`}</li>)}</ul>
      <h3>Gaps and unobserved periods</h3>
      <ul className="discovery-history-gaps">{history.gaps.map((gap, index) => <li key={index}>{stamp(gap.start)} – {stamp(gap.end)}: {label(gap.kind)} {gap.state && label(gap.state)}. {gap.reason}</li>)}</ul>
    </>}
  </details>
}
