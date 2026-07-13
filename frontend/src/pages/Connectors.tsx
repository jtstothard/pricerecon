import { useState, useEffect } from 'react'
import SourceHealth from '../components/SourceHealth'
import SectionCard from '../components/ui/SectionCard'
import type { SourceSummary } from '../components/watchTypes'
import { usePageTitle } from '../hooks/usePageTitle'

export default function Connectors() {
  usePageTitle('Connectors')
  const [sources, setSources] = useState<SourceSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetch('/api/sources')
      .then(res => {
        if (!res.ok) throw new Error('Failed to fetch sources')
        return res.json()
      })
      .then((data: SourceSummary[]) => {
        setSources(Array.isArray(data) ? data : [])
        setError(null)
      })
      .catch(err => {
        setError(err instanceof Error ? err.message : 'Failed to load connectors')
      })
      .finally(() => {
        setLoading(false)
      })
  }, [])

  if (loading) {
    return (
      <div className="page">
        <h1 id="page-title" tabIndex={-1}>Connectors</h1>
        <p className="page-empty-state">Loading connector health data...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="page">
        <h1 id="page-title" tabIndex={-1}>Connectors</h1>
        <p className="page-empty-state">{error}</p>
      </div>
    )
  }

  return (
    <div className="page">
      <h1 id="page-title" tabIndex={-1}>Connectors</h1>
      <SectionCard title="Connector Health" subtitle="">
        <SourceHealth sources={sources} />
      </SectionCard>
    </div>
  )
}