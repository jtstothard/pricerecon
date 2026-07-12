export interface WatchSummary {
  id: number
  name: string
  query: string
  category: string | null
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
  status: string
  last_error: string | null
}
