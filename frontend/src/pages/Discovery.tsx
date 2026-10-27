import { useEffect, useState, type FormEvent } from 'react'
import { usePageTitle } from '../hooks/usePageTitle'
import { loadDiscovery, savePreferences, type DiscoveryCandidate, type DiscoveryFeed, type PreferenceProfile } from '../lib/discovery'
import '../styles/discovery.css'
import ExactTrackingControl, { TrackingStatus } from '../components/ExactTracking'
import type { ExactTracking } from '../lib/tracking'
import { ObservationHistory } from '../components/discovery/ObservationHistory'

const strengthLabel = { hard: 'Hard constraint', soft: 'Soft preference', unset: 'Unset' }

function Preferences({ profile, onSaved }: { profile: PreferenceProfile; onSaved: () => Promise<void> }) {
  const [width, setWidth] = useState(profile.values.compact_max_width_mm ?? '')
  const [colours, setColours] = useState(profile.values.colourful_dials.join(', '))
  const [budget, setBudget] = useState(profile.values.budget_gbp ?? '')
  const [compactStrength, setCompactStrength] = useState(profile.values.compact_strength)
  const [colourStrength, setColourStrength] = useState(profile.values.colourful_strength)
  const [budgetStrength, setBudgetStrength] = useState(profile.values.budget_strength)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')

  async function submit(event: FormEvent) {
    event.preventDefault()
    setSaving(true); setError(''); setMessage('')
    try {
      await savePreferences({ ...profile, values: {
        compact_max_width_mm: width || null, compact_strength: compactStrength,
        colourful_dials: colours.split(',').map(value => value.trim()).filter(Boolean),
        colourful_strength: colourStrength, budget_gbp: budget || null, budget_strength: budgetStrength,
      } })
      await onSaved()
      setMessage('Preferences saved.')
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : 'Preferences were not saved.')
    } finally { setSaving(false) }
  }

  return <details className="discovery-preferences">
    <summary>Edit preferences</summary>
    <p>Define compact, colourful and your delivered budget. Leave a value blank to keep it unset.</p>
    <form onSubmit={submit}>
      <div className="discovery-fields">
        <div>
          <label htmlFor="discovery-width">Compact: maximum case width (mm)</label>
          <input id="discovery-width" type="number" min="0.01" step="any" value={width} onChange={event => setWidth(event.target.value)} />
          <label htmlFor="discovery-width-strength">Width rule</label>
          <select id="discovery-width-strength" value={compactStrength} onChange={event => setCompactStrength(event.target.value === 'soft' ? 'soft' : 'hard')}>
            <option value="hard">Hard constraint</option><option value="soft">Soft preference</option>
          </select>
        </div>
        <div>
          <label htmlFor="discovery-colours">Colourful: dial colours, separated by commas</label>
          <input id="discovery-colours" type="text" value={colours} onChange={event => setColours(event.target.value)} />
          <label htmlFor="discovery-colour-strength">Colour rule</label>
          <select id="discovery-colour-strength" value={colourStrength} onChange={event => setColourStrength(event.target.value === 'hard' ? 'hard' : 'soft')}>
            <option value="soft">Soft preference</option><option value="hard">Hard constraint</option>
          </select>
        </div>
        <div>
          <label htmlFor="discovery-budget">Public UK delivered budget (£)</label>
          <input id="discovery-budget" type="number" min="0.01" step="any" value={budget} onChange={event => setBudget(event.target.value)} />
          <label htmlFor="discovery-budget-strength">Budget rule</label>
          <select id="discovery-budget-strength" value={budgetStrength} onChange={event => setBudgetStrength(event.target.value === 'soft' ? 'soft' : 'hard')}>
            <option value="hard">Hard constraint</option><option value="soft">Soft preference</option>
          </select>
        </div>
      </div>
      <button type="submit" disabled={saving}>{saving ? 'Saving…' : 'Save preferences'}</button>
      <span role="status">{message}</span>{error && <p role="alert">{error}</p>}
    </form>
    <ul className="discovery-interpretation">{profile.interpretation.map(rule => <li key={rule.field}>
      <strong>{strengthLabel[rule.strength]}.</strong> {rule.meaning}
    </li>)}</ul>
    <p className="discovery-quiet">Unknown dimensions stay visible for review. They do not satisfy hard constraints or soft preferences.</p>
  </details>
}

