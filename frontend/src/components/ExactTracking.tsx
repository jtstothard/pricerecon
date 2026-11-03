import { ChoiceValue } from './discovery/ChoiceValue'
import { DetailRows } from './discovery/DetailRows'
import { useEffect, useState, type FormEvent } from 'react'
import {
  channels,
  loadDeliveries,
  resolveDelivery,
  saveTracking,
  type Delivery,
  trackingStateLabel,
  type ExactTracking,
  type TrackingChannel,
} from '../lib/tracking'
import type { DiscoveryCandidate } from '../lib/discovery'
import { correctionPresentationState, currentCorrectionSummary } from '../lib/corrections'

const reasons: Record<string, string> = {
  policy_required: 'Freshness and buyer eligibility policy have not been supplied.',
  target_changed_requires_observation: 'Target changed; waiting for a new qualified observation.',
  baseline_recorded: 'First qualified observation recorded; waiting for a qualifying price change.',
  target_crossing: 'Verified delivered total crossed your target.',
  further_drop: 'A further qualifying delivered-price drop.',
  duplicate_offer_price: 'Same offer and price, or no further drop; repeat alert suppressed.',
  duplicate_or_older_evidence: 'Duplicate or older evidence; no new alert.',
  above_target: 'Verified at observation, above your delivered target.',
  evidence_stale_or_expired: 'Evidence is stale or expired; a fresh check is required.',
  evidence_invalidated: 'Prior evidence no longer applies; target retained.',
  preferences_changed_requires_observation:
    'Preferences changed; waiting for a qualified observation.',
  preference_mismatch_or_unknown:
    'This offer does not satisfy the stated preferences, or fit is unknown.',
  public_delivered_total_unverified: 'The public UK delivered total is unknown or conditional.',
  exact_configuration_unresolved_or_changed:
    'Exact identity is unresolved or differs from your tracked configuration.',
  selected_offer_unqualified: 'Merchant selection or offer evidence is unresolved.',
  offer_unavailable_or_not_buy_now: 'Offer is unavailable or lacks a fixed buy-now price.',
  buyer_eligibility_mismatch:
    'Quantity, condition, destination or payment differs from the supplied policy.',
  source_evidence_unavailable:
    'No qualifying source evidence was acquired; earlier evidence remains historical.',
  delivery_in_flight_or_interrupted:
    'A delivery is in flight or interrupted. Its external result may be unknown.',
  delivery_resolved_requires_observation: 'Delivery reconciled; waiting for a new observation.',
  offer_revision_changed_requires_observation:
    'Offer evidence changed; waiting for a new decision.',
  conflicting_route_totals:
    'Acquisition routes disagree about the same offer total; alert withheld.',
  acquisition_partial_or_reused:
    'Acquisition is partial or reuses a cached capture; a fresh complete check is required.',
  evidence_revision_withdrawn: 'Supporting evidence no longer applies; alert withheld.',
}

export function TrackingStatus({ intent }: { intent: ExactTracking }) {
  return (
    <div className="exact-tracking-state" role="status">
      <strong>
        {trackingStateLabel[intent.assessment.state]} · target £{intent.target_gbp} delivered
      </strong>
      {intent.assessment.delivered_gbp !== null && (
        <p>Assessed delivered total £{intent.assessment.delivered_gbp}.</p>
      )}
      {intent.assessment.reasons.some(
        (reason) => reason.includes('stale') || reason.includes('expired')
      ) && <p className="discovery-caution">Stale evidence · alerts wait for a fresh offer</p>}
      {/* Neutral on purpose: a disputed save or a bare revision withdrawal also
          lands here, so the wording must not claim the evidence was "corrected". */}
      {intent.assessment.reasons.some(
        (reason) => reason.includes('invalidated') || reason.includes('withdrawn')
      ) && (
        <p className="discovery-caution" title="Technical state: evidence invalidated">
          Prior evidence no longer applies — kept on record, no longer used for alerts · target
          retained
        </p>
      )}
      <section>
        <h3>Alert eligibility details</h3>
        <ul>
          {intent.assessment.reasons.map((reason) => (
            <li key={reason}>{reasons[reason] ?? reason.replace(/_/g, ' ')}</li>
          ))}
        </ul>
        {intent.assessment.assessed_at && (
          <p>Assessed {new Date(intent.assessment.assessed_at).toLocaleString()}.</p>
        )}
        {intent.assessment.valid_until && (
          <p>Evidence limit: {new Date(intent.assessment.valid_until).toLocaleString()}.</p>
        )}
        <section>
          <h3>Technical evidence</h3>
          <p>Policy: {intent.assessment.policy_version ?? 'not supplied'}</p>
        </section>
      </section>
    </div>
  )
}

