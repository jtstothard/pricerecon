import { useEffect, useState } from 'react'
import { loadHistory, type ObservationHistory as History } from '../../lib/history'

export function ObservationHistory({
  candidateId,
  technical = false,
}: {
  candidateId: string
  technical?: boolean
}) {
  const [open, setOpen] = useState(false)
  const [history, setHistory] = useState<History | null>(null)
  const [error, setError] = useState('')
  useEffect(() => {
    if (!open) return
    const controller = new AbortController()
    setError('')
    loadHistory(candidateId, controller.signal)
      .then(setHistory)
      .catch((failure: unknown) => {
        if (!controller.signal.aborted)
          setError(failure instanceof Error ? failure.message : 'History unavailable')
      })
    return () => controller.abort()
  }, [candidateId, open])
  return (
    <section className="discovery-history">
      <button type="button" onClick={() => setOpen(true)}>
        Load retained observations
      </button>
      <h3>Observations and gaps</h3>
      {error && <p role="alert">{error}</p>}
      {open && !history && !error && <p role="status">Loading retained observations…</p>}
      {history && (
        <>
          <p>
            Limited retained history. Usual price unavailable. No savings claim. Observations are
            separate from alert events and acquisition failures.
          </p>
          <p>{history.coverage_reason}</p>
          <p>
            As of {new Date(history.as_of).toLocaleString()}.{' '}
            {history.last_good
              ? `Last good evidence observed ${new Date(history.last_good.observed_at).toLocaleString()}; age ${Math.floor(history.last_good.age_seconds / 3600)} hours. Freshness unvalidated; current price and availability unknown.`
              : 'No qualifying last-good evidence. Current price and availability unknown.'}
          </p>
          {technical ? (
            <pre>{JSON.stringify(history, null, 2)}</pre>
          ) : (
            <table>
              <caption>Retained price observations</caption>
              <thead>
                <tr>
                  <th>Observed</th>
                  <th>Status</th>
                  <th>Delivered total</th>
                </tr>
              </thead>
              <tbody>
                {history.observations.map((observation) => (
                  <tr key={observation.id}>
                    <td>{observation.observed_at ?? observation.captured_at}</td>
                    <td>
                      {observation.validity.replace(/_/g, ' ')}
                      {observation.duplicate_of && ' · repeated evidence'}
                      {observation.invalidations.length > 0 && ' · withdrawn'}
                    </td>
                    <td>
                      {observation.costs.map((cost) => (
                        <p key={cost.id}>
                          {cost.kind.replace(/_/g, ' ')}:{' '}
                          {cost.total
                            ? `${cost.total.currency} ${cost.total.amount}`
                            : 'Total unknown'}{' '}
                          · {cost.state}
                        </p>
                      ))}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </>
      )}
    </section>
  )
}
