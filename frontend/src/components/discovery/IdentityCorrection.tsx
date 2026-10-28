import { useState, type FormEvent } from 'react'
import type { DiscoveryCandidate } from '../../lib/discovery'
import { identityFields, saveCorrection, type IdentityField } from '../../lib/corrections'

const label = (value: string) => value.replace(/_/g, ' ')
export function IdentityCorrection({ candidate, onSaved }: { candidate: DiscoveryCandidate; onSaved: () => Promise<void> }) {
  const [field, setField] = useState<IdentityField>('dial')
  const [value, setValue] = useState('')
  const [actor, setActor] = useState('')
  const [rationale, setRationale] = useState('')
  const [state, setState] = useState<'corrected' | 'disputed'>('corrected')
  const [selectedId, setSelectedId] = useState(candidate.configurations[0]?.id ?? '')
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)
  const configuration = candidate.configurations.find(c => c.id === selectedId) ?? candidate.configurations[0]
  const correction = candidate.corrections.find(c => c.configuration_id === configuration?.id) ?? candidate.corrections[0]
  const original = correction?.original_configuration ?? configuration
  async function submit(event: FormEvent) {
    event.preventDefault()
    if (!configuration) return
    setSaving(true); setError(''); setMessage('')
    try {
      await saveCorrection(candidate.id, correction?.configuration_id ?? configuration.id, {
        capture_id: candidate.capture_id, observed_configuration_id: configuration.id,
        configuration_revision: configuration.revision, expected_revision: correction?.revision ?? 0,
        field, value, actor, rationale, state,
      })
      await onSaved()
      setMessage('Correction saved. Old prices stop applying. Your target stays; alerts wait for a matching offer.')
      setValue(''); setRationale('')
    } catch (failure: unknown) {
      setError(failure instanceof Error ? failure.message : 'Correction could not be saved.')
    } finally { setSaving(false) }
  }
  return <details className="identity-correction">
    <summary>Wrong watch details?</summary>
    <p>Old prices stop applying. Your target stays; alerts wait for a matching offer.</p>
    <details><summary>Correction history and provenance</summary>
    <p>Original prices, coupons, assessments and sent alerts remain history. Saving does not fetch a price or change the reference image.</p>
    {candidate.corrections.map(item => <section className="correction-state" key={item.configuration_id}>
      <h3>Identity {item.state} · {label(item.requalification)}</h3>
      <p>Correction revision {item.revision}. {item.requalification === 'required' ? 'Your saved price target stays, but old prices, coupons and buying assessments no longer apply to this watch. Price alerts are paused until fresh matching evidence supports the corrected watch. Saving alone does not fetch a new price or change the reference image.' : 'Fresh matching evidence now supports the corrected watch. Prices for the original watch remain history; they are not prices for the corrected watch.'}</p>
      <dl>{Object.entries(item.values).map(([key, current]) => <div key={key}><dt>Intended {label(key)}</dt><dd>{current}</dd></div>)}</dl>
      <ul>{item.needs.map(need => <li key={need}>{need}</li>)}</ul>
      <ol className="correction-lineage">{item.lineage.map(entry => <li key={entry.id}>
        <strong>{label(entry.field)}: {entry.original_value ?? 'unknown'} → {entry.value} ({entry.state})</strong>
        <p>{entry.actor} · {new Date(entry.recorded_at).toLocaleString()} · revision {entry.revision}. {entry.rationale}</p>
      </li>)}</ol>
    </section>)}
    </details>
    <form onSubmit={submit}>
      {candidate.configurations.length > 1 && <label>Observed configuration<select value={configuration?.id ?? ''} onChange={event => setSelectedId(event.target.value)}>{candidate.configurations.map(c => <option key={c.id} value={c.id}>{c.id}</option>)}</select></label>}
      <label>Identity field<select name="correction_field" value={field} onChange={event => {
        const selected = identityFields.find(option => option === event.target.value)
        if (selected) setField(selected)
      }}>{identityFields.map(option => <option key={option} value={option}>{label(option)}</option>)}</select></label>
      <p>Original acquired {label(field)}: {original?.values[field] ?? 'unknown'}. Intended value: {correction?.values[field] ?? original?.values[field] ?? 'unknown'}.</p>
      <label>Correct value<input required maxLength={500} name="correction_value" value={value} onChange={event => setValue(event.target.value)} /></label>
      <details><summary>Advanced: dispute this identity</summary>
      <label>Identity state<select name="correction_state" value={state} onChange={event => setState(event.target.value === 'disputed' ? 'disputed' : 'corrected')}><option value="corrected">Corrected; fresh evidence required</option><option value="disputed">Disputed; withhold qualification</option></select></label>
      </details>
      <label>Your name<input required maxLength={250} name="correction_actor" autoComplete="name" value={actor} onChange={event => setActor(event.target.value)} /></label>
      <label>Reason<textarea required maxLength={1000} name="correction_rationale" value={rationale} onChange={event => setRationale(event.target.value)} /></label>
      <button type="submit" disabled={saving || !configuration}>{saving ? 'Saving correction…' : 'Save watch details'}</button>
    </form>
    {error && <p role="alert">{error} Reload the feed before retrying.</p>}
    {message && <p role="status">{message}</p>}
    <details className="correction-original"><summary>Original acquired evidence</summary>
      <dl>{Object.entries(original?.values ?? {}).map(([key, current]) => <div key={key}><dt>{label(key)}</dt><dd>{current}</dd></div>)}</dl>
      <ul>{(correction?.original_evidence ?? candidate.offers.flatMap(o => o.evidence)).map((claim, index) => <li key={`${claim.id}:${index}`}>{claim.subject} / {label(claim.field)}: {claim.value}; {claim.issuer_kind}: {claim.issuer}; extractor {claim.extractor}; observed {claim.observed_at ?? 'unknown'}; capture {claim.capture_id}; lineage {claim.derived_from.join(', ')}. {claim.pointer && <a href={claim.pointer} target="_blank" rel="noreferrer">Evidence source</a>}</li>)}</ul>
    </details>
  </details>
}
