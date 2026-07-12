import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import WatchForm from './WatchForm'
import SourceHealth from './SourceHealth'
import SectionCard from './ui/SectionCard'
import StatusBadge from './ui/StatusBadge'
import EmptyState from './ui/EmptyState'
import type { SourceSummary, WatchSummary } from './watchTypes'

interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

type WatchFilter = 'all' | 'active' | 'paused'
type HealthFilter = 'all' | 'healthy' | 'issues'
type NormalizedSourceStatus = 'healthy' | 'degraded' | 'failed' | 'paused' | 'neutral'

const normalizeSourceStatus = (status: string): NormalizedSourceStatus => {
  switch (status.toLowerCase()) {
    case 'healthy':
    case 'ok':
      return 'healthy'
    case 'warning':
    case 'degraded':
      return 'degraded'
    case 'error':
    case 'failed':
      return 'failed'
    case 'disabled':
      return 'paused'
    default:
      return 'neutral'
  }
}

const formatDateTime = (value: string | null) => {
  if (!value) return '—'
  return new Date(value).toLocaleString()
}

const sourceStateLabel = (statuses: NormalizedSourceStatus[]) => {
  if (statuses.some(status => status === 'failed')) return 'failed'
  if (statuses.some(status => status === 'degraded')) return 'degraded'
  if (statuses.some(status => status === 'paused')) return 'paused'
  if (statuses.some(status => status === 'healthy')) return 'healthy'
  return 'neutral'
}

