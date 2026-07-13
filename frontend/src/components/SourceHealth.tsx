import EmptyState from './ui/EmptyState'
import StatusBadge from './ui/StatusBadge'
import type { SourceSummary } from './watchTypes'
import { formatSourceName } from '../lib/sourceNames'

interface SourceHealthProps {
  sources: SourceSummary[]
}

type BadgeVariant = 'healthy' | 'degraded' | 'failed' | 'paused' | 'neutral'

const statusVariant = (status: string): BadgeVariant => {
  switch (status.toLowerCase()) {
    case 'healthy':
    case 'ok':
      return 'healthy'
    case 'warning':
    case 'degraded':
      return 'degraded'
    case 'error':
    case 'failed':
      return 'failed'
    case 'disabled':
      return 'paused'
    default:
      return 'neutral'
  }
}

const statusLabel = (status: string) => {
  const lowerStatus = status.toLowerCase()
  const normalized = lowerStatus === 'ok' ? 'healthy' : lowerStatus.replace(/_/g, ' ')
  return normalized.replace(/\b\w/g, letter => letter.toUpperCase())
}

export default function SourceHealth({ sources }: SourceHealthProps) {
  const counts = sources.reduce(
    (acc, source) => {
      const variant = statusVariant(source.status)
      acc[variant] += 1
      return acc
    },
    { healthy: 0, degraded: 0, failed: 0, paused: 0, neutral: 0 } as Record<BadgeVariant, number>,
  )

  if (sources.length === 0) {
    return <EmptyState title="No source health data yet" description="Connectors will appear here once the dashboard loads live health status." />
  }

  return (
    <div className="source-health">
      <div className="source-health__summary" aria-live="polite" aria-atomic="true">
        <StatusBadge variant="healthy">{counts.healthy} Healthy</StatusBadge>
        <StatusBadge variant="warning">{counts.degraded} Degraded</StatusBadge>
        <StatusBadge variant="failed">{counts.failed} Failed</StatusBadge>
      </div>
      <div className="source-health__grid" role="list">
        {sources.map(source => {
          const variant = statusVariant(source.status)
          return (
            <div key={source.connector} className="source-health__item" role="listitem">
              <div>
                <p className="source-health__title">{formatSourceName(source.name || source.connector)}</p>
                {source.last_error && (
                  <div className="source-health__meta">
                    {source.last_error}
                  </div>
                )}
              </div>
              <StatusBadge variant={variant === 'neutral' ? 'neutral' : variant}>{statusLabel(source.status)}</StatusBadge>
            </div>
          )
        })}
      </div>
    </div>
  )
}
