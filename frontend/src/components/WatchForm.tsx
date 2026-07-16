import { useState, useEffect, useLayoutEffect, useRef } from 'react'
import { createPortal } from 'react-dom'
import { formatSourceName } from '../lib/sourceNames'
import { buildWatchCreatePayload, type WatchFormData } from '../lib/watchPayload'
import type { WatchSummary, SourceSummary } from './watchTypes'

interface WatchFormProps {
  open: boolean
  onClose: () => void
  onCreated: (watch: WatchSummary) => void
}

const CATEGORIES = [
  { value: 'gpu', label: 'GPU' },
  { value: 'cpu', label: 'CPU' },
  { value: 'ram', label: 'RAM' },
  { value: 'storage', label: 'Storage' },
  { value: 'motherboard', label: 'Motherboard' },
  { value: 'other', label: 'Other' },
]

const INTERVALS = [
  { value: '1h', label: 'Every hour' },
  { value: '4h', label: 'Every 4 hours' },
  { value: '8h', label: 'Every 8 hours' },
  { value: '12h', label: 'Every 12 hours' },
  { value: '1d', label: 'Every day' },
]

const CONDITIONS = [
  { value: 'new', label: 'New' },
  { value: 'new_open_box', label: 'New Open Box' },
  { value: 'refurbished', label: 'Refurbished' },
  { value: 'used_like_new', label: 'Used Like New' },
  { value: 'used_good', label: 'Used Good' },
  { value: 'used_fair', label: 'Used Fair' },
]

const SOURCE_GROUP_ORDER = ['marketplace', 'retailer', 'community', 'aggregator'] as const

const SOURCE_GROUP_LABELS: Record<string, string> = {
  marketplace: 'Marketplaces',
  retailer: 'Retailers',
  community: 'Community & Deals',
  aggregator: 'Aggregators',
}

const CONNECTOR_GROUPS: Record<string, string> = {
  hotukdeals: 'community',
}

function getSourceGroup(connector: string, sourceType?: string): string {
  if (connector in CONNECTOR_GROUPS) return CONNECTOR_GROUPS[connector]
  return sourceType ?? 'retailer'
}

