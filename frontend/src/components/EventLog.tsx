import { useState, useEffect } from 'react'

interface Event {
  id: number
  event_type: string
  severity: string
  data: any
  created_at: string
}

export default function EventLog({ watchId }: { watchId: number }) {
  const [events, setEvents] = useState<Event[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchEvents()
  }, [watchId])

  const fetchEvents = async () => {
    try {
      const response = await fetch(`/api/watches/${watchId}/events`)
      if (!response.ok) throw new Error('Failed to fetch events')
      const data = await response.json()
      setEvents(data.slice(0, 50)) // Show last 50 events
    } catch (err) {
      console.error('Failed to load events:', err)
    } finally {
      setLoading(false)
    }
  }

  const getEventSeverity = (severity: string) => {
    switch (severity) {
      case 'critical': return 'critical'
      case 'warning': return 'warning'
      case 'notice': return 'notice'
      case 'info': return 'info'
      default: return 'debug'
    }
  }

  const formatEventData = (data: any) => {
    if (typeof data === 'string') return data
    return JSON.stringify(data, null, 2)
  }

  if (loading) return <div className="loading">Loading events...</div>
  if (events.length === 0) return <p className="empty-state">No events yet</p>

  return (
    <div>
      <h3>Event Log ({events.length})</h3>
      <div className="event-log">
        {events.map(event => (
          <div key={event.id} className={`event-item ${getEventSeverity(event.severity)}`}>
            <div className="event-header">
              <span className="event-type">{event.event_type}</span>
              <span className="event-time">{new Date(event.created_at).toLocaleString()}</span>
            </div>
            <pre className="event-data">{formatEventData(event.data)}</pre>
          </div>
        ))}
      </div>
    </div>
  )
}
