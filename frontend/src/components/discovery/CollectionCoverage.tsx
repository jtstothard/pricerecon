import { useEffect, useState } from 'react'
import { parseCollection, type CollectionStatus } from '../../lib/collection'

// What a tracking reserve means (src/pricerecon/core/rate_limiter.py): it is
// withheld from discovery only, so a reserve of 0 carves nothing out of the
// shared allowance. That says nothing about admission: debit() refuses every
// request unless the operating policy is supplied and inside its window, so any
// claim about usable capacity is made only for state "supplied".
function reserveStatement(status: CollectionStatus) {
  if (status.state === 'expired')
    return 'The operating envelope has expired: admission is closed and there is no current operating envelope, so no tracking reserve currently applies. The recorded figures below are exact but nothing can use them.'
  const limits = [...status.usage, ...status.provider_usage]
  if (status.state === 'blocked') {
    if (limits.length === 0)
      return 'No operating envelope is supplied, so no tracking reserve is defined. Admission is closed.'
    return 'The operating policy is blocked: admission is closed and there is no current operating envelope, so no tracking reserve currently applies. The recorded figures below are exact but nothing can use them.'
  }
  if (limits.length === 0) return 'No operating envelope is supplied, so no tracking reserve is defined.'
  const held = limits.filter((limit) => limit.tracking_reserve > 0).length
  const spent = limits.filter((limit) => limit.used >= limit.limit).length
  const exhausted =
    spent > 0
      ? ` ${spent} of ${limits.length} limits are already used up, so further attempts that need them are capped.`
      : ''
  if (held === 0)
    return `No capacity is carved out of the shared allowance for tracking or potential-alert verification: every tracking reserve is 0, so discovery and tracking draw on the same allowance until a limit is used up.${exhausted}`
  return `Capacity is held back from discovery for tracking and potential-alert verification on ${held} of ${limits.length} limits; a tracking reserve of 0 holds nothing back.${exhausted}`
}
// next_eligible_at is the earliest permitted retry for the source (attempt end
// plus recovery spacing), or the lease end while running. It is never a
// scheduled run. The API sends no server time, so past/future is judged against
// this browser's clock and worded as such; admission is decided by the server
// (rate_limiter begin()), which also marks an expired running lease interrupted
// only when the next attempt starts, so a crashed run can still read "running".
const ADMISSION = 'the server decides admission when an attempt starts'
const NOT_SCHEDULED = 'no run is scheduled and missed periods are not replayed'
function retryTiming(attempt: CollectionStatus['attempts'][number]) {
  if (!attempt.next_eligible_at) return null
  const at = new Date(attempt.next_eligible_at)
  const when = at.toLocaleString()
  const ahead = at.getTime() > Date.now()
  if (attempt.state === 'running') {
    if (ahead)
      return `This source is held for the running attempt until ${when} (by this browser's clock, lease still ahead); ${ADMISSION}; ${NOT_SCHEDULED}.`
    return `Lease expired, unconfirmed: the running attempt's lease ended ${when} (by this browser's clock) with no recorded finish; ${ADMISSION}; ${NOT_SCHEDULED}.`
  }
  if (ahead)
    return `Source spacing: recorded earliest next attempt is ${when} (by this browser's clock, still ahead); ${ADMISSION}; ${NOT_SCHEDULED}.`
  return `By this browser's clock no spacing wait remains (recorded earliest next attempt: ${when}); ${ADMISSION}; ${NOT_SCHEDULED}.`
}

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
        if (!controller.signal.aborted)
          setError(failure instanceof Error ? failure.message : 'Collection coverage unavailable.')
      }
    }
    void load()
    return () => controller.abort()
  }, [])
  return (
    <section className="collection-coverage">
      <h3>Collection limits and coverage</h3>
      {error && <p role="alert">{error} Evidence freshness remains unproven.</p>}
      {!error && !status && <p>Loading collection coverage…</p>}
      {status && (
        <>
          <p>
            Operating policy: {status.state}. Activation: {status.activation}.
          </p>
          {status.gates.length > 0 && (
            <ul>
              {status.gates.map((gate) => (
                <li key={gate}>{gate.replace(/_/g, ' ')}</li>
              ))}
            </ul>
          )}
          <p>
            {reserveStatement(status)} Capped, blocked and failed attempts leave gaps; an empty
            result means the declared search completed.
          </p>
          <p>
            Transport health does not renew offer evidence. Retained observations keep their
            original dates and cannot alone establish a current bargain.
          </p>
          {status.scope_id && (
            <p>
              Envelope {status.scope_id}; stops{' '}
              {status.stops_at ? new Date(status.stops_at).toLocaleString() : 'unknown'}.
            </p>
          )}
          <ul>
            {status.usage.map((usage) => (
              <li key={usage.resource}>
                {usage.resource.replace(/_/g, ' ')}: {usage.used} used or reserved of {usage.limit};
                tracking reserve {usage.tracking_reserve}.
              </li>
            ))}
          </ul>
          <ul>
            {status.provider_usage.map((usage) => (
              <li key={usage.source}>
                {usage.source} requests: {usage.used} of {usage.limit}; tracking reserve{' '}
                {usage.tracking_reserve}.
              </li>
            ))}
          </ul>
          <p>
            Storage accounting covers SQLite retained payload growth. Filesystem allocation,
            journals, logs and backups still require operating approval.
          </p>
          {status.attempts.length === 0 && <p>No governed collection attempts retained.</p>}
          <ul>
            {status.attempts.map((attempt) => (
              <li key={attempt.id}>
                {attempt.source} · {attempt.query} · {attempt.purpose} ·{' '}
                <strong>{attempt.state.replace(/_/g, ' ')}</strong>
                {attempt.reason && ` (${attempt.reason.replace(/_/g, ' ')})`}. Attempted{' '}
                {new Date(attempt.attempted_at).toLocaleString()}; evidence{' '}
                {attempt.evidence_state.replace(/_/g, ' ')}. Last completed acquisition{' '}
                {attempt.last_good_at
                  ? `${new Date(attempt.last_good_at).toLocaleString()} (${attempt.last_good_age_seconds} seconds old)`
                  : 'unavailable'}
                ; qualification is not inferred.
                {attempt.next_eligible_at && (
                  <>
                    {' '}
                    <span title={`Technical field next_eligible_at: ${attempt.next_eligible_at}`}>
                      {retryTiming(attempt)}
                    </span>
                  </>
                )}
              </li>
            ))}
          </ul>
        </>
      )}
    </section>
  )
}
