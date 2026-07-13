import { useState, useEffect } from 'react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import EmptyState from './ui/EmptyState'

interface PriceDataPoint {
  timestamp: string
  price: number
  source: string
}

export default function PriceHistoryChart({ watchId }: { watchId: number }) {
  const [data, setData] = useState<PriceDataPoint[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchHistory()
  }, [watchId])

  const fetchHistory = async () => {
    try {
      const response = await fetch(`/api/watches/${watchId}/history`)
      if (!response.ok) throw new Error('Failed to fetch history')
      const historyData = await response.json()
      const items = Array.isArray(historyData) ? historyData : historyData.items || []

      const chartData = items.map((point: { timestamp: string; price: number; source: string }) => ({
        timestamp: new Date(point.timestamp).toLocaleDateString(),
        price: point.price,
        source: point.source,
      }))

      setData(chartData)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load price history')
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return <div className="state-panel state-panel--loading">Loading price history…</div>
  }
  if (error) {
    return <EmptyState title="Price history failed to load" description={error} action={<button className="btn btn-secondary" onClick={() => void fetchHistory()}>Try again</button>} />
  }
  if (data.length === 0) return <EmptyState title="No price history yet" description="The chart will appear after the first recorded checks." />

  return (
    <div className="chart-card__wrap">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(148, 163, 184, 0.14)" />
          <XAxis dataKey="timestamp" tick={{ fill: '#b3bdd4', fontSize: 12 }} axisLine={{ stroke: 'rgba(148, 163, 184, 0.2)' }} />
          <YAxis tick={{ fill: '#b3bdd4', fontSize: 12 }} axisLine={{ stroke: 'rgba(148, 163, 184, 0.2)' }} />
          <Tooltip />
          <Line type="monotone" dataKey="price" stroke="#8796ff" strokeWidth={2.5} dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
