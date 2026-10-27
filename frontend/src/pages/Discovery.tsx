import { useEffect, useState, type FormEvent } from 'react'
import { usePageTitle } from '../hooks/usePageTitle'
import { loadDiscovery, savePreferences, type DiscoveryCandidate, type DiscoveryFeed, type PreferenceProfile } from '../lib/discovery'
import '../styles/discovery.css'

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

function Candidate({ candidate }: { candidate: DiscoveryCandidate }) {
  return <article className="discovery-row">
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
      <p className="discovery-caution">Exact identity unresolved</p>
      <p>Movement, size, dial and merchant selection need checking.</p>
      <ul className="discovery-fit">{candidate.preference_fit.filter(fit => fit.state !== 'unset').map(fit => <li key={fit.field}>
        <strong>{strengthLabel[fit.strength]}:</strong> {fit.reason}
      </li>)}</ul>
    </div>
    <div className="discovery-price">
      <div className="discovery-total">Total unknown</div>
      <p>Public UK delivered price</p>
      {candidate.advertised_item_price !== null && <p className="discovery-item-price">
        Item lead: {candidate.reported_currency ?? 'currency unknown'} {candidate.advertised_item_price}
      </p>}
      <p className="discovery-quiet">Usual price unavailable</p>
      <p className="discovery-quiet">No bargain alerts</p>
    </div>
    <details className="discovery-evidence">
      <summary>Price and evidence</summary>
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
        {feed.candidates.map(candidate => <Candidate key={candidate.id} candidate={candidate} />)}
      </div>
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
