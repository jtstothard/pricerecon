import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import WatchForm from './WatchForm'
import SourceHealth from './SourceHealth'

interface Watch {
  id: number
  name: string
  query: string
  category: string | null
  enabled: boolean
  last_check_at: string | null
  schedule?: {
    interval?: string
    timezone?: string
    time_window?: string | null
  }
}

interface Source {
  name: string
  status: string
  last_error: string | null
}

interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

export default function WatchList() {
  const [watches, setWatches] = useState<Watch[]>([])
  const [sources, setSources] = useState<Source[]>([])
  const [showForm, setShowForm] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchWatches()
    fetchSources()
  }, [])

  const fetchWatches = async () => {
    try {
      const response = await fetch('/api/watches')
      if (!response.ok) throw new Error('Failed to fetch watches')
      const data: PaginatedResponse<Watch> = await response.json()
      setWatches(data.items)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load watches')
    } finally {
      setLoading(false)
    }
  }

  const fetchSources = async () => {
    try {
      const response = await fetch('/api/sources')
      if (!response.ok) throw new Error('Failed to fetch sources')
      const data: Source[] = await response.json()
      setSources(data)
    } catch (err) {
      console.error('Failed to load sources:', err)
    }
  }

  const handleWatchCreated = (watch: Watch) => {
    setWatches([...watches, watch])
    setShowForm(false)
  }

  const toggleWatch = async (id: number, enabled: boolean) => {
    try {
      const response = await fetch(`/api/watches/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enabled: !enabled }),
      })
      if (!response.ok) throw new Error('Failed to toggle watch')
      setWatches(watches.map(w => w.id === id ? { ...w, enabled: !enabled } : w))
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to toggle watch')
    }
  }

  const deleteWatch = async (id: number) => {
    if (!confirm('Are you sure you want to delete this watch?')) return
    try {
      const response = await fetch(`/api/watches/${id}`, { method: 'DELETE' })
      if (!response.ok) throw new Error('Failed to delete watch')
      setWatches(watches.filter(w => w.id !== id))
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to delete watch')
    }
  }

  if (loading) return <div className="loading">Loading watches...</div>
  if (error) return <div className="error">{error}</div>

  return (
    <div className="watch-list">
      <div className="watch-list-header">
        <h2>Watches</h2>
        <button className="btn btn-primary" onClick={() => setShowForm(true)}>
          + New Watch
        </button>
      </div>

      <SourceHealth sources={sources} />

      {watches.length === 0 ? (
        <div className="empty-state">
          <p>No watches yet. Create your first watch to start tracking prices.</p>
          <button className="btn btn-primary" onClick={() => setShowForm(true)}>
            Create Watch
          </button>
        </div>
      ) : (
        <div className="watch-grid">
          {watches.map(watch => (
            <div key={watch.id} className={`watch-card ${!watch.enabled ? 'disabled' : ''}`}>
              <div className="watch-card-header">
                <h3>
                  <Link to={`/watch/${watch.id}`}>{watch.name}</Link>
                </h3>
                <span className={`status-badge ${watch.enabled ? 'enabled' : 'disabled'}`}>
                  {watch.enabled ? 'Active' : 'Paused'}
                </span>
              </div>
              <div className="watch-card-body">
                <p><strong>Query:</strong> {watch.query}</p>
                <p><strong>Category:</strong> {watch.category || '—'}</p>
                <p><strong>Interval:</strong> {watch.schedule?.interval || '—'}</p>
                {watch.last_check_at && (
                  <p><strong>Last check:</strong> {new Date(watch.last_check_at).toLocaleString()}</p>
                )}
              </div>
              <div className="watch-card-actions">
                <button
                  className="btn btn-secondary"
                  onClick={() => toggleWatch(watch.id, watch.enabled)}
                >
                  {watch.enabled ? 'Pause' : 'Resume'}
                </button>
                <button className="btn btn-danger" onClick={() => deleteWatch(watch.id)}>
                  Delete
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {showForm && (
        <WatchForm
          onClose={() => setShowForm(false)}
          onCreated={handleWatchCreated}
        />
      )}
    </div>
  )
}