function SourceMultiSelect({ sources, selected, onToggle, disabled }: {
  sources: SourceSummary[]
  selected: string[]
  onToggle: (connector: string) => void
  disabled?: boolean
}) {
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const ref = useRef<HTMLDivElement>(null)
  const dropdownRef = useRef<HTMLDivElement>(null)
  const [dropdownPosition, setDropdownPosition] = useState<React.CSSProperties>({})

  const updateDropdownPosition = () => {
    const trigger = ref.current
    if (!trigger) return

    const rect = trigger.getBoundingClientRect()
    const gutter = 12
    const width = Math.min(rect.width, window.innerWidth - gutter * 2)
    const left = Math.min(Math.max(rect.left, gutter), window.innerWidth - width - gutter)
    const availableBelow = window.innerHeight - rect.bottom - gutter
    const availableAbove = rect.top - gutter
    const openAbove = availableBelow < 220 && availableAbove > availableBelow

    setDropdownPosition({
      position: 'fixed',
      left,
      width,
      ...(openAbove ? { bottom: window.innerHeight - rect.top + 4 } : { top: rect.bottom + 4 }),
    })
  }

  useEffect(() => {
    if (!open) return
    const handler = (e: MouseEvent) => {
      if (
        ref.current &&
        !ref.current.contains(e.target as Node) &&
        dropdownRef.current &&
        !dropdownRef.current.contains(e.target as Node)
      ) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [open])

  useLayoutEffect(() => {
    if (!open) return
    updateDropdownPosition()
    window.addEventListener('resize', updateDropdownPosition)
    window.addEventListener('scroll', updateDropdownPosition, true)
    return () => {
      window.removeEventListener('resize', updateDropdownPosition)
      window.removeEventListener('scroll', updateDropdownPosition, true)
    }
  }, [open])

  const filtered = sources.filter(s => {
    const name = formatSourceName(s.name || s.connector).toLowerCase()
    return name.includes(query.toLowerCase())
  })

  const selectedNames = selected
    .map(connector => {
      const s = sources.find(x => x.connector === connector)
      return s ? formatSourceName(s.name || s.connector) : connector
    })

  return (
    <div className="source-multiselect" ref={ref}>
      <button
        type="button"
        className="source-multiselect__trigger"
        onClick={() => setOpen(!open)}
        disabled={disabled}
      >
        {selected.length === 0 ? (
          <span className="source-multiselect__placeholder">Select sources…</span>
        ) : (
          <span className="source-multiselect__selected">
            {selectedNames.slice(0, 3).join(', ')}
            {selectedNames.length > 3 && ` +${selectedNames.length - 3} more`}
          </span>
        )}
        <span className="source-multiselect__badge">{selected.length}</span>
        <span className="source-multiselect__arrow">{open ? '▲' : '▼'}</span>
      </button>

      {open && createPortal(
        <div className="source-multiselect__dropdown source-multiselect__dropdown--portal" ref={dropdownRef} style={dropdownPosition}>
          <input
            type="text"
            className="source-multiselect__search"
            placeholder="Search sources…"
            value={query}
            onChange={e => setQuery(e.target.value)}
            autoFocus
          />
          <div className="source-multiselect__options">
            {filtered.length === 0 ? (
              <div className="source-multiselect__empty">No sources found</div>
            ) : (
              (() => {
                const groups = new Map<string, SourceSummary[]>()
                for (const s of filtered) {
                  const g = getSourceGroup(s.connector, s.source_type)
                  if (!groups.has(g)) groups.set(g, [])
                  groups.get(g)!.push(s)
                }
                const orderedGroups = [...groups.entries()].sort((a, b) => {
                  const ai = SOURCE_GROUP_ORDER.indexOf(a[0] as typeof SOURCE_GROUP_ORDER[number])
                  const bi = SOURCE_GROUP_ORDER.indexOf(b[0] as typeof SOURCE_GROUP_ORDER[number])
                  return (ai === -1 ? 99 : ai) - (bi === -1 ? 99 : bi)
                })
                return orderedGroups.map(([group, items]) => (
                  <div key={group} className="source-multiselect__group">
                    <div className="source-multiselect__group-label">
                      {SOURCE_GROUP_LABELS[group] || group}
                    </div>
                    {items.map(source => {
                      const isSelected = selected.includes(source.connector)
                      const name = formatSourceName(source.name || source.connector)
                      return (
                        <button
                          key={source.connector}
                          type="button"
                          className={`source-multiselect__option${isSelected ? ' is-selected' : ''}`}
                          onClick={() => onToggle(source.connector)}
                        >
                          <span className={`source-multiselect__check${isSelected ? ' is-checked' : ''}`}>
                            {isSelected ? '✓' : ''}
                          </span>
                          {name}
                        </button>
                      )
                    })}
                  </div>
                ))
              })()
            )}
          </div>
        </div>,
        document.body,
      )}
    </div>
  )
}

export default function WatchForm({ open, onClose, onCreated }: WatchFormProps) {
  const [formData, setFormData] = useState<WatchFormData>({
    name: '',
    query: '',
    category: 'gpu',
    interval: '4h',
    enabled: true,
    sources: ['ebay', 'cex'],
    filters: {
      price_max: '',
      condition: ['new', 'refurbished', 'used_like_new'],
    },
  })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [availableSources, setAvailableSources] = useState<SourceSummary[]>([])
  const [sourcesLoading, setSourcesLoading] = useState(true)

  useEffect(() => {
    fetch('/api/sources')
      .then(res => {
        if (!res.ok) throw new Error('Failed to fetch sources')
        return res.json()
      })
      .then((data: SourceSummary[]) => {
        setAvailableSources(Array.isArray(data) ? data : [])
      })
      .catch(() => {})
      .finally(() => setSourcesLoading(false))
  }, [])

  // Lock body scroll when open
  useEffect(() => {
    if (open) {
      document.body.style.overflow = 'hidden'
    } else {
      document.body.style.overflow = ''
    }
    return () => { document.body.style.overflow = '' }
  }, [open])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    try {
      const payload = buildWatchCreatePayload(formData)

      const response = await fetch('/api/watches', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to create watch')
      }
      const newWatch: WatchSummary = await response.json()
      onCreated(newWatch)
      onClose()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create watch')
    } finally {
      setLoading(false)
    }
  }

  const toggleSource = (connector: string) => {
    setFormData(prev => ({
      ...prev,
      sources: prev.sources.includes(connector)
        ? prev.sources.filter(s => s !== connector)
        : [...prev.sources, connector],
    }))
  }

  const toggleCondition = (condition: string) => {
    setFormData(prev => ({
      ...prev,
      filters: {
        ...prev.filters,
        condition: prev.filters.condition.includes(condition)
          ? prev.filters.condition.filter(c => c !== condition)
          : [...prev.filters.condition, condition],
      },
    }))
  }

  if (!open) return null

  return (
    <div className="watch-form-overlay" onClick={onClose}>
      <div className="watch-form-modal" onClick={e => e.stopPropagation()}>
        <div className="watch-form-header">
          <div>
            <h2 className="watch-form-title">Create watch</h2>
            <p className="watch-form-subtitle">Track prices across your selected sources.</p>
          </div>
          <button type="button" className="watch-form-close" onClick={onClose} aria-label="Close">✕</button>
        </div>

        {error && <div className="watch-form-error">{error}</div>}

        <form onSubmit={handleSubmit} className="watch-form-body">
          <div className="watch-form-grid">
            <div className="watch-form-field">
              <label htmlFor="name">Name</label>
              <input
                id="name"
                type="text"
                value={formData.name}
                onChange={e => setFormData(prev => ({ ...prev, name: e.target.value }))}
                placeholder="My GPU watch"
                required
                disabled={loading}
              />
            </div>

            <div className="watch-form-field">
              <label htmlFor="query">Query</label>
              <input
                id="query"
                type="text"
                value={formData.query}
                onChange={e => setFormData(prev => ({ ...prev, query: e.target.value }))}
                placeholder="RTX 4090 24GB"
                required
                disabled={loading}
              />
            </div>

            <div className="watch-form-field">
              <label htmlFor="category">Category</label>
              <select
                id="category"
                value={formData.category}
                onChange={e => setFormData(prev => ({ ...prev, category: e.target.value }))}
                disabled={loading}
              >
                {CATEGORIES.map(c => <option key={c.value} value={c.value}>{c.label}</option>)}
              </select>
            </div>

            <div className="watch-form-field">
              <label htmlFor="interval">Check interval</label>
              <select
                id="interval"
                value={formData.interval}
                onChange={e => setFormData(prev => ({ ...prev, interval: e.target.value }))}
                disabled={loading}
              >
                {INTERVALS.map(i => <option key={i.value} value={i.value}>{i.label}</option>)}
              </select>
            </div>

            <div className="watch-form-field watch-form-field--full">
              <label>Max price (optional)</label>
              <input
                id="price_max"
                type="number"
                step="0.01"
                value={formData.filters.price_max}
                onChange={e => setFormData(prev => ({
                  ...prev,
                  filters: { ...prev.filters, price_max: e.target.value }
                }))}
                placeholder="1000.00"
                disabled={loading}
              />
            </div>

            <div className="watch-form-field watch-form-field--full">
              <label>Sources ({formData.sources.length} selected)</label>
              {sourcesLoading ? (
                <p className="watch-form-hint">Loading sources…</p>
              ) : (
                <SourceMultiSelect
                  sources={availableSources}
                  selected={formData.sources}
                  onToggle={toggleSource}
                  disabled={loading}
                />
              )}
            </div>

            <div className="watch-form-field watch-form-field--full">
              <label>Condition</label>
              <div className="watch-form-chips">
                {CONDITIONS.map(cond => {
                  const selected = formData.filters.condition.includes(cond.value)
                  return (
                    <button
                      key={cond.value}
                      type="button"
                      className={`watch-chip${selected ? ' watch-chip--active' : ''}`}
                      onClick={() => toggleCondition(cond.value)}
                      disabled={loading}
                    >
                      {cond.label}
                    </button>
                  )
                })}
              </div>
            </div>
          </div>

          <div className="watch-form-actions">
            <button type="button" className="btn btn-secondary" onClick={onClose} disabled={loading}>
              Cancel
            </button>
            <button type="submit" className="btn btn-primary" disabled={loading}>
              {loading ? 'Creating…' : 'Create watch'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
