import { createContext, useContext, useState, useEffect, ReactNode } from 'react'

interface SourceSummary {
  connector: string
  name: string
  status: string
  last_error: string | null
}

interface WatchSummary {
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

interface DataContextType {
  watches: WatchSummary[]
  sources: SourceSummary[]
  loading: boolean
  refresh: () => Promise<void>
  metrics: {
    totalWatches: number
    activeWatches: number
    totalEvents: number
    healthySources: number
  }
}

const DataContext = createContext<DataContextType | undefined>(undefined)

export function DataProvider({ children }: { children: ReactNode }) {
  const [watches, setWatches] = useState<WatchSummary[]>([])
  const [sources, setSources] = useState<SourceSummary[]>([])
  const [loading, setLoading] = useState(true)

  const fetchData = async () => {
    try {
      const [watchesRes, sourcesRes] = await Promise.all([
        fetch('/api/watches?page=1&page_size=100'),
        fetch('/api/sources'),
      ])

      if (watchesRes.ok) {
        const watchesData = await watchesRes.json()
        setWatches(Array.isArray(watchesData.items) ? watchesData.items : [])
      }

      if (sourcesRes.ok) {
        const sourcesData = await sourcesRes.json()
        setSources(Array.isArray(sourcesData) ? sourcesData : [])
      }
    } catch (error) {
      console.error('Failed to fetch data:', error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [])

  const metrics = {
    totalWatches: watches.length,
    activeWatches: watches.filter(w => w.enabled).length,
    totalEvents: 0, // We could fetch event count if needed
    healthySources: sources.filter(s => {
      const status = s.status.toLowerCase()
      return status === 'healthy' || status === 'ok'
    }).length,
  }

  return (
    <DataContext.Provider value={{ watches, sources, loading, refresh: fetchData, metrics }}>
      {children}
    </DataContext.Provider>
  )
}

export function useData() {
  const context = useContext(DataContext)
  if (!context) {
    throw new Error('useData must be used within DataProvider')
  }
  return context
}