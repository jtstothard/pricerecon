import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import PriceHistoryChart from './PriceHistoryChart'
import EventLog from './EventLog'

interface Watch {
  id: number
  name: string
  query: string
  category: string | null
  enabled: boolean
  last_check_at: string | null
  schedule?: {
    interval?: string
  }
}

interface Listing {
  source: string
  source_listing_id: string
  title_raw: string
  price: number | string
  currency: string
  condition: string | null
  url: string
  timestamp_seen: string
  in_stock: boolean | null
}

interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

export default function WatchDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [watch, setWatch] = useState<Watch | null>(null)
  const [listings, setListings] = useState<Listing[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (id) {
      fetchWatchData()
    }
  }, [id])

  const fetchWatchData = async () => {
    if (!id) return
    try {
      const [watchRes, listingsRes] = await Promise.all([
        fetch(`/api/watches/${id}`),
        fetch(`/api/watches/${id}/listings`),
      ])

      if (!watchRes.ok || !listingsRes.ok) {
        throw new Error('Failed to fetch watch data')
      }

      const watchData: Watch = await watchRes.json()
      const listingsData: PaginatedResponse<Listing> = await listingsRes.json()

      setWatch(watchData)
      setListings(listingsData.items)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load watch')
    } finally {
      setLoading(false)
    }
  }

  const triggerCheck = async () => {
    if (!id) return
    try {
      const response = await fetch(`/api/watches/${id}/check`, { method: 'POST' })
      if (!response.ok) throw new Error('Failed to trigger check')
      await fetchWatchData()
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to trigger check')
    }
  }

  if (loading) return <div className="loading">Loading watch...</div>
  if (error) return <div className="error">{error}</div>
  if (!watch) return <div className="error">Watch not found</div>

  return (
    <div className="watch-detail">
      <div className="watch-detail-header">
        <button className="btn btn-secondary" onClick={() => navigate('/')}>
          ← Back
        </button>
        <div className="header-content">
          <h2>{watch.name}</h2>
          <button className="btn btn-primary" onClick={triggerCheck}>
            Check Now
          </button>
        </div>
      </div>

      <div className="watch-info">
        <p><strong>Query:</strong> {watch.query}</p>
        <p><strong>Category:</strong> {watch.category || '—'}</p>
        <p><strong>Interval:</strong> {watch.schedule?.interval || '—'}</p>
        <p><strong>Status:</strong> {watch.enabled ? 'Active' : 'Paused'}</p>
        {watch.last_check_at && (
          <p><strong>Last check:</strong> {new Date(watch.last_check_at).toLocaleString()}</p>
        )}
      </div>

      <div className="watch-sections">
        <section className="watch-section">
          <h3>Current Listings ({listings.length})</h3>
          {listings.length === 0 ? (
            <p className="empty-state">No listings found</p>
          ) : (
            <div className="listings-table">
              <table>
                <thead>
                  <tr>
                    <th>Source</th>
                    <th>Title</th>
                    <th>Price</th>
                    <th>Condition</th>
                    <th>Stock</th>
                    <th>Seen</th>
                    <th>Link</th>
                  </tr>
                </thead>
                <tbody>
                  {listings.map(listing => (
                    <tr key={listing.source_listing_id}>
                      <td>{listing.source}</td>
                      <td>{listing.title_raw}</td>
                      <td>{listing.currency} {Number(listing.price).toFixed(2)}</td>
                      <td>{listing.condition || 'N/A'}</td>
                      <td>
                        <span className={`stock-badge ${listing.in_stock ? 'in-stock' : 'out-of-stock'}`}>
                          {listing.in_stock ? 'In Stock' : 'Out of Stock'}
                        </span>
                      </td>
                      <td>{new Date(listing.timestamp_seen).toLocaleString()}</td>
                      <td>
                        <a href={listing.url} target="_blank" rel="noopener noreferrer">
                          View
                        </a>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>

        <section className="watch-section">
          <PriceHistoryChart watchId={parseInt(id!)} />
        </section>

        <section className="watch-section">
          <EventLog watchId={parseInt(id!)} />
        </section>
      </div>
    </div>
  )
}
