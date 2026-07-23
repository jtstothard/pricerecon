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
  display_title: string
  synonym_groups: string[][]
  excluded_terms: string[]
  /** Optional so callers using the pre-advanced form shape remain valid. */
  source_queries?: Record<string, string>
  advancedMode?: boolean
}

export function validateWatchForm(formData: WatchFormData): string | null {
  if (!formData.name.trim()) return 'Name is required.'
  if (!formData.query.trim()) return 'Query is required.'
  if (formData.sources.length === 0) return 'Select at least one source.'
  if (formData.synonym_groups.some(group => group.some(term => !term.trim()))) {
    return 'Complete or remove every synonym term.'
  }
  return null
}

export interface WatchCreatePayload {
  name: string
  query: string
  category: string
  display_title: string | null
  synonym_groups: string[][]
  source_queries: Record<string, string>
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
  const {
    sources,
    interval,
    filters,
    display_title,
    synonym_groups,
    excluded_terms,
    source_queries = {},
    advancedMode = false,
    ...rest
  } = formData
  const normalizedSynonymGroups = synonym_groups
    .map(group => group.map(term => term.trim()).filter(Boolean))
    .filter(group => group.length > 0)
  const normalizedExcludedTerms = excluded_terms.map(term => term.trim()).filter(Boolean)

  // Clean up source_queries: only include non-empty values for enabled connectors.
  // Raw strings are intentionally not trimmed so connector syntax is preserved exactly.
  const cleanedSourceQueries: Record<string, string> = {}
  for (const [connector, query] of Object.entries(advancedMode ? source_queries : {})) {
    if (sources.includes(connector) && query.trim()) {
      cleanedSourceQueries[connector] = query
    }
  }

  return {
    ...rest,
    display_title: display_title.trim() || null,
    synonym_groups: normalizedSynonymGroups,
    source_queries: cleanedSourceQueries,
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
      exclude_patterns: normalizedExcludedTerms,
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