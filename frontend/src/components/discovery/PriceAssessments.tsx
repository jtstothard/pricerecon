import { DetailRows } from './DetailRows'
import { PriceAssessment } from '../../lib/assessments'

function Price({ label, value }: { label: string; value: PriceAssessment['current_best'] }) {
  return <div><p><strong>{label}:</strong> {value.state === 'supported' ? `GBP ${value.amount}` : value.state.replace(/_/g, ' ')}.</p>
    <p>{value.reason} Retained observations: {value.observation_count}.</p>
    {value.paths.map((path, i) => <details key={i}><summary>Observed {new Date(path.observed_at).toLocaleString()} · {path.scenario_kind.replace(/_/g, ' ')}</summary>
      {value.state !== 'supported' && <p>Historical quoted amount: GBP {value.amount}; unavailable as a current buying claim.</p>}
      {path.synthetic && <p>Synthetic verification data; no real market history.</p>}
      <details><summary>Technical evidence</summary>
      <p>Opportunity: <code>{path.offer_key}</code></p>
      <p>Evidence: {path.evidence_ids.join(', ')}</p>
      <ul>{path.dependencies.map((ref, n) => <li key={n}>{ref.kind} {ref.id}, revision {ref.revision}</li>)}</ul>
      </details>
    </details>)}
  </div>
}

export function PriceAssessments({ assessments }: { assessments: PriceAssessment[] }) {
  return <section className="price-assessments" aria-label="Comparable prices">
    <h3>Comparable prices</h3>
    {assessments.length === 0 && <p>Comparison unavailable: explicit freshness, eligibility and retained-date policy required.</p>}
    {[...assessments].reverse().map(item => <details key={`${item.id}:${item.revision}`}>
      <summary>{item.historical ? 'Historical assessment' : 'Scoped price assessment'} · {item.cohort.condition} · quantity {item.cohort.quantity}</summary>
      <p>Assessed {new Date(item.assessed_at).toLocaleString()}. {item.invalidation_reasons.join('; ').replace(/_/g, ' ')}</p>
      <Price label="Lowest verified total among offers checked" value={item.current_best} />
      <p>Retained dates: {new Date(item.window_start).toLocaleString()} to {new Date(item.window_end).toLocaleString()}.</p>
      <Price label="Dated observed low" value={item.observed_low} />
      <p>Usual price unavailable. {item.usual_price.reason} No savings claim.</p>
      <p>Personal price unavailable. {item.personal_price.reason}</p>
      <DetailRows rows={[["Sources checked", item.sources.join(', ')], ["Unchecked sources", item.unchecked_sources.join(', ') || 'none in this declared scope']]} />
      <p>{item.coverage_reason}</p>
      <details><summary>Comparison conditions</summary>
        <dl>{Object.entries(item.cohort).map(([key, value]) => <div key={key}><dt>{key.replace(/_/g, ' ')}</dt><dd>{value}</dd></div>)}</dl>
        <ul>{item.gaps.map((gap, i) => <li key={i}>{gap.start} – {gap.end}: {gap.reason}</li>)}</ul>
        <ul>{item.exclusions.map((excluded, i) => <li key={i}>{excluded.scope}: {excluded.reasons.join('; ').replace(/_/g, ' ')} </li>)}</ul>
      </details>
      <details><summary>Technical evidence</summary>
        <p>Revision {item.revision}</p>
        <p>Method: {item.method}. Policy: {item.policy_version}; supplied evidence age limit {item.max_age} seconds. Scenarios: {item.allowed_scenarios.join(', ')}.</p>
        <p>Policy fingerprint: <code>{item.policy_fingerprint}</code></p>
        <ul>{item.exclusions.map((excluded, i) => <li key={i}>{excluded.scope}: {excluded.observation_id}</li>)}</ul>
      </details>
    </details>)}
  </section>
}
