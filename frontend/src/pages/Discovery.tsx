import { productNavigation } from '../lib/productNavigation'
import { ChoiceValue } from '../components/discovery/ChoiceValue'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import { DetailRows } from '../components/discovery/DetailRows'
import DiscoveryImage from '../components/discovery/DiscoveryImage'
import { useEffect, useState, type FormEvent } from 'react'
import { usePageTitle } from '../hooks/usePageTitle'
import {
  loadDiscovery,
  savePreferences,
  type DiscoveryCandidate,
  type DiscoveryFeed,
  type PreferenceProfile,
} from '../lib/discovery'
import '../styles/discovery.css'
import ExactTrackingControl, { TrackingStatus } from '../components/ExactTracking'
import type { ExactTracking } from '../lib/tracking'
import { CollectionCoverage } from '../components/discovery/CollectionCoverage'
import { IdentityCorrection } from '../components/discovery/IdentityCorrection'
import { ObservationHistory } from '../components/discovery/ObservationHistory'
import { SourceCoverage, SourceReceipt } from '../components/discovery/SourceCoverage'

const strengthLabel = { hard: 'Hard constraint', soft: 'Soft preference', unset: 'Unset' }

function Preferences({
  profile,
  onSaved,
}: {
  profile: PreferenceProfile
  onSaved: () => Promise<void>
}) {
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
    setSaving(true)
    setError('')
    setMessage('')
    try {
      await savePreferences({
        ...profile,
        values: {
          compact_max_width_mm: width || null,
          compact_strength: compactStrength,
          colourful_dials: colours
            .split(',')
            .map((value) => value.trim())
            .filter(Boolean),
          colourful_strength: colourStrength,
          budget_gbp: budget || null,
          budget_strength: budgetStrength,
        },
      })
      await onSaved()
      setMessage('Preferences saved.')
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : 'Preferences were not saved.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <section className="discovery-preferences">
      <h3>Edit preferences</h3>
      <p>
        Define compact, colourful and your delivered budget. Leave a value blank to keep it unset.
      </p>
      <form onSubmit={submit}>
        <div className="discovery-fields">
          <div>
            <ChoiceValue
              label="Maximum case width (mm)"
              value={width}
              choices={['36', '38', '40', '42']}
              onChange={setWidth}
            />
            <label htmlFor="discovery-width-strength">Width rule</label>
            <select
              id="discovery-width-strength"
              value={compactStrength}
              onChange={(event) =>
                setCompactStrength(event.target.value === 'soft' ? 'soft' : 'hard')
              }
            >
              <option value="hard">Hard constraint</option>
              <option value="soft">Soft preference</option>
            </select>
          </div>
          <div>
            <ChoiceValue
              label="Dial colours"
              value={colours}
              choices={['Blue', 'Green', 'Pink', 'Purple', 'Colourful']}
              onChange={setColours}
            />
            <label htmlFor="discovery-colour-strength">Colour rule</label>
            <select
              id="discovery-colour-strength"
              value={colourStrength}
              onChange={(event) =>
                setColourStrength(event.target.value === 'hard' ? 'hard' : 'soft')
              }
            >
              <option value="soft">Soft preference</option>
              <option value="hard">Hard constraint</option>
            </select>
          </div>
          <div>
            <ChoiceValue
              label="Public UK delivered budget (£)"
              value={budget}
              choices={['100', '150', '200', '300']}
              onChange={setBudget}
            />
            <label htmlFor="discovery-budget-strength">Budget rule</label>
            <select
              id="discovery-budget-strength"
              value={budgetStrength}
              onChange={(event) =>
                setBudgetStrength(event.target.value === 'soft' ? 'soft' : 'hard')
              }
            >
              <option value="hard">Hard constraint</option>
              <option value="soft">Soft preference</option>
            </select>
          </div>
        </div>
        <button type="submit" disabled={saving}>
          {saving ? 'Saving…' : 'Save preferences'}
        </button>
        <span role="status">{message}</span>
        {error && <p role="alert">{error}</p>}
      </form>
      <ul className="discovery-interpretation">
        {profile.interpretation.map((rule) => (
          <li key={rule.field}>
            <strong>{strengthLabel[rule.strength]}.</strong> {rule.meaning}
          </li>
        ))}
      </ul>
      <p className="discovery-quiet">
        Unknown dimensions stay visible for review. They do not satisfy hard constraints or soft
        preferences.
      </p>
    </section>
  )
}

