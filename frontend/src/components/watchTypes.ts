export interface WatchSummary {
  id: number
  name: string
  query: string
  category: string | null
  display_title?: string | null
  synonym_groups?: string[][]
  source_queries?: Record<string, string>
  filters?: {
    price_max?: number | string | null
    currency?: string
    condition_filter?: { conditions?: string[]; dedup_enabled?: boolean }
    exclude_patterns?: string[]
    spec_match?: {
      gpu_model?: string | null
      ram_gb?: number | null
      storage_gb?: number | null
      cpu_model?: string | null
      synonym_groups?: string[][]
      excluded_title_terms?: string[]
      required_title_terms?: string[]
    }
    min_price_gbp?: number | null
    component_subject_pattern?: string | null
    enforce_component_pattern?: boolean
    enforce_price_floor?: boolean
    min_seller_feedback?: number | null
    min_seller_feedback_pct?: number | string | null
  }
  enabled: boolean
  last_check_at: string | null
  sources: { connector: string; enabled?: boolean; config?: Record<string, unknown> }[]
  schedule?: {
    interval?: string
    timezone?: string
    time_window?: Record<string, unknown> | null
  }
  grouping?: { enabled: boolean; product_key?: string | null }
  notifications?: {
    events: string[]
    channels: string[]
    webhook_url?: string | null
    telegram_bot_token?: string | null
    telegram_chat_id?: string | null
    discord_webhook_url?: string | null
  }
}

export interface SourceSummary {
  connector: string
  name: string
  source_type?: string
  status: string
  last_error: string | null
}
