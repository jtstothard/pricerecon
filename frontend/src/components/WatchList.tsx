import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import TopActionBar from './layout/TopActionBar'
import WatchForm from './WatchForm'
import SourceHealth from './SourceHealth'
import SectionCard from './ui/SectionCard'
import StatusBadge from './ui/StatusBadge'
import EmptyState from './ui/EmptyState'
import Toast, { ToastVariant } from './ui/toast'
import type { SourceSummary, WatchSummary } from './watchTypes'
import { usePageTitle } from '../hooks/usePageTitle'
import { formatSourceName } from '../lib/sourceNames'
import { formatDateTime } from '../lib/dateUtils'

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
    case 'paused':
      return 'paused'
    default:
      return 'neutral'
  }
}

const dedupeTrailingTokens = (value: string) => value.replace(/\b([\p{L}\p{N}_-]+)(?:\s+\1)+$/giu, '$1')

const formatWatchLabel = (value: string) => dedupeTrailingTokens(value).trim()

const formatWatchMeta = (watch: WatchSummary) => {
  const parts: string[] = []
  const category = watch.category?.trim()
  const query = dedupeTrailingTokens(watch.query).trim()

  if (category) parts.push(category)
  if (query && query.toLowerCase() !== watch.name.trim().toLowerCase()) {
    parts.push(query)
  }

  return parts.length > 0 ? parts.join(' · ') : 'No category or query summary'
}

const formatConnectorSummary = (watch: WatchSummary, connectedSources: number, sources: SourceSummary[]) => {
  const sourceLabel = `${connectedSources} source${connectedSources === 1 ? '' : 's'}`
  const connectors = watch.sources.map(source => sourceDisplayName(source.connector, sources)).join(' · ')

  return connectors ? `${sourceLabel} · ${connectors}` : sourceLabel
}

const sourceDisplayName = (connector: string, sources: SourceSummary[]) => {
  const source = sources.find(s => s.connector === connector)
  return formatSourceName(source?.name || connector)
}

const sourceStateLabel = (statuses: NormalizedSourceStatus[]) => {
  if (statuses.some(status => status === 'failed')) return 'Failed'
  if (statuses.some(status => status === 'degraded')) return 'Degraded'
  if (statuses.some(status => status === 'paused')) return 'Paused'
  if (statuses.some(status => status === 'healthy')) return 'Healthy'
  return 'Unknown'
}