const costStateLabel = {
  verified_at_observation: 'Verified at observation',
  conditional: 'Conditional',
  unknown: 'Total unknown',
}
function subtotals(values: Record<string, string>) {
  return (
    Object.entries(values)
      .map(([currency, value]) => `${currency} ${value}`)
      .join('; ') || 'No separately added evidenced amount'
  )
}
type Cost = DiscoveryCandidate['offers'][number]['cost_scenarios'][number]
function Costs({ costs }: { costs: Cost[] }) {
  return (
    <section>
      <h3>Cost options</h3>
      {costs.length === 0 && (
        <p>No exact-scenario cost evidence supplied. Delivered total unknown.</p>
      )}
      {costs.map((cost) => (
        <section key={cost.id}>
          <h4>
            {cost.kind.replace(/_/g, ' ')}: {costStateLabel[cost.state]}
          </h4>
          <p>
            {cost.withdrawn
              ? 'Historical cost withdrawn. Not a current payable price.'
              : cost.total
                ? `${cost.total.currency} ${cost.total.amount}`
                : 'Total unknown'}
          </p>
          <p>Observed {cost.captured_at}. Freshness unvalidated.</p>
          <DetailRows
            rows={[
              ['Merchant payable', subtotals(cost.merchant_payable)],
              ['Additional liabilities', subtotals(cost.additional_liabilities)],
              [
                'Known subtotal',
                `${subtotals(cost.known_subtotal)}${cost.state === 'unknown' ? '; incomplete, not a delivered total.' : ''}`,
              ],
            ]}
          />
          <p>{cost.assumptions.join('; ')}</p>
          <ul>
            {cost.issues.map((issue, i) => (
              <li key={i}>{issue}</li>
            ))}
          </ul>
          <h4>Charges</h4>
          <DetailRows rows={cost.components.map((part, i) => [
            `${part.kind.replace(/_/g, ' ')} (${i + 1})`,
            `${part.currency ?? ''} ${part.amount ?? 'unknown'}; ${part.state}. ${part.reason}`,
          ])} />
          <h4>Benefits excluded from payable</h4>
          {cost.benefits.map((benefit, i) => (
            <p key={i}>
              {benefit.kind}: {benefit.currency} {benefit.amount}; excluded from payable.{' '}
              {benefit.reason}
            </p>
          ))}
        </section>
      ))}
    </section>
  )
}

export function Candidate({
  candidate,
  tracking,
}: {
  candidate: DiscoveryCandidate
  tracking: ExactTracking[]
  onSaved: () => Promise<void>
}) {
  const path = `/discover/product/${encodeURIComponent(candidate.id)}`
  return (
    <article className="comparison-watch" data-candidate={candidate.id}>
      <DiscoveryImage image={candidate.image} compact />
      <div className="discovery-description">
        <h2>{candidate.title}</h2>
        {candidate.identity_state !== 'supported' && (
          <p className="discovery-caution">Identity {candidate.identity_state}</p>
        )}
        {candidate.preference_fit.some((fit) => fit.state === 'outside') ? (
          <p className="discovery-caution">Outside preferences</p>
        ) : (
          candidate.preference_fit.some((fit) => fit.state === 'unknown') && (
            <p className="discovery-quiet">Preference fit unknown</p>
          )
        )}
        {candidate.corrections.some((c) => c.requalification === 'required') && (
          <p className="discovery-caution">Old prices withdrawn · matching offer needed</p>
        )}
        {candidate.configurations
          .filter((config) => config.state === 'supported')
          .slice(0, 1)
          .map((config) => (
            <p className="discovery-specs" key={config.id}>
              {[
                config.values.strap,
                config.values.case_width_mm && `${config.values.case_width_mm} mm`,
                config.values.movement,
              ]
                .filter(Boolean)
                .join(' · ')}
            </p>
          ))}
      </div>
      <div className="discovery-price">
        <div className="discovery-total">
          {candidate.public_total.amount === null
            ? 'Total unknown'
            : `${candidate.public_total.currency} ${candidate.public_total.amount}`}
        </div>
        {candidate.public_total.amount !== null && (
          <p className="discovery-cost-state">
            {costStateLabel[candidate.public_total.state]} · freshness unvalidated
          </p>
        )}
        <p className="discovery-quiet">UK delivered · no coupon · cashback excluded</p>
      </div>

      <div className="comparison-status">
        {tracking
          .filter((t) => t.candidate_id === candidate.id)
          .map((t) => (
            <p key={t.id}>
              Target £{t.target_gbp} · {t.assessment.state.replace(/_/g, ' ')}
              {t.assessment.reasons.some((r) => /stale|expired/.test(r)) && ' · stale evidence'}
              {t.assessment.reasons.some((r) => /withdrawn|invalidated/.test(r)) &&
                ' · evidence withdrawn'}
            </p>
          ))}
      </div>
      <div className="comparison-actions">
        <a href={productNavigation(path)}>Product details</a>
        <a href={productNavigation(path, 'tracking')}>
          {tracking.some((t) => t.candidate_id === candidate.id)
            ? 'Edit delivered target'
            : 'Track this watch'}
        </a>
      </div>
    </article>
  )
}