const costStateLabel = { verified_at_observation: 'Verified at observation', conditional: 'Conditional', unknown: 'Total unknown' }
function subtotals(values: Record<string, string>) {
  return Object.entries(values).map(([currency, value]) => `${currency} ${value}`).join('; ') || 'No separately added evidenced amount'
}
type Cost = DiscoveryCandidate['offers'][number]['cost_scenarios'][number]
type CostClaim = Cost['context_evidence'][number]
function CostEvidence({ claims }: { claims: CostClaim[] }) {
  return <details><summary>Cost evidence and provenance ({claims.length})</summary><ul>{claims.map((claim, index) => <li key={`${claim.id}-${index}`}>
    <p>{claim.retention === 'synthetic' ? 'Synthetic test evidence. ' : ''}{claim.issuer_kind}: {claim.issuer}; extractor {claim.extractor} ({claim.extractor_kind}); route {claim.route}; locator {claim.locator}.</p>
    <p>Claim {claim.id}; capture {claim.capture_id}; observed {claim.observed_at ?? 'unknown'}; retrieved {claim.retrieved_at}; effective {claim.effective_at ?? 'not stated'}; expiry {claim.expires_at ?? 'not stated'}.</p>
    <p>Lineage: {claim.derived_from.join(', ')}; input claims: {claim.input_claim_ids.join(', ') || 'none'}; permission {claim.permission_reference}; retention {claim.retention}.</p>
    <dl>{Object.entries(claim.context).map(([field, value]) => <div key={field}><dt>{field.replace(/_/g, ' ')}</dt><dd>{Array.isArray(value) ? value.join(', ') : value ?? 'unknown'}</dd></div>)}</dl>
    {claim.pointer && <a href={claim.pointer} target="_blank" rel="noreferrer">Cost evidence source</a>}
  </li>)}</ul></details>
}
function Costs({ costs }: { costs: Cost[] }) {
  return <details className="discovery-costs"><summary>Delivered cost scenarios ({costs.length})</summary>
    <p>Costs describe the captured buyer scenario. Observation-time verification does not prove current freshness or comparison acceptance. Item lead prices are discovery prefilters.</p>
    {costs.length === 0 && <p>No exact-scenario cost evidence supplied. Legacy normalized totals cannot certify delivered costs.</p>}
    {costs.map(cost => <section key={`${cost.id}-${cost.revision}`}>
      <h4>{cost.kind === 'public_no_coupon' ? 'Public no-coupon' : cost.kind} · {costStateLabel[cost.state]}{cost.total && ` · ${cost.total.currency} ${cost.total.amount}`}</h4>
      <p>Observed capture {cost.captured_at}. Scenario revision {cost.revision}; offer revision {cost.offer_revision}; selection revision {cost.binding_revision}; configuration revision {cost.configuration_revision}; policy {cost.policy_version}. Freshness unvalidated.</p>
      <p>Merchant payable: {subtotals(cost.merchant_payable)}. Additional import/carrier/payment liabilities: {subtotals(cost.additional_liabilities)}.</p>
      <p>Known subtotal: {subtotals(cost.known_subtotal)}{cost.state === 'unknown' ? '; incomplete, not a delivered total.' : '.'}</p>
      {cost.assumptions.length > 0 && <p><strong>Assumptions:</strong> {cost.assumptions.join('; ')}</p>}
      <ul>{cost.issues.map((issue, i) => <li key={i}>{issue}</li>)}</ul>
      <details><summary>Buyer scenario context</summary><dl>{Object.entries(cost.context).map(([field, value]) => <div key={field}><dt>{field.replace(/_/g, ' ')}</dt><dd>{Array.isArray(value) ? value.join(', ') : value ?? 'unknown'}</dd></div>)}</dl></details>
      <CostEvidence claims={cost.context_evidence} />
      <ul>{cost.components.map((part, i) => <li key={`${part.kind}-${i}`}>
        <strong>{part.kind.replace(/_/g, ' ')}: {part.state.replace(/_/g, ' ')}</strong> · {part.currency ?? 'currency unspecified'} {part.amount ?? 'amount absent'} · {part.basis.replace(/_/g, ' ')}{part.included_in && `; included in ${part.included_in.replace(/_/g, ' ')} (counted once)`}
        <p>Payer {part.payer}; collector {part.collector}. {part.reason}</p>
        {part.assumptions.length > 0 && <p><strong>Assumptions:</strong> {part.assumptions.join('; ')}</p>}
        <CostEvidence claims={part.evidence} />
      </li>)}</ul>
      {cost.fx_quotes.map((fx, i) => <div key={i}><p>{fx.purpose.replace(/_/g, ' ')}: 1 {fx.from_currency} → {fx.rate} {fx.to_currency}; {fx.converter}; {fx.state}. Spread included: {fx.spread_included === null ? 'unknown' : String(fx.spread_included)}; rounding {fx.quantum} {fx.rounding}. Customs valuation FX is excluded from buyer payment accounting.</p><p>{fx.assumptions.join('; ')}</p><CostEvidence claims={fx.evidence} /></div>)}
      {cost.benefits.map((benefit, i) => <div key={i}><p><strong>{benefit.kind} {benefit.state}:</strong> {benefit.currency ?? 'currency unknown'} {benefit.amount ?? 'amount unknown'}; excluded from payable. {benefit.reason}</p><CostEvidence claims={benefit.evidence} /></div>)}
    </section>)}
  </details>
}

