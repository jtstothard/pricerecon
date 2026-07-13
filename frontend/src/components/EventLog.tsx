import { useState, useEffect } from 'react'
import EmptyState from './ui/EmptyState'
import StatusBadge from './ui/StatusBadge'

interface Event {
  id: number
  event_type: string
  severity: string
  data: unknown
  created_at: string
}

const severityVariant = (severity: string) => {
  switch (severity) {
    case 'critical':
      return 'failed'
    case 'warning':
      return 'warning'
    case 'notice':
      return 'info'
    case 'info':
      return 'neutral'
    default:
      return 'neutral'
  }
}

export default function EventLog({ watchId }: { watchId: number }) {
  const [events, setEvents] = useState<Event[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchEvents()
  }, [watchId])

  const fetchEvents = async () => {
    try {
      const response = await fetch(`/api/watches/${watchId}/events`)
      if (!response.ok) throw new Error('Failed to fetch events')
      const data = await response.json()
      const items = Array.isArray(data) ? data : data.items || []
      setEvents(items.slice(0, 50))
      setError(null)
    } catch (err) {
      console.error('Failed to load events:', err)
      setError(err instanceof Error ? err.message : 'Failed to load events')
    } finally {
      setLoading(false)
    }
  }

  const formatEventData = (data: unknown) => {
    if (typeof data === 'string') return data
    return JSON.stringify(data, null, 2)
  }

  if (loading) {
    return <div className="state-panel state-panel--loading">Loading events…</div>
  }
  if (error) {
    return <EmptyState title="Events failed to load" description={error} action={<button className="btn btn-secondary" onClick={() => void fetchEvents()}>Try again</button>} />
  }
  if (events.length === 0) return <EmptyState title="No events yet" description="This watch has not emitted any events yet." />

  return (
    <div className="event-log" tabIndex={0} aria-label="Recent watch events">
      {events.map(event => (
        <div key={event.id} className={`event-item event-item--${severityVariant(event.severity)}`}>
          <div className="event-item__header">
            <StatusBadge variant={severityVariant(event.severity)}>{event.event_type}</StatusBadge>
            <span className="event-item__time">{new Date(event.created_at).toLocaleString()}</span>
          </div>
          <pre className="event-item__data">{formatEventData(event.data)}</pre>
        </div>
      ))}
    </div>
  )
}