export function ProductContent({
  candidate,
  tracking,
  onSaved,
  view,
}: {
  candidate: DiscoveryCandidate
  tracking: ExactTracking[]
  onSaved: () => Promise<void>
  view: string
}) {
  return (
    <div className={`product-content product-view-${view}`}>
      {view === 'overview' && (
        <>
          <h2>Watch specifications</h2>
          <p>Identity {candidate.identity_state}. Unknown specifications remain unresolved.</p>
          {candidate.configurations.map((config) => (
            <section key={config.id}>
              <h3>
                {config.state === 'supported'
                  ? 'Evidenced configuration'
                  : 'Unresolved configuration'}
              </h3>
              <DetailRows
                rows={Object.entries(config.values).map(([field, value]) => [
                  field.replace(/_/g, ' '),
                  value,
                ])}
              />
            </section>
          ))}
          <h3>Preference fit</h3>
          <ul>
            {candidate.preference_fit.map((fit) => (
              <li key={fit.field}>{fit.reason}</li>
            ))}
          </ul>
          <h3>Offers</h3>
          {candidate.offers.map((offer) => (
            <section key={offer.id} aria-label={offer.seller ?? 'Seller unknown'}>
              <h4>{offer.seller ?? 'Seller unknown'}</h4>
              <DetailRows rows={[
                ['Condition', offer.condition ?? 'Unknown'],
                ['Availability', offer.availability ?? 'Unknown'],
                ['Qualification', offer.qualification.state],
                ['Comparison', offer.comparison.state],
              ]} />
            </section>
          ))}
          <p>{candidate.missing_data.join('; ')}</p>
        </>
      )}
      {view === 'costs' && (
        <>
          {' '}
          <h2>UK delivered price</h2>
          <dl>
            <div>
              <dt>Public total, no coupon</dt>
              <dd>
                {candidate.public_total.amount === null
                  ? 'Total unknown'
                  : `${candidate.public_total.currency} ${candidate.public_total.amount}`}{' '}
                — {costStateLabel[candidate.public_total.state]}
              </dd>
            </div>
          </dl>
          <p>{candidate.total_reason}</p>
          <p>{candidate.price_caveat}</p>
          {!tracking.some((intent) =>
            candidate.configurations.some((config) => config.id === intent.configuration_id)
          ) && <p>No bargain alerts until exact tracking and qualification.</p>}
          {candidate.advertised_item_price !== null && (
            <dl>
              <div>
                <dt>
                  {candidate.corrections.some((c) => c.requalification === 'required')
                    ? 'Historical item lead (withdrawn)'
                    : 'Item lead'}
                </dt>
                <dd>
                  {candidate.reported_currency ?? 'currency unknown'}{' '}
                  {candidate.advertised_item_price}
                </dd>
              </div>
            </dl>
          )}
          <p>
            <strong>Missing data:</strong> {candidate.missing_data.join('; ')}.
          </p>
          {candidate.offers.map((offer) => (
            <section key={offer.id}>
              <h3>{offer.seller ?? 'Seller unknown'}</h3>
              <Costs costs={offer.cost_scenarios} />
              <h4>Coupons and conditional benefits</h4>
              {offer.coupons.length === 0 && <p>No verified applicable public coupon supplied.</p>}
              {offer.coupons.map((coupon) => (
                <section key={coupon.id}>
                  <h4>
                    {coupon.label}: {coupon.state.replace(/_/g, ' ')}
                  </h4>
                  <p>{coupon.applicability}</p>
                  <p>{coupon.terms?.literal}</p>
                  {coupon.category !== 'public' && (
                    <p>
                      Conditional benefit excluded from public payable. Cashback is not checkout
                      cash.
                    </p>
                  )}
                  <ul>
                    {coupon.issues.map((issue, i) => (
                      <li key={i}>{issue}</li>
                    ))}
                  </ul>
                  {coupon.resulting_cost && <Costs costs={[coupon.resulting_cost]} />}
                  {coupon.historical_resulting_cost && (
                    <p>
                      Historical coupon result withdrawn; unavailable as a current payable scenario.
                    </p>
                  )}
                </section>
              ))}
            </section>
          ))}
        </>
      )}
      {view === 'history' && (
        <>
          {' '}
          <section>
            <h2>Comparable prices</h2>
            {candidate.price_assessments.length === 0 && (
              <p>
                Comparison unavailable: explicit freshness, eligibility and retained-date policy
                required.
              </p>
            )}
            {candidate.price_assessments.map((item) => (
              <section key={item.id}>
                <h3>{item.historical ? 'Historical assessment' : 'Scoped price assessment'}</h3>
                <p>
                  {item.current_best.state === 'supported' && !item.historical
                    ? `Lowest verified total among offers checked: GBP ${item.current_best.amount}`
                    : 'Current comparison unavailable'}
                  . {item.current_best.reason}
                </p>
                <p>{item.coverage_reason}</p>
                <p>
                  Retained dates {item.window_start} to {item.window_end}. This does not establish
                  current availability.
                </p>
              </section>
            ))}
          </section>
          <p>
            <strong>Usual price unavailable.</strong> {candidate.usual_reason} No savings claim.
          </p>
          <ObservationHistory
            key={`${candidate.capture_id}:${candidate.corrections.map((c) => c.revision).join('-')}`}
            candidateId={candidate.id}
          />
        </>
      )}
      {view === 'technical' && (
        <>
          <h2>Technical evidence</h2>
          <DiscoveryImage image={candidate.image} />
          <dl>
            <div>
              <dt>Source</dt>
              <dd>{candidate.source}</dd>
            </div>
          </dl>
          <p>
            Discovered using “{candidate.query}”. Captured{' '}
            <time dateTime={candidate.captured_at}>
              {new Date(candidate.captured_at).toLocaleString()}
            </time>
            . This capture does not establish current availability.
          </p>
          {candidate.url && (
            <p>
              <a href={candidate.url} target="_blank" rel="noreferrer">
                Open source listing
              </a>{' '}
              (unverified lead)
            </p>
          )}
          <section>
            <h3>Capture lineage</h3>
            <DetailRows rows={[
              ['Capture', candidate.capture_id],
              ['Source listing', candidate.source_listing_id],
              ['Reported source', candidate.reported_source],
            ]} />
            {candidate.evidence.map((evidence) => (
              <section key={evidence.id}>
                <h4>{evidence.field === 'title' ? 'Reported title' : 'Reported item price'}: {evidence.value}</h4>
                <DetailRows rows={[
                  ['Issuer', `${evidence.issuer_kind} from ${evidence.issuer}`],
                  ['Extraction', `${evidence.extractor} via ${evidence.route}`],
                  ['Retrieved', evidence.captured_at],
                  ['Source observation', evidence.source_observed_at ?? 'Unknown'],
                  ['Validity', evidence.validity_context],
                  ['Derived from', evidence.derived_from.join(', ') || 'No parent evidence supplied'],
                ]} />
              </section>
            ))}
          </section>
          <ObservationHistory candidateId={candidate.id} technical />
          <h3>Complete retained record</h3>
          <p>
            Raw provenance, including withdrawn evidence. This record does not establish current
            buying qualification.
          </p>
          <pre>{JSON.stringify(candidate, null, 2)}</pre>
        </>
      )}
      {view === 'correction' && <><h2>Correct watch details</h2><IdentityCorrection candidate={candidate} onSaved={onSaved} /></>}
      {view === 'tracking' && (
        <>
          <h2>Track this exact watch</h2>
          <p>Choose a delivered target. Alerts wait for fresh, qualified evidence for your selected configuration.</p>
          {candidate.configurations.length === 0 && (
            <p>Exact identity unresolved. Resolve watch details before tracking.</p>
          )}
          {candidate.configurations.map((configuration) => (
            <ExactTrackingControl
              key={configuration.id}
              candidate={candidate}
              configuration={configuration}
              intent={tracking.find(
                (t) =>
                  t.configuration_id === configuration.id ||
                  (t.candidate_id === candidate.id &&
                    candidate.corrections.some((c) => c.configuration_id === t.configuration_id))
              )}
              onSaved={onSaved}
            />
          ))}
        </>
      )}
    </div>
  )
}