function Candidate({ candidate, tracking, onSaved }: { candidate: DiscoveryCandidate; tracking: ExactTracking[]; onSaved: () => Promise<void> }) {
  return <article className="discovery-row" data-candidate={candidate.id}>
    <figure className="discovery-picture">
      <svg viewBox="0 0 100 180" role="img" aria-label="Generic watch placeholder, not a product photograph">
        <rect x="32" y="0" width="36" height="180" rx="8" fill="#536b7d" />
        <path d="M33 22h34M33 30h34M33 150h34M33 158h34" stroke="#90a6b4" strokeWidth="2" />
        <rect x="14" y="49" width="72" height="82" rx="33" fill="#b6c6cf" />
        <rect x="86" y="83" width="6" height="13" rx="2" fill="#90a6b4" />
        <circle cx="50" cy="90" r="29" fill="#243a49" />
        <path d="M50 66v5m24 19h-5m-19 24v-5M26 90h5m19-18v18l13 9" stroke="#ebf1f5" strokeWidth="2" fill="none" />
        <circle cx="50" cy="90" r="3" fill="#ebf1f5" />
      </svg>
      <figcaption>Original illustration<br />Not a product photo</figcaption>
    </figure>
    <div className="discovery-description">
      <p className="discovery-quiet">Category discovery from {candidate.source}</p>
      <h2>{candidate.title}</h2>
      <p className="discovery-caution">Configuration {candidate.identity_state}</p>
      <p>Merchant selection and comparison are assessed separately.</p>
      {candidate.offers.map(offer => <p key={offer.id}>{offer.seller ?? 'Seller unknown'} · {offer.condition ?? 'condition unknown'} · {offer.purchase_mode ?? 'purchase mode unknown'}</p>)}
      <ul className="discovery-fit">{candidate.preference_fit.filter(fit => fit.state !== 'unset').map(fit => <li key={fit.field}>
        <strong>{strengthLabel[fit.strength]}:</strong> {fit.reason}
      </li>)}</ul>
    </div>
    <div className="discovery-price">
      <div className="discovery-total">{candidate.public_total.amount === null ? 'Total unknown' : `${candidate.public_total.currency} ${candidate.public_total.amount}`}</div>
      {candidate.public_total.amount !== null && <p className="discovery-cost-state">{costStateLabel[candidate.public_total.state]} · freshness unvalidated</p>}
      <p>Public UK delivered price</p>
      {candidate.advertised_item_price !== null && <p className="discovery-item-price">
        Item lead: {candidate.reported_currency ?? 'currency unknown'} {candidate.advertised_item_price}
      </p>}
      <p className="discovery-quiet">Usual price unavailable</p>
      {!tracking.some(intent => candidate.configurations.some(config => config.id === intent.configuration_id)) && <p className="discovery-quiet">No bargain alerts until exact tracking and qualification.</p>}
    </div>
    <div className="discovery-tracking">{candidate.configurations.map(configuration => <ExactTrackingControl key={configuration.id} candidate={candidate} configuration={configuration}
      intent={tracking.find(intent => intent.configuration_id === configuration.id)} onSaved={onSaved} />)}</div>
    <details className="discovery-evidence">
      <summary>Price and evidence</summary>
      <ObservationHistory candidateId={candidate.id} />
      <div className="discovery-qualification">
        {candidate.configurations.length === 0 && <p>Configuration unresolved: no typed evidence supplied.</p>}
        {candidate.configurations.map(config => <section key={config.id}>
          <h3>Configuration {config.state}</h3>
          <p>Revision {config.revision}; policy {config.policy_version}.</p>
          <dl>{Object.entries(config.values).map(([field, value]) => <div key={field}><dt>{field.replace(/_/g, ' ')}</dt><dd>{value}</dd></div>)}</dl>
          <ul>{config.issues.map((issue, i) => <li key={i}>{issue.field}: {issue.code} {issue.evidence_ids.join(', ')}</li>)}</ul>
        </section>)}
        {candidate.bindings.map(binding => <section key={binding.id}>
          <h3>Selected variation {binding.resolution.state}</h3>
          <p>{binding.merchant_key ?? 'Merchant unknown'} / {binding.product_id ?? 'product unknown'} / {binding.variation_id ?? 'variation unknown'}; binding revision {binding.revision}, configuration revision {binding.configuration_revision}.</p>
          <ul>{binding.resolution.issues.map((issue, i) => <li key={i}>{issue.field}: {issue.code} {issue.evidence_ids.join(', ')}</li>)}</ul>
        </section>)}
        {candidate.offers.map(offer => <section key={offer.id}>
          <h3>Merchant offer {offer.qualification.state}</h3>
          <p>{offer.seller ?? 'Seller unknown'} · {offer.condition ?? 'condition unknown'} · {offer.purchase_mode ?? 'purchase mode unknown'}</p>
          <p>Quantity {offer.quantity ?? 'unknown'}; availability {offer.availability ?? 'unknown'}; destination {offer.destination ?? 'unknown'}. Selected item price: {offer.currency ?? 'currency unknown'} {offer.item_price ?? 'unknown'}.</p>
          {offer.condition_description && <p>Seller condition description: {offer.condition_description}</p>}
          {offer.visible_condition && <p>Visible-condition claim: {offer.visible_condition}</p>}
          <p>Authenticity unknown; internal health unknown. Photos and catalogue claims provide no assurance.</p>
          <p>Comparison {offer.comparison.state}. Cohort: {offer.comparison_cohort ?? 'unresolved'}.</p>
          <ul>{[...offer.qualification.issues, ...offer.comparison.issues].map((issue, i) => <li key={i}>{issue.field}: {issue.code} {issue.evidence_ids.join(', ')}</li>)}</ul>
          <Costs costs={offer.cost_scenarios} />
          <details><summary>Field claims and rejected evidence</summary>
            <ul>{offer.evidence.map((claim, i) => <li key={`${claim.id}-${i}`}>
              <strong>{claim.subject} · {claim.field}:</strong> {claim.value} ({claim.assertion_state})
              <p>{claim.retention === 'synthetic' ? 'Synthetic test evidence. ' : ''}{claim.issuer_kind}: {claim.issuer}; extractor {claim.extractor} ({claim.extractor_kind}); route {claim.route}; locator {claim.locator}.</p>
              <p>Extractor version {claim.extractor_version ?? 'unknown'}; model {claim.extractor_model ?? 'unknown'}; run {claim.extraction_run_id ?? 'unknown'}; uncertainty {claim.uncertainty ?? 'not stated'}. Effective time {claim.effective_at ?? 'unknown'}.</p>
              <p>Claim {claim.id}; capture {claim.capture_id}. Observed {claim.observed_at ?? 'unknown'}; retrieved {claim.retrieved_at}.</p>
              <p>Context: {claim.context.scope}; {claim.context.merchant_key ?? 'merchant unknown'} / {claim.context.product_id ?? 'product unknown'} / {claim.context.variation_id ?? 'variation unknown'}; {claim.context.destination ?? 'destination unknown'}; {claim.context.currency ?? 'currency unknown'}; quantity {claim.context.quantity ?? 'unknown'}.</p>
              <p>Lineage: {claim.derived_from.join(', ')}; input claims: {claim.input_claim_ids.join(', ') || 'none'}. Retention: {claim.retention}; permission: {claim.permission_reference}.</p>
              {claim.pointer && <a href={claim.pointer} target="_blank" rel="noreferrer">Evidence source</a>}
            </li>)}</ul>
          </details>
        </section>)}
      </div>
      <p>{candidate.price_caveat}</p>
      <p>{candidate.total_reason}</p>
      <p><strong>Usual price unavailable.</strong> {candidate.usual_reason} No savings claim.</p>
      <p><strong>Missing data:</strong> {candidate.missing_data.join('; ')}.</p>
      <p>Discovered using “{candidate.query}”. Captured <time dateTime={candidate.captured_at}>{new Date(candidate.captured_at).toLocaleString()}</time>. This capture does not establish current availability.</p>
      <p>{candidate.image.attribution}. {candidate.image.provenance}</p>
      {candidate.url && <p><a href={candidate.url} target="_blank" rel="noreferrer">Open source listing</a> (unverified lead)</p>}
      <details><summary>Capture lineage</summary>
        <p>Capture: <code>{candidate.capture_id}</code>. Source listing: {candidate.source_listing_id}. Connector-reported source: {candidate.reported_source}.</p>
        <ul>{candidate.evidence.map(evidence => <li key={evidence.id}>
          <strong>{evidence.field === 'title' ? 'Reported title' : 'Reported item price'}:</strong> {evidence.value}
          <p>{evidence.issuer_kind} from {evidence.issuer}; extracted by {evidence.extractor} via {evidence.route}.</p>
          <p>Retrieved {new Date(evidence.captured_at).toLocaleString()}; source observation {evidence.source_observed_at ? new Date(evidence.source_observed_at).toLocaleString() : 'unknown'}. {evidence.validity_context}.</p>
          <p>Derived from: <code>{evidence.derived_from.join(', ')}</code></p>
        </li>)}</ul>
      </details>
    </details>
  </article>
}