function DeliveryRecords({
  intent,
  onSaved,
}: {
  intent: ExactTracking
  onSaved: () => Promise<void>
}) {
  const [deliveries, setDeliveries] = useState<Delivery[]>([])
  const [error, setError] = useState('')
  const [confirmed, setConfirmed] = useState(false)
  const [busy, setBusy] = useState(false)
  async function reload() {
    try {
      setDeliveries(await loadDeliveries(intent.id))
      setError('')
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : 'Delivery records could not load.')
    }
  }
  async function reconcile(
    eventId: number,
    channel: TrackingChannel,
    resolution: 'record_sent' | 'abandon'
  ) {
    setBusy(true)
    try {
      await resolveDelivery(intent, eventId, channel, resolution)
      await onSaved()
      await reload()
      setConfirmed(false)
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : 'Reconciliation failed.')
    } finally {
      setBusy(false)
    }
  }
  return (
    <section className="exact-tracking-deliveries">
      <button type="button" onClick={() => void reload()}>
        Load records
      </button>
      <h3>Notification delivery records</h3>
      <p>
        External send/ack crashes can leave delivery unknown. Ambiguous attempts are not retried
        automatically; exactly-once delivery is not guaranteed.
      </p>
      {error && <p role="alert">{error}</p>}
      {deliveries.length === 0 && <p>No target notifications recorded.</p>}
      {deliveries.map((delivery) => (
        <section key={delivery.event_id}>
          <p>
            £{delivery.delivered_gbp} · {delivery.reason.replace(/_/g, ' ')} ·{' '}
            {delivery.status.replace(/_/g, ' ')}
          </p>
          {delivery.channels.map(({ channel, status }) => (
            <div key={channel}>
              <p>
                {channel}: {status.replace(/_/g, ' ')}
              </p>
              {['failed', 'dispatching'].includes(status) && (
                <>
                  <label>
                    <input
                      type="checkbox"
                      checked={confirmed}
                      onChange={(event) => setConfirmed(event.target.checked)}
                    />
                    I have stopped the sending process and confirmed no send is in flight.
                  </label>
                  <button
                    disabled={!confirmed || busy}
                    onClick={() => void reconcile(delivery.event_id, channel, 'record_sent')}
                  >
                    Record as received
                  </button>
                  <button
                    disabled={!confirmed || busy}
                    onClick={() => void reconcile(delivery.event_id, channel, 'abandon')}
                  >
                    Abandon ambiguous attempt
                  </button>
                  <p>These actions record your resolution and never resend the message.</p>
                </>
              )}
            </div>
          ))}
        </section>
      ))}
    </section>
  )
}