export function ProductDetail() {
  const { id } = useParams()
  const [params] = useSearchParams()
  const views = ['overview', 'costs', 'history', 'tracking', 'correction', 'technical']
  const requestedView = params.get('view') ?? 'overview'
  const view = views.includes(requestedView) ? requestedView : 'overview'
  const [feed, setFeed] = useState<DiscoveryFeed | null>(null)
  const [error, setError] = useState('')
  async function reload() {
    setFeed(await loadDiscovery())
  }
  useEffect(() => {
    const controller = new AbortController()
    loadDiscovery(controller.signal)
      .then(setFeed)
      .catch((e) => {
        if (!controller.signal.aborted)
          setError(e instanceof Error ? e.message : 'Product could not load.')
      })
    return () => controller.abort()
  }, [id])
  const candidate = feed?.candidates.find((c) => c.id === id)
  usePageTitle(candidate?.title ?? 'Watch details')
  return (
    <div className="discovery-page product-page">
      <a href={productNavigation('/discover')}>Back to comparison</a>
      {error && <p role="alert">{error}</p>}
      {!feed && !error && <p role="status">Loading watch…</p>}
      {feed && !candidate && (
        <p role="alert">Watch not found in the retained feed. Return to comparison.</p>
      )}
      {candidate && (
        <>
          <header className="product-hero" aria-label="Watch buying summary">
            <DiscoveryImage image={candidate.image} compact />
            <div className="product-buying-brief">
              <h1>{candidate.title}</h1>
              {candidate.image.kind === 'remote_reference' && <p className="discovery-caution">{candidate.image.configuration_note}</p>}
              <p className={candidate.identity_state === 'supported' ? 'discovery-quiet' : 'discovery-caution'}>
                Identity {candidate.identity_state}
              </p>
              {candidate.configurations.filter(c => c.state === 'supported').slice(0, 1).map(config => (
                <DetailRows key={config.id} rows={Object.entries(config.values).filter(([field]) => ['dial', 'case_width_mm', 'movement', 'strap'].includes(field)).map(([field, value]) => [field.replace(/_/g, ' '), value])} />
              ))}
              <div className="product-price-summary">
                <p className="product-delivered-label">UK delivered · no coupon</p>
                <p className="product-delivered-price">{candidate.public_total.amount === null ? 'Total unknown' : `${candidate.public_total.currency} ${candidate.public_total.amount}`}</p>
                <p>{costStateLabel[candidate.public_total.state]}. Freshness unvalidated. Cashback excluded.</p>
                <p>Condition: {[...new Set(candidate.offers.map(offer => offer.condition ?? 'Unknown'))].join(', ') || 'Unknown'}</p>
                {candidate.corrections.some(c => c.requalification === 'required') && <p className="discovery-caution">Old prices withdrawn; matching offer needed.</p>}
              </div>
              <Link className="product-track-action" to={productNavigation(`/discover/product/${encodeURIComponent(candidate.id)}`, 'tracking')}>
                {feed?.tracking.some(t => t.candidate_id === candidate.id) ? 'Edit delivered target' : 'Track this watch'}
              </Link>
              {feed?.captures.some(capture => capture.mode === 'offline_verification') && <p className="discovery-caution product-session-note">Synthetic session · prices and buying evidence are test data.</p>}
            </div>
          </header>
          <nav aria-label="Product sections">
            {views.map((item) => (
              <Link
                key={item}
                aria-current={item === view ? 'page' : undefined}
                to={productNavigation(
                  `/discover/product/${encodeURIComponent(candidate.id)}`,
                  item
                )}
              >
                {item.charAt(0).toUpperCase() + item.slice(1)}
              </Link>
            ))}
          </nav>
          <ProductContent
            candidate={candidate}
            tracking={feed?.tracking ?? []}
            onSaved={reload}
            view={view}
          />
        </>
      )}
    </div>
  )
}

