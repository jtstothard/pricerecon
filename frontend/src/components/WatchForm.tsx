import { useState, useEffect, useRef } from 'react'
import { formatSourceName } from '../lib/sourceNames'
import type { WatchSummary, SourceSummary } from './watchTypes'

interface WatchFormData {
  name: string
  query: string
  category: string
  interval: string
  enabled: boolean
  sources: string[]
  filters: {
    price_max: string
    condition: string[]
  }
}

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

function SourceMultiSelect({ sources, selected, onToggle, disabled }: {
  sources: SourceSummary[]
  selected: string[]
  onToggle: (connector: string) => void
  disabled?: boolean
}) {
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
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

      {open && (
        <div className="source-multiselect__dropdown">
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
              filtered.map(source => {
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
              })
            )}
          </div>
        </div>
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
      const payload = {
        ...formData,
        filters: {
          ...formData.filters,
          price_max: formData.filters.price_max ? parseFloat(formData.filters.price_max) : null,
        },
      }
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