export default function Discovery() {
  usePageTitle('Watch discovery')
  const [feed, setFeed] = useState<DiscoveryFeed | null>(null)
  const [error, setError] = useState('')
  async function reload() { setFeed(await loadDiscovery()) }
  useEffect(() => {
    const controller = new AbortController()
    loadDiscovery(controller.signal).then(setFeed).catch(failure => {
      if (!controller.signal.aborted) setError(failure instanceof Error ? failure.message : 'Discovery could not load.')
    })
    return () => controller.abort()
  }, [])

  return <div className="discovery-page">
    <header><h1 id="page-title" tabIndex={-1}>Find your next watch</h1>
      <p>Explore wristwatch candidates beyond your saved searches.</p>
    </header>
    {error && <p role="alert">{error}</p>}
    {!feed && !error && <p role="status">Loading watch discovery…</p>}
    {feed && <>
      <p className="discovery-collection">{feed.collection_reason}</p>
      {feed.captures.some(capture => capture.mode === 'offline_verification') && <p className="discovery-caution">Offline verification data. These are test leads, not live merchant evidence.</p>}
      {feed.captures.length > 0 && <p className="discovery-quiet">Latest attempt: {feed.captures[0].outcomes.map(outcome => `${outcome.source} ${outcome.state.replace(/_/g, ' ')}`).join('; ')}. Source completeness unknown. Earlier candidates retain their capture dates.</p>}
      <Preferences profile={feed.preferences} onSaved={reload} />
      <div className="discovery-feed" aria-label="Watch candidates">
        {feed.candidates.length === 0 && <p className="discovery-empty">No category candidates collected yet. You can save preferences now; collection remains staged.</p>}
        {feed.candidates.map(candidate => <Candidate key={candidate.id} candidate={candidate} tracking={feed.tracking} onSaved={reload} />)}
      </div>
      {feed.tracking.filter(intent => !feed.candidates.some(candidate => candidate.configurations.some(config => config.id === intent.configuration_id))).map(intent => <section key={intent.id}>
        <h2>Retained exact tracking</h2><p>Configuration {intent.configuration_id}; original intent retained while source identity needs review.</p><TrackingStatus intent={intent} />
      </section>)}
      <details className="discovery-coverage"><summary>Checked coverage and collection attempts</summary>
        <p>Attempts are retained separately from candidates and preferences. A failed check does not refresh an earlier capture or establish that a watch disappeared.</p>
        {feed.captures.length === 0 && <p>No collection attempts recorded.</p>}
        {feed.captures.map(capture => <section key={capture.capture_id}>
          <h2>{new Date(capture.captured_at).toLocaleString()}</h2><p>Query: {capture.query}</p>
          <ul>{capture.outcomes.map((outcome, index) => <li key={`${outcome.source}-${index}`}>
            {outcome.source}: {outcome.state.replace(/_/g, ' ')}{outcome.reason ? ` (${outcome.reason.replace(/_/g, ' ')})` : ''}; {outcome.listing_count} leads returned. Source completeness unknown.
          </li>)}</ul>
        </section>)}
      </details>
    </>}
  </div>
}
