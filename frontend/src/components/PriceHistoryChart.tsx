import { useState, useEffect } from 'react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'

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
      
      // Transform data for Recharts
      const chartData = items.map((point: any) => ({ 
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

  if (loading) return <div className="loading">Loading price history...</div>
  if (error) return <div className="error">{error}</div>
  if (data.length === 0) return <p className="empty-state">No price history yet</p>

  return (
    <div>
      <h3>Price History</h3>
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="timestamp" />
          <YAxis />
          <Tooltip />
          <Line type="monotone" dataKey="price" stroke="#8884d8" />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
