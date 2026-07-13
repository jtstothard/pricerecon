import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import PriceHistoryChart from './PriceHistoryChart'
import EventLog from './EventLog'
import SectionCard from './ui/SectionCard'
import StatusBadge from './ui/StatusBadge'
import EmptyState from './ui/EmptyState'
import Toast, { ToastVariant } from './ui/toast'
import { usePageTitle } from '../hooks/usePageTitle'
import { formatSourceName } from '../lib/sourceNames'
import { formatCategory } from '../lib/categoryUtils'

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

const formatDateTime = (value: string | null) => {
  if (!value) return '—'
  return new Date(value).toLocaleString()
}

const formatPrice = (currency: string, price: number | string) => {
  const numericPrice = Number(price)
  if (Number.isNaN(numericPrice)) return `${currency} ${price}`
  return `${currency} ${numericPrice.toFixed(2)}`
}



export default function WatchDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [watch, setWatch] = useState<Watch | null>(null)
  const [listings, setListings] = useState<Listing[]>([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [checking, setChecking] = useState(false)
  const [toast, setToast] = useState<{ message: string; variant: ToastVariant } | null>(null)

  usePageTitle(watch ? `Watch: ${watch.name}` : 'Watch detail')

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
      setRefreshing(false)
    }
  }

  const handleRefresh = async () => {
    setRefreshing(true)
    await fetchWatchData()
  }

  const triggerCheck = async () => {
    if (!id) return
    setChecking(true)
    try {
      const response = await fetch(`/api/watches/${id}/check`, { method: 'POST' })
      if (!response.ok) throw new Error('Failed to trigger check')
      await fetchWatchData()
      setToast({ message: 'Check triggered successfully', variant: 'success' })
    } catch (err) {
      setToast({ message: err instanceof Error ? err.message : 'Failed to trigger check', variant: 'error' })
    } finally {
      setChecking(false)
    }
  }


  if (loading) {
    return (
      <div className="state-panel state-panel--loading">
        <div className="state-panel__title">Loading watch detail</div>
        <div className="state-panel__description">Fetching the latest watch record, listings, history, and events.</div>
      </div>
    )
  }
  if (error) {
    return (
      <EmptyState
        title="Watch detail failed to load"
        description={error}
        icon="!"
        action={<button className="btn btn-secondary" onClick={() => void fetchWatchData()}>Try again</button>}
      />
    )
  }
  if (!watch) {
    return (
      <EmptyState
        title="Watch not found"
        description="The requested watch no longer exists or the route is invalid."
        action={<button className="btn btn-secondary" onClick={() => navigate(-1)}>Go back</button>}
      />
    )
  }

  const lastCheck = formatDateTime(watch.last_check_at)
  const schedule = watch.schedule?.interval || '—'
  const category = formatCategory(watch.category)

  return (
    <div className="detail-page">
      <SectionCard
        eyebrow="Watch detail"
        title={watch.name}
        subtitle=""
        headingLevel="h1"
        id="page-title"
        action={(
          <div className="inline-actions">
            <button className="btn btn-secondary" onClick={() => navigate(-1)} aria-label="Go back to dashboard">
              ← Back
            </button>
            <button className="btn btn-secondary" onClick={() => void handleRefresh()} disabled={refreshing} aria-label="Refresh watch data">
              {refreshing ? 'Refreshing...' : 'Refresh'}
            </button>
            <button className="btn btn-primary" onClick={triggerCheck} disabled={checking} aria-label="Trigger watch check now">
              {checking ? 'Checking...' : 'Check now'}
            </button>
          </div>
        )}
      >
        <div className="detail-hero">
          <div className="detail-header__name">
            <StatusBadge variant={watch.enabled ? 'active' : 'paused'}>
              {watch.enabled ? 'Active' : 'Paused'}
            </StatusBadge>
            <StatusBadge variant="neutral">Watch #{watch.id}</StatusBadge>
            <StatusBadge variant="accent">{formatCategory(watch.category)}</StatusBadge>
          </div>

          <div className="detail-meta">
            <span><strong>Query</strong> {watch.query}</span>
            <span><strong>Schedule</strong> {schedule}</span>
            <span><strong>Last check</strong> {lastCheck}</span>
          </div>

          <div className="detail-stat-grid">
            <div className="detail-stat">
              <div className="detail-stat__label">Listings</div>
              <div className="detail-stat__value">{listings.length}</div>
            </div>
            <div className="detail-stat">
              <div className="detail-stat__label">Category</div>
              <div className="detail-stat__value">{category}</div>
            </div>
            <div className="detail-stat">
              <div className="detail-stat__label">Status</div>
              <div className="detail-stat__value">{watch.enabled ? 'Watching' : 'Paused'}</div>
            </div>
          </div>
        </div>
      </SectionCard>

      <div className="detail-layout detail-layout--dense">
        <div className="detail-stack">
          <SectionCard
            title={`Current listings (${listings.length})`}
            subtitle=""
          >
            <div aria-live="polite" aria-atomic="true" className="visually-hidden">
              Showing {listings.length} listings
            </div>
            {listings.length === 0 ? (
              <EmptyState
                title="No listings yet"
                description="The watch has not produced any listings yet. Trigger a check or wait for the next run."
                action={<button className="btn btn-primary" onClick={triggerCheck}>Check now</button>}
              />
            ) : (
              <div className="table-scroll">
                <table className="listings-table" aria-label="Current listings table">
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
                        <td data-label="Source">
                          <div className="table-cell-stack">
                            <span className="table-cell__primary" title={formatSourceName(listing.source)}>{formatSourceName(listing.source)}</span>
                          </div>
                        </td>
                        <td data-label="Title">
                          <div className="table-cell-stack">
                            <span className="table-cell__primary">{listing.title_raw}</span>
                          </div>
                        </td>
                        <td data-label="Price">
                          <div className="table-cell-stack">
                            <span className="table-cell__primary">{formatPrice(listing.currency, listing.price)}</span>
                            <span className="table-cell__secondary">Latest observed price</span>
                          </div>
                        </td>
                        <td data-label="Condition">{listing.condition || 'N/A'}</td>
                        <td data-label="Stock">
                          <StatusBadge variant={listing.in_stock ? 'healthy' : 'failed'}>
                            {listing.in_stock ? 'In stock' : 'Out of stock'}
                          </StatusBadge>
                        </td>
                        <td data-label="Seen">{formatDateTime(listing.timestamp_seen)}</td>
                        <td data-label="Link">
                          <a className="btn btn-secondary btn--compact" href={listing.url} target="_blank" rel="noopener noreferrer" aria-label={`View listing on ${formatSourceName(listing.source)}`}>
                            View
                          </a>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </SectionCard>

          <SectionCard
            title="Price history"
            subtitle=""
            className="chart-card"
          >
            <PriceHistoryChart watchId={parseInt(id!)} />
          </SectionCard>
        </div>

        <div className="detail-stack">
          <SectionCard
            title="Event log"
            subtitle=""
          >
            <EventLog watchId={parseInt(id!)} />
          </SectionCard>
        </div>
      </div>

      {toast && (
        <Toast
          message={toast.message}
          variant={toast.variant}
          onClose={() => setToast(null)}
        />
      )}
    </div>
  )
}
