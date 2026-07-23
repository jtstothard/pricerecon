export interface WatchSummary {
  id: number
  name: string
  query: string
  category: string | null
  display_title?: string | null
  synonym_groups?: string[][]
  source_queries?: Record<string, string>
  filters?: {
    price_max?: number | null
    condition_filter?: { conditions?: string[] }
    exclude_patterns?: string[]
  }
  enabled: boolean
  last_check_at: string | null
  sources: { connector: string; enabled?: boolean }[]
  schedule?: {
    interval?: string
    timezone?: string
    time_window?: string | null
  }
}

export interface SourceSummary {
  connector: string
  name: string
  source_type?: string
  status: string
  last_error: string | null
}