export default function Discovery() {
  usePageTitle('Watch discovery')
  const [params] = useSearchParams()
  const requestedView = params.get('view') ?? 'compare'
  const view = ['compare', 'preferences', 'sources', 'tracking'].includes(requestedView)
    ? requestedView
    : 'compare'
  const [feed, setFeed] = useState<DiscoveryFeed | null>(null)
  const [error, setError] = useState('')
  async function reload() {
    setFeed(await loadDiscovery())
  }
  useEffect(() => {
    const controller = new AbortController()
    loadDiscovery(controller.signal)
      .then(setFeed)
      .catch((failure) => {
        if (!controller.signal.aborted)
          setError(failure instanceof Error ? failure.message : 'Discovery could not load.')
      })
    return () => controller.abort()
  }, [])

  return (
    <div className="discovery-page">
      <header>
        <h1 id="page-title" tabIndex={-1}>
          Find your next watch
        </h1>
        <p>Explore wristwatch candidates beyond your saved searches.</p>
      </header>
      {error && <p role="alert">{error}</p>}
      {!feed && !error && <p role="status">Loading watch discovery…</p>}
      {feed && (
        <>
          {feed.captures.some((capture) => capture.mode === 'offline_verification') && (
            <p className="discovery-caution">
              Synthetic session · prices and buying evidence are test data.
            </p>
          )}
          <nav aria-label="Discovery sections">
            <a href={productNavigation('/discover', 'compare')}>Compare watches</a>
            <a href={productNavigation('/discover', 'preferences')}>Preferences</a>
            <a href={productNavigation('/discover', 'tracking')}>Saved targets</a>
            <a href={productNavigation('/discover', 'sources')}>Source coverage</a>
          </nav>
          {view === 'preferences' && <Preferences profile={feed.preferences} onSaved={reload} />}
          {view === 'compare' && (
            <>
              <div className="discovery-feed" aria-label="Watch candidates">
                {feed.candidates.length === 0 && (
                  <p className="discovery-empty">
                    No category candidates collected yet. You can save preferences now; collection
                    remains staged.
                  </p>
                )}
                {feed.candidates.map((candidate) => (
                  <Candidate
                    key={candidate.id}
                    candidate={candidate}
                    tracking={feed.tracking}
                    onSaved={reload}
                  />
                ))}
              </div>
            </>
          )}
          {view === 'tracking' && (
            <section>
              <h2>Saved exact targets</h2>
              {feed.tracking.length === 0 && <p>No exact targets saved yet.</p>}
              {feed.tracking.map((intent) => (
                <section key={intent.id}>
                  <h3>Delivered target £{intent.target_gbp}</h3>
                  <TrackingStatus intent={intent} />
                  <a
                    href={productNavigation(
                      `/discover/product/${encodeURIComponent(intent.candidate_id)}`,
                      'tracking'
                    )}
                  >
                    Review tracked watch
                  </a>
                </section>
              ))}
            </section>
          )}
          {view === 'sources' && (
            <section className="discovery-coverage">
              <h3>Source coverage and collection details</h3>
              <p>{feed.collection_reason}</p>
              <CollectionCoverage />
              <SourceCoverage feed={feed} />
              <p>
                Attempts are retained separately from candidates and preferences. A failed check
                does not refresh an earlier capture or establish that a watch disappeared.
              </p>
              {feed.captures.length === 0 && <p>No collection attempts recorded.</p>}
              {feed.captures.map((capture) => (
                <section key={capture.capture_id}>
                  <h2>{new Date(capture.captured_at).toLocaleString()}</h2>
                  <p>Query: {capture.query}</p>
                  <ul>
                    {capture.outcomes.map((outcome, index) => (
                      <li key={`${outcome.source}-${index}`}>
                        {outcome.source}: {outcome.state.replace(/_/g, ' ')}
                        {outcome.reason ? ` (${outcome.reason.replace(/_/g, ' ')})` : ''};{' '}
                        {outcome.listing_count} leads returned. Source completeness{' '}
                        {outcome.completeness}.
                        {outcome.reused_capture_id && (
                          <p>
                            Reused capture {outcome.reused_capture_id}; no new source observation.
                          </p>
                        )}
                        {outcome.source_evidence && (
                          <SourceReceipt receipt={outcome.source_evidence} />
                        )}
                      </li>
                    ))}
                  </ul>
                </section>
              ))}
            </section>
          )}
        </>
      )}
    </div>
  )
}