export default function WatchList() {
  const [watches, setWatches] = useState<WatchSummary[]>([])
  const [sources, setSources] = useState<SourceSummary[]>([])
  const [showForm, setShowForm] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [search, setSearch] = useState('')
  const [watchFilter, setWatchFilter] = useState<WatchFilter>('all')
  const [healthFilter, setHealthFilter] = useState<HealthFilter>('all')
  const [pageInfo, setPageInfo] = useState({ page: 1, pageSize: 0, total: 0 })

  useEffect(() => {
    void fetchDashboardData()
  }, [])

  const fetchDashboardData = async () => {
    setLoading(true)
    try {
      const [watchesResponse, sourcesResponse] = await Promise.all([
        fetch('/api/watches?page=1&page_size=100'),
        fetch('/api/sources'),
      ])

      if (!watchesResponse.ok) throw new Error('Failed to fetch watches')
      if (!sourcesResponse.ok) throw new Error('Failed to fetch sources')

      const watchesData: PaginatedResponse<WatchSummary> = await watchesResponse.json()
      const sourcesData: SourceSummary[] = await sourcesResponse.json()

      setWatches(Array.isArray(watchesData.items) ? watchesData.items : [])
      setSources(Array.isArray(sourcesData) ? sourcesData : [])
      setPageInfo({
        page: watchesData.page ?? 1,
        pageSize: watchesData.page_size ?? watchesData.items.length,
        total: watchesData.total ?? watchesData.items.length,
      })
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load dashboard')
    } finally {
      setLoading(false)
    }
  }

  const handleWatchCreated = (watch: WatchSummary) => {
    setWatches(prev => [watch, ...prev])
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
      const updatedWatch: WatchSummary = await response.json()
      setWatches(prev => prev.map(w => (w.id === id ? updatedWatch : w)))
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to toggle watch')
    }
  }

  const deleteWatch = async (id: number) => {
    if (!confirm('Are you sure you want to delete this watch?')) return
    try {
      const response = await fetch(`/api/watches/${id}`, { method: 'DELETE' })
      if (!response.ok) throw new Error('Failed to delete watch')
      setWatches(prev => prev.filter(w => w.id !== id))
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to delete watch')
    }
  }

  const sourcesByConnector = useMemo(
    () => new Map(sources.map(source => [source.connector, source])),
    [sources],
  )

  const kpis = useMemo(() => {
    const activeWatches = watches.filter(watch => watch.enabled).length
    const pausedWatches = watches.length - activeWatches
    const checkedWatches = watches.filter(watch => Boolean(watch.last_check_at)).length
    const healthySources = sources.filter(source => normalizeSourceStatus(source.status) === 'healthy').length
    const degradedSources = sources.filter(source => normalizeSourceStatus(source.status) === 'degraded').length
    const failedSources = sources.filter(source => normalizeSourceStatus(source.status) === 'failed').length

    return {
      activeWatches,
      pausedWatches,
      checkedWatches,
      healthySources,
      degradedSources,
      failedSources,
    }
  }, [sources, watches])

  const filteredWatches = useMemo(() => {
    const needle = search.trim().toLowerCase()

    return watches.filter(watch => {
      const matchesSearch =
        needle.length === 0 ||
        [watch.name, watch.query, watch.category ?? '', watch.sources.map(source => source.connector).join(' ')].some(value =>
          value.toLowerCase().includes(needle),
        )

      const matchesWatchFilter =
        watchFilter === 'all' ||
        (watchFilter === 'active' && watch.enabled) ||
        (watchFilter === 'paused' && !watch.enabled)

      const rowSourceStatuses = watch.sources
        .map(source => sourcesByConnector.get(source.connector)?.status)
        .filter((value): value is string => Boolean(value))
        .map(normalizeSourceStatus)

      const rowHasIssues = rowSourceStatuses.some(status => status === 'degraded' || status === 'failed')
      const matchesHealthFilter =
        healthFilter === 'all' ||
        (healthFilter === 'healthy' && !rowHasIssues) ||
        (healthFilter === 'issues' && rowHasIssues)

      return matchesSearch && matchesWatchFilter && matchesHealthFilter
    })
  }, [healthFilter, search, sourcesByConnector, watches, watchFilter])

  const watchRows = filteredWatches.map(watch => {
    const rowSourceRecords = watch.sources.map(source => sourcesByConnector.get(source.connector)).filter(Boolean)
    const rowSourceStatuses = rowSourceRecords.map(source => normalizeSourceStatus(source!.status))
    const rowState = sourceStateLabel(rowSourceStatuses)
    const connectedSources = rowSourceRecords.length > 0 ? rowSourceRecords.length : watch.sources.length
    const healthyConnections = rowSourceStatuses.filter(status => status === 'healthy').length
    const degradedConnections = rowSourceStatuses.filter(status => status === 'degraded').length
    const failedConnections = rowSourceStatuses.filter(status => status === 'failed').length

    return {
      watch,
      rowState,
      connectedSources,
      healthyConnections,
      degradedConnections,
      failedConnections,
    }
  })

  const handleCheckNow = async (watchId: number) => {
    const response = await fetch(`/api/watches/${watchId}/check`, { method: 'POST' })
    if (!response.ok) throw new Error('Failed to trigger watch check')
    await fetchDashboardData()
  }

  if (loading) return <div className="loading">Loading control center...</div>
  if (error) return <div className="error">{error}</div>

  return (
    <div className="dashboard-stack">
      <div className="kpi-grid">
        <SectionCard title="Active watches" subtitle="Currently checking on schedule">
          <div className="kpi-card__value">{kpis.activeWatches}</div>
          <div className="kpi-card__meta">{kpis.pausedWatches} paused · {watches.length} total</div>
        </SectionCard>
        <SectionCard title="Watches checked" subtitle="Watches with a recorded check">
          <div className="kpi-card__value">{kpis.checkedWatches}</div>
          <div className="kpi-card__meta">{pageInfo.total} listed in the current page window</div>
        </SectionCard>
        <SectionCard title="Healthy sources" subtitle="Connector posture across the board">
          <div className="kpi-card__value">{kpis.healthySources}</div>
          <div className="kpi-card__meta">{kpis.degradedSources} degraded · {kpis.failedSources} failed</div>
        </SectionCard>
        <SectionCard title="Attention needed" subtitle="Anything worth drilling into">
          <div className="kpi-card__value">{kpis.degradedSources + kpis.failedSources}</div>
          <div className="kpi-card__meta">Source health issues and manual follow-up</div>
        </SectionCard>
      </div>

      <div className="toolbar watch-toolbar">
        <input
          className="toolbar__search"
          type="search"
          placeholder="Search watches, queries, categories, or connectors…"
          value={search}
          onChange={e => setSearch(e.target.value)}
        />
        <div className="watch-filter-group">
          <button type="button" className={`toolbar__filter ${watchFilter === 'all' ? 'is-active' : ''}`} onClick={() => setWatchFilter('all')}>
            All watches
          </button>
          <button type="button" className={`toolbar__filter ${watchFilter === 'active' ? 'is-active' : ''}`} onClick={() => setWatchFilter('active')}>
            Active
          </button>
          <button type="button" className={`toolbar__filter ${watchFilter === 'paused' ? 'is-active' : ''}`} onClick={() => setWatchFilter('paused')}>
            Paused
          </button>
        </div>
        <div className="watch-filter-group">
          <button type="button" className={`toolbar__filter ${healthFilter === 'all' ? 'is-active' : ''}`} onClick={() => setHealthFilter('all')}>
            Any source state
          </button>
          <button type="button" className={`toolbar__filter ${healthFilter === 'healthy' ? 'is-active' : ''}`} onClick={() => setHealthFilter('healthy')}>
            Healthy only
          </button>
          <button type="button" className={`toolbar__filter ${healthFilter === 'issues' ? 'is-active' : ''}`} onClick={() => setHealthFilter('issues')}>
            Needs attention
          </button>
        </div>
      </div>

      <div className="dashboard-grid">
        <SectionCard
          title="Watch queue"
          subtitle="Dense operations view with query summary, source state, recency, and the next action."
          action={<StatusBadge variant="accent">Page {pageInfo.page} · {pageInfo.pageSize || filteredWatches.length} shown</StatusBadge>}
        >
          {watchRows.length === 0 ? (
            <EmptyState
              title="No watches match the current filters"
              description="Broaden the search or switch the source-health filter to reveal more watches."
              action={<button className="btn btn-primary" onClick={() => setShowForm(true)}>Create watch</button>}
            />
          ) : (
            <div style={{ overflowX: 'auto' }}>
              <table className="watch-table">
                <thead>
                  <tr>
                    <th>Watch</th>
                    <th>Source state</th>
                    <th>Last check / change</th>
                    <th>Status</th>
                    <th>Primary action</th>
                  </tr>
                </thead>
                <tbody>
                  {watchRows.map(({ watch, rowState, connectedSources, healthyConnections, degradedConnections, failedConnections }) => (
                    <tr key={watch.id}>
                      <td>
                        <div className="watch-row__name">
                          <div className="watch-row__title">
                            <Link to={`/watch/${watch.id}`} className="watch-table__link">
                              {watch.name}
                            </Link>
                          </div>
                          <div className="watch-row__meta">{watch.query}</div>
                          <div className="watch-table__secondary">
                            {watch.category || 'Uncategorized'} · {watch.sources.map(source => source.connector).join(' · ') || 'No sources configured'}
                          </div>
                        </div>
                      </td>
                      <td>
                        <div className="watch-row__name">
                          <StatusBadge
                            variant={
                              rowState === 'healthy'
                                ? 'healthy'
                                : rowState === 'degraded'
                                  ? 'warning'
                                  : rowState === 'failed'
                                    ? 'failed'
                                    : rowState === 'paused'
                                      ? 'paused'
                                      : 'neutral'
                            }
                          >
                            {rowState}
                          </StatusBadge>
                          <div className="watch-table__secondary">
                            {connectedSources} source{connectedSources === 1 ? '' : 's'} · {healthyConnections} healthy
                            {degradedConnections ? ` · ${degradedConnections} degraded` : ''}
                            {failedConnections ? ` · ${failedConnections} failed` : ''}
                          </div>
                        </div>
                      </td>
                      <td>
                        <div className="watch-row__name">
                          <div className="watch-row__title">{formatDateTime(watch.last_check_at)}</div>
                          <div className="watch-table__secondary">
                            {watch.enabled
                              ? `Schedule every ${watch.schedule?.interval || '—'}`
                              : 'Paused watch · no scheduled checks'}
                          </div>
                        </div>
                      </td>
                      <td>
                        <StatusBadge variant={watch.enabled ? 'active' : 'paused'}>
                          {watch.enabled ? 'Active' : 'Paused'}
                        </StatusBadge>
                      </td>
                      <td>
                        <div className="watch-row__actions">
                          <button type="button" className="btn btn-secondary" onClick={() => toggleWatch(watch.id, watch.enabled)}>
                            {watch.enabled ? 'Pause' : 'Resume'}
                          </button>
                          <button type="button" className="btn btn-secondary" onClick={() => void handleCheckNow(watch.id).catch(err => alert(err instanceof Error ? err.message : 'Failed to trigger watch check'))}>
                            Check now
                          </button>
                          <button type="button" className="btn btn-danger" onClick={() => deleteWatch(watch.id)}>
                            Delete
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </SectionCard>

        <SectionCard
          title="Source health"
          subtitle="Healthy, degraded, and failed connectors kept in one compact operational panel."
          action={<StatusBadge variant="neutral">{sources.length} connectors</StatusBadge>}
        >
          <SourceHealth sources={sources} />
        </SectionCard>
      </div>

      {showForm && (
        <WatchForm
          onClose={() => setShowForm(false)}
          onCreated={handleWatchCreated}
        />
      )}
    </div>
  )
}
