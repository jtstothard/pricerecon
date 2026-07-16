export interface WatchFormData {
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

export interface WatchCreatePayload {
  name: string
  query: string
  category: string
  enabled: boolean
  sources: Array<{ connector: string; enabled: boolean }>
  schedule: {
    interval: string
    timezone: string
  }
  filters: {
    price_max: number | null
    condition_filter: {
      conditions: string[]
      dedup_enabled: boolean
    }
    currency: string
    exclude_patterns: string[]
    spec_match: Record<string, unknown>
  }
  grouping: {
    enabled: boolean
  }
  notifications: {
    events: string[]
    channels: string[]
  }
}

export function buildWatchCreatePayload(formData: WatchFormData): WatchCreatePayload {
  const { sources, interval, filters, ...rest } = formData

  return {
    ...rest,
    // Transform sources from string[] to object[]
    sources: sources.map(connector => ({ connector, enabled: true })),
    // Nest interval under schedule
    schedule: { interval, timezone: 'UTC' },
    // Transform filters structure
    filters: {
      price_max: filters.price_max ? parseFloat(filters.price_max) : null,
      condition_filter: {
        conditions: filters.condition,
        dedup_enabled: false,
      },
      currency: 'GBP',
      exclude_patterns: [],
      spec_match: {},
    },
    // Add required defaults
    grouping: { enabled: false },
    notifications: {
      events: ['new_listing', 'price_drop', 'stock_change'],
      channels: ['webhook'],
    },
  }
}