export default function ExactTrackingControl({
  candidate,
  configuration,
  intent,
  onSaved,
}: {
  candidate: DiscoveryCandidate
  configuration: DiscoveryCandidate['configurations'][number]
  intent?: ExactTracking
  onSaved: () => Promise<void>
}) {
  const [target, setTarget] = useState(intent?.target_gbp ?? '')
  const [selected, setSelected] = useState<TrackingChannel[]>(intent?.notifications.channels ?? [])
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const correction = candidate.corrections.find(
    (item) => item.configuration_id === configuration.id && item.requalification === 'required'
  )
  const correctedValues = currentCorrectionSummary(correction ? [correction] : [])
  const retainedConfiguration = correction?.original_configuration ?? configuration
  const detailsLabel = {
    corrected: 'Corrected details',
    disputed: 'Disputed details',
    changed: 'Changed details',
  }[correctionPresentationState(correctedValues)]
  useEffect(() => {
    setTarget(intent?.target_gbp ?? '')
    setSelected(intent?.notifications.channels ?? [])
  }, [intent?.revision])
  async function submit(event: FormEvent) {
    event.preventDefault()
    setSaving(true)
    setError('')
    setMessage('')
    try {
      await saveTracking(
        {
          candidate_id: candidate.id,
          capture_id: candidate.capture_id,
          configuration_id: configuration.id,
          configuration_revision: configuration.revision,
          target_gbp: target,
          notifications: { channels: selected },
        },
        intent
      )
      await onSaved()
      setMessage('Delivered target saved. Collection remains staged.')
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : 'Target was not saved.')
    } finally {
      setSaving(false)
    }
  }
  return (
    <div className="exact-tracking" data-configuration={configuration.id}>
      {intent && <TrackingStatus intent={intent} />}
      <section className="exact-tracking-editor">
        <h3>{intent ? 'Edit delivered target' : 'Track this watch'}</h3>
        <h3>
          Tracked watch{correctedValues.length > 0 ? ' — retained observation' : ''}
        </h3>
        {correctedValues.length > 0 && (
          <p>Details as originally observed; kept unchanged as evidence.</p>
        )}
        <DetailRows
          rows={['reference', 'dial', 'movement', 'strap'].map((field) => [
            field,
            retainedConfiguration.values[field] ?? 'Unresolved',
          ])}
        />
        {correctedValues.length > 0 && (
          <section>
            <h3>{detailsLabel} — waiting for fresh evidence</h3>
            <DetailRows
              rows={correctedValues.map((entry) => [
                entry.field.replace(/_/g, ' '),
                `${entry.value} (was: ${entry.original_value ?? 'unknown'}, as listed)`,
              ])}
            />
          </section>
        )}
        <p>
          Saving keeps this exact intent. Collection remains staged. A supplied policy and fresh
          qualified evidence are required before verified delivered alerts.
        </p>
        {configuration.state !== 'supported' &&
          (intent ? (
            // F9 — after a correction this line sits directly under a
            // retained target; it must explain the wait, not read as
            // "your target is blocked".
            <p>
              Your saved target is retained. Alerts wait for fresh evidence for this watch.
            </p>
          ) : (
            <p>Exact identity must be resolved before starting exact tracking.</p>
          ))}
        <form onSubmit={submit}>
          <ChoiceValue
            label="UK delivered target (£)"
            name="target_gbp"
            value={target}
            choices={['100', '125', '150', '200', '300']}
            onChange={setTarget}
            required
          />
          <fieldset>
            <legend>Notification channels</legend>
            {channels.map((channel) => (
              <label key={channel}>
                <input
                  type="checkbox"
                  name={channel}
                  checked={selected.includes(channel)}
                  onChange={(event) =>
                    setSelected(
                      event.target.checked
                        ? [...selected, channel]
                        : selected.filter((value) => value !== channel)
                    )
                  }
                />
                {channel}
              </label>
            ))}
          </fieldset>
          <p>
            Uses your existing notification configuration. With no selected channels, no target
            message is sent.
          </p>
          <button
            type="submit"
            disabled={saving || (!intent && configuration.state !== 'supported')}
          >
            {saving ? 'Saving…' : 'Save delivered target'}
          </button>
          <p role="status">{message}</p>
          {error && <p role="alert">{error}</p>}
        </form>
      </section>
      {intent && <DeliveryRecords intent={intent} onSaved={onSaved} />}
    </div>
  )
}
