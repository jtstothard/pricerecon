import * as React from "react"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "./ui/dialog"
import { Button } from "./ui/button"
import { Label } from "./ui/label"
import { Input } from "./ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "./ui/select"
import { Checkbox } from "./ui/checkbox"
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

export default function WatchForm({ open, onClose, onCreated }: WatchFormProps) {
  const [formData, setFormData] = React.useState<WatchFormData>({
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
  const [loading, setLoading] = React.useState(false)
  const [error, setError] = React.useState<string | null>(null)

  // Fetch available sources
  const [availableSources, setAvailableSources] = React.useState<SourceSummary[]>([])
  const [sourcesLoading, setSourcesLoading] = React.useState(true)

  React.useEffect(() => {
    fetch('/api/sources')
      .then(res => {
        if (!res.ok) throw new Error('Failed to fetch sources')
        return res.json()
      })
      .then((data: SourceSummary[]) => {
        setAvailableSources(Array.isArray(data) ? data : [])
      })
      .catch(err => {
        console.error('Failed to load sources:', err)
      })
      .finally(() => {
        setSourcesLoading(false)
      })
  }, [])

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

  const handleCategoryChange = (value: string | null) => {
    if (value) setFormData(prev => ({ ...prev, category: value }))
  }

  const handleIntervalChange = (value: string | null) => {
    if (value) setFormData(prev => ({ ...prev, interval: value }))
  }

  return (
    <Dialog open={open} onOpenChange={(isOpen) => !isOpen && onClose()}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Create watch</DialogTitle>
          <DialogDescription>
            Configure a new watch to track prices across your selected sources.
          </DialogDescription>
        </DialogHeader>

        {error && (
          <div className="p-3 text-sm text-destructive-foreground bg-destructive/10 rounded-lg border border-destructive/20">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="name">Name</Label>
              <Input
                id="name"
                value={formData.name}
                onChange={e => setFormData(prev => ({ ...prev, name: e.target.value }))}
                placeholder="My GPU watch"
                required
                disabled={loading}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="query">Query</Label>
              <Input
                id="query"
                value={formData.query}
                onChange={e => setFormData(prev => ({ ...prev, query: e.target.value }))}
                placeholder="RTX 4090 24GB"
                required
                disabled={loading}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="category">Category</Label>
              <Select
                value={formData.category}
                onValueChange={handleCategoryChange}
                disabled={loading}
              >
                <SelectTrigger id="category">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="gpu">GPU</SelectItem>
                  <SelectItem value="cpu">CPU</SelectItem>
                  <SelectItem value="ram">RAM</SelectItem>
                  <SelectItem value="storage">Storage</SelectItem>
                  <SelectItem value="motherboard">Motherboard</SelectItem>
                  <SelectItem value="other">Other</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="interval">Check Interval</Label>
              <Select
                value={formData.interval}
                onValueChange={handleIntervalChange}
                disabled={loading}
              >
                <SelectTrigger id="interval">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="1h">Every hour</SelectItem>
                  <SelectItem value="4h">Every 4 hours</SelectItem>
                  <SelectItem value="8h">Every 8 hours</SelectItem>
                  <SelectItem value="12h">Every 12 hours</SelectItem>
                  <SelectItem value="1d">Every day</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="col-span-2 space-y-2">
              <Label>Sources</Label>
              <div className="space-y-2">
                <div className="text-xs text-muted-foreground">
                  Select the sources you want to check:
                </div>
                {sourcesLoading ? (
                  <div className="text-sm text-muted-foreground">Loading sources...</div>
                ) : (
                  <div className="grid grid-cols-2 gap-2">
                    {availableSources.map(source => (
                      <label key={source.connector} className="flex items-center space-x-2 cursor-pointer">
                        <Checkbox
                          checked={formData.sources.includes(source.connector)}
                          onCheckedChange={() => toggleSource(source.connector)}
                          disabled={loading}
                        />
                        <span className="text-sm">
                          {formatSourceName(source.name || source.connector)}
                        </span>
                      </label>
                    ))}
                  </div>
                )}
                {formData.sources.length > 0 && (
                  <div className="flex flex-wrap gap-1">
                    {formData.sources.map(connector => {
                      const source = availableSources.find(s => s.connector === connector)
                      return (
                        <span
                          key={connector}
                          className="inline-flex items-center gap-1 rounded-full bg-primary/10 text-primary px-2 py-0.5 text-xs"
                        >
                          {formatSourceName(source?.name || connector)}
                          <button
                            type="button"
                            onClick={() => toggleSource(connector)}
                            className="ml-1 hover:text-primary-foreground"
                            aria-label={`Remove ${formatSourceName(source?.name || connector)}`}
                          >
                            ×
                          </button>
                        </span>
                      )
                    })}
                  </div>
                )}
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="price_max">Max Price (optional)</Label>
              <Input
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

            <div className="col-span-2 space-y-2">
              <Label>Condition</Label>
              <div className="grid grid-cols-3 gap-2">
                {[{ value: 'new', label: 'New' }, { value: 'new_open_box', label: 'New Open Box' }, { value: 'refurbished', label: 'Refurbished' }, { value: 'used_like_new', label: 'Used Like New' }, { value: 'used_good', label: 'Used Good' }, { value: 'used_fair', label: 'Used Fair' }].map(cond => (
                  <div key={cond.value} className="flex items-center space-x-2">
                    <Checkbox
                      id={`condition-${cond.value}`}
                      checked={formData.filters.condition.includes(cond.value)}
                      onCheckedChange={() => toggleCondition(cond.value)}
                      disabled={loading}
                    />
                    <Label
                      htmlFor={`condition-${cond.value}`}
                      className="text-sm font-normal cursor-pointer"
                    >
                      {cond.label}
                    </Label>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <DialogFooter>
            <Button type="button" variant="secondary" onClick={onClose} disabled={loading}>
              Cancel
            </Button>
            <Button type="submit" disabled={loading}>
              {loading ? 'Creating...' : 'Create Watch'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}