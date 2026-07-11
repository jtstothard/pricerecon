import { useState } from 'react'

interface Watch {
  id: number
  name: string
  query: string
  category: string
  interval: string
  enabled: boolean
  last_check_at: string | null
  next_check_at: string | null
}

interface WatchFormProps {
  onClose: () => void
  onCreated: (watch: Watch) => void
}

export default function WatchForm({ onClose, onCreated }: WatchFormProps) {
  const [formData, setFormData] = useState({
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

      const newWatch = await response.json()
      onCreated(newWatch)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create watch')
    } finally {
      setLoading(false)
    }
  }

  const toggleSource = (source: string) => {
    setFormData({
      ...formData,
      sources: formData.sources.includes(source)
        ? formData.sources.filter(s => s !== source)
        : [...formData.sources, source],
    })
  }

  const toggleCondition = (condition: string) => {
    setFormData({
      ...formData,
      filters: {
        ...formData.filters,
        condition: formData.filters.condition.includes(condition)
          ? formData.filters.condition.filter(c => c !== condition)
          : [...formData.filters.condition, condition],
      },
    })
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <h3>Create Watch</h3>
          <button className="close-btn" onClick={onClose}>×</button>
        </div>

        {error && <div className="error">{error}</div>}

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="name">Name</label>
            <input
              id="name"
              type="text"
              value={formData.name}
              onChange={e => setFormData({ ...formData, name: e.target.value })}
              required
            />
          </div>

          <div className="form-group">
            <label htmlFor="query">Query</label>
            <input
              id="query"
              type="text"
              value={formData.query}
              onChange={e => setFormData({ ...formData, query: e.target.value })}
              required
            />
          </div>

          <div className="form-group">
            <label htmlFor="category">Category</label>
            <select
              id="category"
              value={formData.category}
              onChange={e => setFormData({ ...formData, category: e.target.value })}
            >
              <option value="gpu">GPU</option>
              <option value="cpu">CPU</option>
              <option value="ram">RAM</option>
              <option value="storage">Storage</option>
              <option value="motherboard">Motherboard</option>
              <option value="other">Other</option>
            </select>
          </div>

          <div className="form-group">
            <label htmlFor="interval">Check Interval</label>
            <select
              id="interval"
              value={formData.interval}
              onChange={e => setFormData({ ...formData, interval: e.target.value })}
            >
              <option value="1h">Every hour</option>
              <option value="4h">Every 4 hours</option>
              <option value="8h">Every 8 hours</option>
              <option value="12h">Every 12 hours</option>
              <option value="1d">Every day</option>
            </select>
          </div>

          <div className="form-group">
            <label>Sources</label>
            <div className="checkbox-group">
              {['ebay', 'cex', 'amazon_uk'].map(source => (
                <label key={source} className="checkbox-label">
                  <input
                    type="checkbox"
                    checked={formData.sources.includes(source)}
                    onChange={() => toggleSource(source)}
                  />
                  {source}
                </label>
              ))}
            </div>
          </div>

          <div className="form-group">
            <label htmlFor="price_max">Max Price (optional)</label>
            <input
              id="price_max"
              type="number"
              step="0.01"
              value={formData.filters.price_max}
              onChange={e => setFormData({
                ...formData,
                filters: { ...formData.filters, price_max: e.target.value }
              })}
            />
          </div>

          <div className="form-group">
            <label>Condition</label>
            <div className="checkbox-group">
              {['new', 'new_open_box', 'refurbished', 'used_like_new', 'used_good', 'used_fair'].map(cond => (
                <label key={cond} className="checkbox-label">
                  <input
                    type="checkbox"
                    checked={formData.filters.condition.includes(cond)}
                    onChange={() => toggleCondition(cond)}
                  />
                  {cond.replace(/_/g, ' ')}
                </label>
              ))}
            </div>
          </div>

          <div className="modal-actions">
            <button type="button" className="btn btn-secondary" onClick={onClose} disabled={loading}>
              Cancel
            </button>
            <button type="submit" className="btn btn-primary" disabled={loading}>
              {loading ? 'Creating...' : 'Create Watch'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
