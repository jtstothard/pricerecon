import { ChoiceValue } from './ChoiceValue'
import { useState, type FormEvent } from 'react'
import type { DiscoveryCandidate } from '../../lib/discovery'
import type { ExactTracking } from '../../lib/tracking'
import { productNavigation } from '../../lib/productNavigation'
import {
  correctionPresentationState,
  currentCorrectionSummary,
  identityFields,
  saveCorrection,
  type IdentityField,
} from '../../lib/corrections'

const label = (value: string) => value.replace(/_/g, ' ')
// F5 — one plain-language family for what a correction does to old evidence;
// the precise internal terms stay available as tooltips.
const keptOnRecord = 'kept on record, no longer used for pricing'
const requalificationLabel: Record<string, string> = {
  required: 'waiting for fresh evidence',
  supported_by_fresh_evidence: 'fresh evidence verified',
  not_required: 'no fresh evidence needed',
}
// Same neutral wording as the card, hero and Tracking: a journal whose current
// values mix corrected and disputed entries is "Changed", never upgraded.
function journalHeading(item: DiscoveryCandidate['corrections'][number]) {
  const current = currentCorrectionSummary([item])
  const entries = current.length > 0 ? current : item.lineage
  const state =
    entries.length > 0
      ? correctionPresentationState(entries)
      : item.state === 'corrected'
        ? 'corrected'
        : 'disputed'
  return { corrected: 'Corrected', disputed: 'Disputed', changed: 'Changed' }[state]
}
export function IdentityCorrection({
  candidate,
  tracking = [],
  onSaved,
}: {
  candidate: DiscoveryCandidate
  tracking?: ExactTracking[]
  onSaved: () => Promise<void>
}) {
  const [field, setField] = useState<IdentityField>('dial')
  const [value, setValue] = useState('')
  const [actor, setActor] = useState('')
  const [rationale, setRationale] = useState('')
  const [state, setState] = useState<'corrected' | 'disputed'>('corrected')
  const [selectedId, setSelectedId] = useState(candidate.configurations[0]?.id ?? '')
  const [outcome, setOutcome] = useState<{
    field: IdentityField
    from: string
    to: string
    prevTotal: DiscoveryCandidate['public_total']
  } | null>(null)
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)
  const configuration =
    candidate.configurations.find((c) => c.id === selectedId) ?? candidate.configurations[0]
  const correction =
    candidate.corrections.find((c) => c.configuration_id === configuration?.id) ??
    candidate.corrections[0]
  const original = correction?.original_configuration ?? configuration
  const originalValue = original?.values[field] ?? 'unknown'
  const savedValue = correction?.values[field]
  async function submit(event: FormEvent) {
    event.preventDefault()
    if (!configuration) return
    setSaving(true)
    setError('')
    setOutcome(null)
    try {
      await saveCorrection(candidate.id, correction?.configuration_id ?? configuration.id, {
        capture_id: candidate.capture_id,
        observed_configuration_id: configuration.id,
        configuration_revision: configuration.revision,
        expected_revision: correction?.revision ?? 0,
        field,
        value,
        actor,
        rationale,
        state,
      })
      await onSaved()
      setOutcome({
        field,
        from: originalValue,
        to: value,
        prevTotal: candidate.public_total,
      })
      setValue('')
      setRationale('')
    } catch (failure: unknown) {
      setError(failure instanceof Error ? failure.message : 'Correction could not be saved.')
    } finally {
      setSaving(false)
    }
  }
  const productPath = (view: string) =>
    productNavigation(`/discover/product/${encodeURIComponent(candidate.id)}`, view)
  const invalidatedCoupons = outcome
    ? candidate.offers.flatMap((offer) =>
        offer.coupons.filter((coupon) => coupon.state === 'invalidated')
      )
    : []
  const retainedTargets = tracking.filter((intent) => intent.candidate_id === candidate.id)
  return (
    <section className="identity-correction">
      <h3>Wrong watch details?</h3>
      <p>Spotted a wrong recorded detail? Correct it here — nothing is deleted or overwritten.</p>
      <form onSubmit={submit}>
        {candidate.configurations.length > 1 && (
          <label title="Technical term: observed configuration">
            Observed configuration
            <select
              value={configuration?.id ?? ''}
              onChange={(event) => setSelectedId(event.target.value)}
            >
              {candidate.configurations.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.id}
                </option>
              ))}
            </select>
            <span className="discovery-quiet">Which captured set of details this applies to.</span>
          </label>
        )}
        <label title="Technical term: identity field">
          What's wrong?
          <select
            name="correction_field"
            value={field}
            onChange={(event) => {
              const selected = identityFields.find((option) => option === event.target.value)
              if (selected) {
                setField(selected)
                setValue('')
              }
            }}
          >
            {identityFields.map((option) => (
              <option key={option} value={option}>
                {label(option)}
              </option>
            ))}
          </select>
        </label>
        {/* F2 — the promised original-vs-intended preview must track the live
            form value, so the buyer can verify the change before committing. */}
        <p className="correction-preview" aria-live="polite">
          You are changing <strong>{label(field)}</strong> from <strong>{originalValue}</strong> to{' '}
          <strong className={value ? undefined : 'correction-preview-pending'}>
            {value || '— choose the correct value below —'}
          </strong>
          {savedValue !== undefined && savedValue !== originalValue && (
            <> Last saved value: {savedValue}.</>
          )}
        </p>
        <ChoiceValue
          key={field}
          label="What should it be?"
          name="correction_value"
          required
          placeholder="Choose the correct value…"
          value={value}
          onChange={setValue}
          current={original?.values[field]}
          choices={
            field === 'dial'
              ? ['Blue', 'Green', 'Pink', 'Purple', 'Multicolour', 'Black', 'White']
              : field === 'movement'
                ? ['Quartz', 'Automatic', 'Solar', 'Manual wind']
                : field === 'strap'
                  ? ['Steel', 'Silicone', 'Nylon', 'Leather']
                  : field === 'product_kind'
                    ? ['complete_watch', 'accessory', 'component']
                    : field === 'date_display'
                      ? ['date', 'no_date']
                      : field === 'case_width_mm'
                        ? ['36', '38', '40', '42']
                        : []
          }
        />
        {/* F8 — consequence copy appears at the moment of decision, not
            before the buyer has entered anything. */}
        {value !== '' && (
          <p className="discovery-caution">
            Saving this correction withdraws the prices recorded for the old details — they are{' '}
            {keptOnRecord}, kept in History. Saving records your correction; it does not fetch new
            prices.
          </p>
        )}
        <label title="Technical term: identity state (corrected or disputed)">
          How sure are you?
          <select
            name="correction_state"
            value={state}
            onChange={(event) =>
              setState(event.target.value === 'disputed' ? 'disputed' : 'corrected')
            }
          >
            <option value="corrected">It's fixed — re-check prices</option>
            <option value="disputed">Not sure — pause buying qualification</option>
          </select>
        </label>
        <label>
          Your name
          <input
            required
            maxLength={250}
            name="correction_actor"
            autoComplete="name"
            value={actor}
            onChange={(event) => setActor(event.target.value)}
          />
        </label>
        <ChoiceValue
          label="Reason (recorded with your name in the correction history)"
          name="correction_rationale"
          required
          placeholder="Choose a reason…"
          customLabel="Write your own reason…"
          value={rationale}
          onChange={setRationale}
          choices={[
            'The selected variation differs from this watch.',
            'The source description conflicts with the watch shown.',
            'The recorded specification is incorrect.',
          ]}
        />
        <button type="submit" disabled={saving || !configuration}>
          {saving ? 'Saving correction…' : 'Save correction — old prices will be withdrawn'}
        </button>
      </form>
      {error && <p role="alert">{error} Reload the feed before retrying.</p>}
      {/* F4 — after saving, state what happened BECAUSE of the correction and
          link every dependent surface plus the appended lineage entry. */}
      {outcome && (
        <div role="status" className="correction-outcome">
          <p>
            <strong>Correction saved</strong> — a history entry was added below.
          </p>
          <p>
            Because <strong>{label(outcome.field)}</strong> changed ({outcome.from} →{' '}
            {outcome.to}):
          </p>
          <ul>
            {candidate.public_total.amount === null && (
              <li>
                the delivered total is withheld — now “Total unknown”
                {outcome.prevTotal.amount !== null
                  ? ` (was ${outcome.prevTotal.currency} ${outcome.prevTotal.amount})`
                  : ''}{' '}
                · see <a href={productPath('costs')}>Costs</a>
              </li>
            )}
            {invalidatedCoupons.map((coupon) => (
              <li key={coupon.id}>
                the {coupon.label} coupon result was invalidated (kept as a dated record) · see{' '}
                <a href={productPath('costs')}>Costs</a>
              </li>
            ))}
            <li>
              old observations were marked withdrawn — kept, unchanged, in{' '}
              <a href={productPath('history')}>History</a>
            </li>
            {retainedTargets.map((intent) => (
              <li key={intent.id}>
                your £{intent.target_gbp} target stays saved; alerts wait for fresh evidence for
                this watch · see <a href={productPath('tracking')}>Tracking</a>
              </li>
            ))}
            <li>
              1 entry appended to the correction history (nothing is overwritten) —{' '}
              <a href="#correction-history">see it below</a>
            </li>
          </ul>
        </div>
      )}
      <section id="correction-history">
        <h3>Correction history and provenance</h3>
        <p>Full original evidence and revisions are retained in the Technical tab.</p>
        {candidate.corrections.map((item) => (
          <section key={item.configuration_id}>
            <h3 title={`Technical record: state ${item.state} · requalification ${item.requalification}`}>
              {journalHeading(item)} —{' '}
              {requalificationLabel[item.requalification] ?? label(item.requalification)}
            </h3>
            <p title={`Technical state: ${item.state} · ${item.requalification}`}>
              {item.requalification === 'required'
                ? `Old prices, coupons and buying assessments are ${keptOnRecord}. Your target stays; alerts wait for a fresh matching offer.`
                : 'Fresh matching evidence supports the corrected watch. Original-watch prices remain historical.'}
            </p>
            {/* F6 — a single-field correction must not read as a whole-watch
                rewrite: only the changed fields lead, the full intended
                configuration sits behind an explicit disclosure. */}
            {item.lineage.length > 0 && (
              <p className="correction-changed">
                {item.lineage
                  .map(
                    (entry) =>
                      `${label(entry.field)}: ${entry.original_value ?? 'unknown'} → ${entry.value}`
                  )
                  .join(' · ')}
              </p>
            )}
            <details>
              <summary>Show full intended configuration</summary>
              <dl>
                {Object.entries(item.values).map(([key, current]) => (
                  <div key={key}>
                    <dt>Intended {label(key)}</dt>
                    <dd>{current}</dd>
                  </div>
                ))}
              </dl>
            </details>
            {item.needs.length > 0 && (
              <>
                <p className="discovery-quiet">Waiting for:</p>
                <ul>
                  {item.needs.map((need) => (
                    <li key={need}>{need}</li>
                  ))}
                </ul>
              </>
            )}
            <ol>
              {item.lineage.map((entry) => (
                <li key={entry.id}>
                  <strong>
                    {label(entry.field)}: {entry.original_value ?? 'unknown'} → {entry.value} (
                    {entry.state})
                  </strong>
                  <p>
                    {entry.actor} · {new Date(entry.recorded_at).toLocaleString()}.{' '}
                    {entry.rationale}
                  </p>
                </li>
              ))}
            </ol>
          </section>
        ))}
      </section>
    </section>
  )
}
