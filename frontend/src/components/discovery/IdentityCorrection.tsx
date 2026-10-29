import { ChoiceValue } from './ChoiceValue'
import { useState, type FormEvent } from 'react'
import type { DiscoveryCandidate } from '../../lib/discovery'
import { identityFields, saveCorrection, type IdentityField } from '../../lib/corrections'

const label = (value: string) => value.replace(/_/g, ' ')
export function IdentityCorrection({
  candidate,
  onSaved,
}: {
  candidate: DiscoveryCandidate
  onSaved: () => Promise<void>
}) {
  const [field, setField] = useState<IdentityField>('dial')
  const [value, setValue] = useState('')
  const [actor, setActor] = useState('')
  const [rationale, setRationale] = useState('')
  const [state, setState] = useState<'corrected' | 'disputed'>('corrected')
  const [selectedId, setSelectedId] = useState(candidate.configurations[0]?.id ?? '')
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)
  const configuration =
    candidate.configurations.find((c) => c.id === selectedId) ?? candidate.configurations[0]
  const correction =
    candidate.corrections.find((c) => c.configuration_id === configuration?.id) ??
    candidate.corrections[0]
  const original = correction?.original_configuration ?? configuration
  async function submit(event: FormEvent) {
    event.preventDefault()
    if (!configuration) return
    setSaving(true)
    setError('')
    setMessage('')
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
      setMessage(
        'Correction saved. Old prices stop applying. Your target stays; alerts wait for a matching offer.'
      )
      setValue('')
      setRationale('')
    } catch (failure: unknown) {
      setError(failure instanceof Error ? failure.message : 'Correction could not be saved.')
    } finally {
      setSaving(false)
    }
  }
  return (
    <section className="identity-correction">
      <h3>Wrong watch details?</h3>
      <p>Old prices stop applying. Your target stays; alerts wait for a matching offer.</p>
      <form onSubmit={submit}>
        {candidate.configurations.length > 1 && (
          <label>
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
          </label>
        )}
        <label>
          Identity field
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
        <p>
          Original acquired {label(field)}: {original?.values[field] ?? 'unknown'}. Intended value:{' '}
          {correction?.values[field] ?? original?.values[field] ?? 'unknown'}.
        </p>
        <ChoiceValue
          key={field}
          label="Correct value"
          name="correction_value"
          required
          value={value}
          onChange={setValue}
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
        <section>
          <h3>Correction state</h3>
          <label>
            Identity state
            <select
              name="correction_state"
              value={state}
              onChange={(event) =>
                setState(event.target.value === 'disputed' ? 'disputed' : 'corrected')
              }
            >
              <option value="corrected">Corrected; fresh evidence required</option>
              <option value="disputed">Disputed; withhold qualification</option>
            </select>
          </label>
        </section>
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
          label="Reason"
          name="correction_rationale"
          required
          value={rationale}
          onChange={setRationale}
          choices={[
            'The selected variation differs from this watch.',
            'The source description conflicts with the watch shown.',
            'The recorded specification is incorrect.',
          ]}
        />
        <button type="submit" disabled={saving || !configuration}>
          {saving ? 'Saving correction…' : 'Save watch details'}
        </button>
      </form>
      {error && <p role="alert">{error} Reload the feed before retrying.</p>}
      {message && <p role="status">{message}</p>}
      <section>
        <h3>Correction history and provenance</h3>
        <p>Full original evidence and revisions are retained in Technical.</p>
        {candidate.corrections.map((item) => (
          <section key={item.configuration_id}>
            <h3>
              Identity {item.state} · {label(item.requalification)}
            </h3>
            <p>
              {item.requalification === 'required'
                ? 'Old prices, coupons and buying assessments no longer apply. Your target stays; alerts wait for fresh matching evidence.'
                : 'Fresh matching evidence supports the corrected watch. Original-watch prices remain historical.'}
            </p>
            <dl>
              {Object.entries(item.values).map(([key, current]) => (
                <div key={key}>
                  <dt>Intended {label(key)}</dt>
                  <dd>{current}</dd>
                </div>
              ))}
            </dl>
            <ul>
              {item.needs.map((need) => (
                <li key={need}>{need}</li>
              ))}
            </ul>
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