export default function WatchList() {
  const [watches, setWatches] = useState<WatchSummary[]>([])
  const [sources, setSources] = useState<SourceSummary[]>([])
  const [showForm, setShowForm] = useState(false)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [search, setSearch] = useState('')
  const [watchFilter, setWatchFilter] = useState<WatchFilter>('all')
  const [healthFilter, setHealthFilter] = useState<HealthFilter>('all')
  const [pageInfo, setPageInfo] = useState({ page: 1, pageSize: 0, total: 0 })
  const [toast, setToast] = useState<{ message: string; variant: ToastVariant } | null>(null)

  usePageTitle('Dashboard')

  useEffect(() => {
    void fetchDashboardData({ initial: true })
  }, [])

  const fetchDashboardData = async ({ initial = false }: { initial?: boolean } = {}) => {
    if (initial) setLoading(true)
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

  const handleRefresh = async () => {
    setRefreshing(true)
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
      setError(err instanceof Error ? err.message : 'Failed to refresh')
    } finally {
      setRefreshing(false)
    }
  }

  const handleWatchCreated = (watch: WatchSummary) => {
    setWatches(prev => [watch, ...prev])
    setShowForm(false)
  }

  const handleExport = () => {
    window.open('/api/export?resource=all&format=json', '_blank', 'noopener,noreferrer')
  }

  const toggleWatch = async (watch: WatchSummary) => {
    try {
      const response = await fetch(`/api/watches/${watch.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: watch.name,
          query: watch.query,
          category: watch.category,
          sources: watch.sources.map(source => ({
            connector: source.connector,
            enabled: source.enabled ?? true,
            config: {},
          })),
          filters: {
            price_max: null,
            currency: 'GBP',
            condition_filter: { conditions: [], dedup_enabled: false },
            exclude_patterns: [],
            spec_match: {},
            min_seller_feedback: null,
            min_seller_feedback_pct: null,
          },
          schedule: {
            interval: watch.schedule?.interval || '4h',
            timezone: watch.schedule?.timezone || 'UTC',
            time_window: watch.schedule?.time_window || null,
          },
          grouping: { enabled: false, product_key: null },
          notifications: {
            events: ['new_listing', 'price_drop', 'stock_change'],
            channels: ['webhook'],
            webhook_url: null,
            telegram_bot_token: null,
            telegram_chat_id: null,
            discord_webhook_url: null,
          },
          enabled: !watch.enabled,
        }),
      })
      if (!response.ok) throw new Error('Failed to toggle watch')
      const updatedWatch: WatchSummary = await response.json()
      setWatches(prev => prev.map(w => (w.id === watch.id ? updatedWatch : w)))
      setToast({ message: updatedWatch.enabled ? 'Watch resumed' : 'Watch paused', variant: 'success' })
    } catch (err) {
      setToast({ message: err instanceof Error ? err.message : 'Failed to toggle watch', variant: 'error' })
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
    const displayName = formatWatchLabel(watch.name)
    const displayMeta = formatWatchMeta(watch)
    const healthyConnections = rowSourceStatuses.filter(status => status === 'healthy').length
    const degradedConnections = rowSourceStatuses.filter(status => status === 'degraded').length
    const failedConnections = rowSourceStatuses.filter(status => status === 'failed').length

    return {
      watch,
      rowState,
      connectedSources,
      displayName,
      displayMeta,
      healthyConnections,
      degradedConnections,
      failedConnections,
    }
  })

  const handleCheckNow = async (watchId: number) => {
    try {
      const response = await fetch(`/api/watches/${watchId}/check`, { method: "POST" })
      if (!response.ok) throw new Error("Failed to trigger watch check")
      await fetchDashboardData()
      setToast({ message: "Check triggered successfully", variant: "success" })
    } catch (err) {
      setToast({ message: err instanceof Error ? err.message : "Failed to trigger watch check", variant: "error" })
    }
  }

  if (loading) {
    return (
      <div className="state-panel state-panel--loading">
        <div className="state-panel__title">Loading control center</div>
        <div className="state-panel__description">Syncing watches and connector health into the redesigned dashboard.</div>
      </div>
    )
  }

  if (error) {
    return (
      <EmptyState
        title="Dashboard failed to load"
        description={error}
        icon="!"
        action={<button className="btn btn-secondary" onClick={() => void fetchDashboardData()}>Try again</button>}
      />
    )
  }

  return (
    <div className="dashboard-stack">
      <TopActionBar
        eyebrow="Operations control center"
        title="Watch dashboard"
        description=""
        actions={(
          <>
            <button className="btn btn-secondary" onClick={() => void handleRefresh()} disabled={refreshing}>
              {refreshing ? 'Refreshing...' : 'Refresh'}
            </button>
            <button className="btn btn-secondary" onClick={handleExport}>
              Export
            </button>
            <button className="btn btn-primary" onClick={() => setShowForm(true)}>
              + New watch
            </button>
          </>
        )}
      />

      <div className="kpi-grid">
        <SectionCard title="Active watches" subtitle="Currently checking on schedule">
          <div className="kpi-card__value" aria-live="polite">{kpis.activeWatches}</div>
          <div className="kpi-card__meta">{kpis.pausedWatches} paused · {watches.length} total</div>
        </SectionCard>
        <SectionCard title="Watches checked" subtitle="Watches with a recorded check">
          <div className="kpi-card__value" aria-live="polite">{kpis.checkedWatches}</div>
          <div className="kpi-card__meta">{pageInfo.total} listed in the current page window</div>
        </SectionCard>
        <SectionCard title="Healthy sources" subtitle="Connector posture across the board">
          <div className="kpi-card__value" aria-live="polite">{kpis.healthySources}</div>
          <div className="kpi-card__meta">{kpis.degradedSources} degraded · {kpis.failedSources} failed</div>
        </SectionCard>
        <SectionCard title="Attention needed" subtitle="Anything worth drilling into">
          <div className="kpi-card__value" aria-live="polite">{kpis.degradedSources + kpis.failedSources}</div>
          <div className="kpi-card__meta">Source health issues and manual follow-up</div>
        </SectionCard>
      </div>

      <div className="toolbar watch-toolbar">
        <input
          className="toolbar__search"
          type="search"
          placeholder="Search watches…"
          value={search}
          onChange={e => setSearch(e.target.value)}
          aria-label="Search watches"
        />
        <div className="watch-filter-group" role="group" aria-label="Watch status filter">
          <select
            value={watchFilter}
            onChange={e => setWatchFilter(e.target.value as WatchFilter)}
            aria-label="Filter by watch status"
            className="toolbar__filter-select"
          >
            <option value="all">All watches</option>
            <option value="active">Active only</option>
            <option value="paused">Paused only</option>
          </select>
        </div>
        <div className="watch-filter-group" role="group" aria-label="Source health filter">
          <select
            value={healthFilter}
            onChange={e => setHealthFilter(e.target.value as HealthFilter)}
            aria-label="Filter by source health"
            className="toolbar__filter-select"
          >
            <option value="all">Any source state</option>
            <option value="healthy">Healthy only</option>
            <option value="issues">Needs attention</option>
          </select>
        </div>
      </div>

      <div className="dashboard-grid">
        <SectionCard
          title="Watch queue"
          subtitle=""
          action={<StatusBadge variant="accent">Showing {filteredWatches.length} of {pageInfo.total} watches</StatusBadge>}
        >
          {watchRows.length === 0 ? (
            <EmptyState
              title="No watches match the current filters"
              description="Broaden the search or switch the source-health filter to reveal more watches."
              action={<button className="btn btn-primary" onClick={() => setShowForm(true)} aria-label="Create new watch">Create watch</button>}
            />
          ) : (
            <div className="table-scroll">
              <table className="watch-table" aria-label="Watch queue table">
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
                  {watchRows.map(({ watch, rowState, connectedSources, displayName, displayMeta, healthyConnections, degradedConnections, failedConnections }) => (
                    <tr key={watch.id}>
                      <td data-label="Watch">
                        <div className="watch-row__name">
                          <div className="watch-row__title">
                            <Link to={`/watch/${watch.id}`} className="watch-table__link">
                              {displayName}
                            </Link>
                          </div>
                          <div className="watch-row__meta">{displayMeta}</div>
                          <div className="watch-table__secondary">{formatConnectorSummary(watch, connectedSources, sources)}</div>
                        </div>
                      </td>
                      <td data-label="Source state">
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
                      <td data-label="Last check / change">
                        <div className="watch-row__name">
                          <div className="watch-row__title">{formatDateTime(watch.last_check_at)}</div>
                          <div className="watch-table__secondary">
                            {watch.enabled
                              ? `Schedule every ${watch.schedule?.interval || '—'}`
                              : 'Paused watch · no scheduled checks'}
                          </div>
                        </div>
                      </td>
                      <td data-label="Status">
                        <StatusBadge variant={watch.enabled ? 'active' : 'paused'}>
                          {watch.enabled ? 'Active' : 'Paused'}
                        </StatusBadge>
                      </td>
                      <td data-label="Primary action">
                        <div className="watch-row__actions">
                          <button
                            type="button"
                            className="btn btn-secondary btn--icon"
                            onClick={() => toggleWatch(watch)}
                            aria-label={watch.enabled ? `Pause watch ${displayName}` : `Resume watch ${displayName}`}
                            title={watch.enabled ? 'Pause' : 'Resume'}
                          >
                            {watch.enabled ? '⏸' : '▶'}
                          </button>
                          <button
                            type="button"
                            className="btn btn-primary btn--icon"
                            onClick={() => void handleCheckNow(watch.id).catch(err => setToast({
                              message: err instanceof Error ? err.message : 'Failed to trigger watch check',
                              variant: 'error'
                            }))}
                            aria-label={`Check watch ${displayName} now`}
                            title="Check now"
                          >
                            ↻
                          </button>
                          <button
                            type="button"
                            className="btn btn-danger btn--icon"
                            onClick={() => deleteWatch(watch.id)}
                            aria-label={`Delete watch ${displayName}`}
                            title="Delete"
                          >
                            🗑
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
          subtitle=""
          action={<StatusBadge variant="neutral">{sources.length} connectors</StatusBadge>}
        >
          <SourceHealth sources={sources} />
        </SectionCard>
      </div>

      {toast && (
        <Toast
          message={toast.message}
          variant={toast.variant}
          onClose={() => setToast(null)}
        />
      )}

      <button
        className="mobile-fab"
        onClick={() => setShowForm(true)}
        aria-label="Create new watch"
        title="Create new watch"
      >
        <span style={{ fontSize: '24px', fontWeight: 'bold' }}>+</span>
      </button>

      <WatchForm
        open={showForm}
        onClose={() => setShowForm(false)}
        onCreated={handleWatchCreated}
      />
    </div>
  )
}