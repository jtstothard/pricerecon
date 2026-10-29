import type { WatchSummary } from '../components/watchTypes'

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

export const formDataFromWatch = (watch: WatchSummary): WatchFormData => ({
  name: watch.name,
  query: watch.query,
  category: watch.category || 'other',
  interval: watch.schedule?.interval || '4h',
  enabled: watch.enabled,
  sources: watch.sources.filter(source => source.enabled !== false).map(source => source.connector),
  filters: {
    price_max: watch.filters?.price_max == null ? '' : String(watch.filters.price_max),
    condition: [...(watch.filters?.condition_filter?.conditions || [])],
  },
  display_title: watch.display_title || '',
  synonym_groups: watch.synonym_groups?.map(group => [...group]) || [],
  excluded_terms: [...(watch.filters?.exclude_patterns || [])],
  source_queries: { ...watch.source_queries },
  advancedMode: watch.source_queries != null && Object.keys(watch.source_queries).length > 0,
})

type WatchEditPayload = Pick<WatchSummary,
  'name' | 'query' | 'category' | 'display_title' | 'synonym_groups' | 'source_queries' |
  'enabled' | 'sources' | 'filters' | 'schedule' | 'grouping' | 'notifications'
>

export function buildWatchEditPayload(formData: WatchFormData, watch: WatchSummary): WatchEditPayload {
  const initial = formDataFromWatch(watch)
  const created = buildWatchCreatePayload(formData)
  const unchanged = (current: unknown, original: unknown) => JSON.stringify(current) === JSON.stringify(original)

  // PUT replaces complete nested configs. Start from saved intent and change only
  // fields exposed by this form; create defaults must not become edit defaults.
  return {
    ...created,
    category: formData.category === initial.category ? watch.category : created.category,
    display_title: formData.display_title === initial.display_title ? watch.display_title : created.display_title,
    synonym_groups: unchanged(formData.synonym_groups, initial.synonym_groups)
      ? watch.synonym_groups ?? [] : created.synonym_groups,
    source_queries: formData.advancedMode
      ? Object.fromEntries(Object.entries(formData.source_queries ?? {}).filter(([connector, query]) => (
        query === watch.source_queries?.[connector] || query.trim()
      )))
      : {},
    sources: [
      ...watch.sources.map(source => ({ ...source, enabled: formData.sources.includes(source.connector) })),
      ...created.sources.filter(source => !watch.sources.some(saved => saved.connector === source.connector)),
    ],
    schedule: { ...watch.schedule, interval: formData.interval },
    filters: {
      ...(watch.filters ?? created.filters),
      ...(formData.filters.price_max !== initial.filters.price_max ? { price_max: created.filters.price_max } : {}),
      ...(!unchanged(formData.filters.condition, initial.filters.condition) ? {
        condition_filter: { ...watch.filters?.condition_filter, conditions: formData.filters.condition },
      } : {}),
      ...(!unchanged(formData.excluded_terms, initial.excluded_terms) ? { exclude_patterns: created.filters.exclude_patterns } : {}),
    },
    grouping: watch.grouping ?? created.grouping,
    notifications: watch.notifications ?? created.notifications,
  }
}

export function validateWatchForm(formData: WatchFormData, watch?: WatchSummary | null): string | null {
  if (!formData.name.trim()) return 'Name is required.'
  if (!formData.query.trim()) return 'Query is required.'
  if (formData.sources.length === 0 && (!watch || watch.sources.some(source => source.enabled !== false))) {
    return 'Select at least one source.'
  }
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
