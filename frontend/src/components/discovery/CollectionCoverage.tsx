import { useEffect, useState } from 'react'
import { parseCollection, type CollectionStatus } from '../../lib/collection'

export function CollectionCoverage() {
  const [status, setStatus] = useState<CollectionStatus | null>(null)
  const [error, setError] = useState('')
  useEffect(() => {
    const controller = new AbortController()
    async function load() {
      try {
        const response = await fetch('/api/discovery/collection', { signal: controller.signal })
        if (!response.ok) throw new Error('Collection coverage could not load.')
        const parsed = parseCollection(await response.json())
        if (!controller.signal.aborted) setStatus(parsed)
      } catch (failure) {
        if (!controller.signal.aborted) setError(failure instanceof Error ? failure.message : 'Collection coverage unavailable.')
      }
    }
    void load()
    return () => controller.abort()
  }, [])
  return <details className="collection-coverage">
    <summary>Collection limits and coverage</summary>
    {error && <p role="alert">{error} Evidence freshness remains unproven.</p>}
    {!error && !status && <p>Loading collection coverage…</p>}
    {status && <>
      <p>Operating policy: {status.state}. Activation: {status.activation}.</p>
      {status.gates.length > 0 && <ul>{status.gates.map(gate => <li key={gate}>{gate.replace(/_/g, ' ')}</li>)}</ul>}
      <p>Tracking and potential-alert verification have reserved capacity. Capped, blocked and failed attempts leave gaps; an empty result means the declared search completed.</p>
      <p>Transport health does not renew offer evidence. Retained observations keep their original dates and cannot alone establish a current bargain.</p>
      {status.scope_id && <p>Envelope {status.scope_id}; stops {status.stops_at ? new Date(status.stops_at).toLocaleString() : 'unknown'}.</p>}
      <ul>{status.usage.map(usage => <li key={usage.resource}>{usage.resource.replace(/_/g, ' ')}: {usage.used} used or reserved of {usage.limit}; tracking reserve {usage.tracking_reserve}.</li>)}</ul>
      <ul>{status.provider_usage.map(usage => <li key={usage.source}>{usage.source} requests: {usage.used} of {usage.limit}; tracking reserve {usage.tracking_reserve}.</li>)}</ul>
      <p>Storage accounting covers SQLite retained payload growth. Filesystem allocation, journals, logs and backups still require operating approval.</p>
      {status.attempts.length === 0 && <p>No governed collection attempts retained.</p>}
      <ul>{status.attempts.map(attempt => <li key={attempt.id}>
        {attempt.source} · {attempt.query} · {attempt.purpose} · <strong>{attempt.state.replace(/_/g, ' ')}</strong>{attempt.reason && ` (${attempt.reason.replace(/_/g, ' ')})`}.
        {' '}Attempted {new Date(attempt.attempted_at).toLocaleString()}; evidence {attempt.evidence_state.replace(/_/g, ' ')}.
        {' '}Last completed acquisition {attempt.last_good_at ? `${new Date(attempt.last_good_at).toLocaleString()} (${attempt.last_good_age_seconds} seconds old)` : 'unavailable'}; qualification is not inferred.
        {attempt.next_eligible_at && ` Next eligible ${new Date(attempt.next_eligible_at).toLocaleString()}; no catch-up replay.`}
      </li>)}</ul>
    </>}
  </details>
}
