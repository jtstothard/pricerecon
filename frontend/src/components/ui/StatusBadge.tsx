import type { ReactNode } from 'react'

type BadgeVariant =
  | 'healthy'
  | 'degraded'
  | 'failed'
  | 'active'
  | 'paused'
  | 'info'
  | 'warning'
  | 'neutral'
  | 'accent'

interface StatusBadgeProps {
  variant?: BadgeVariant
  children: ReactNode
}

export default function StatusBadge({ variant = 'neutral', children }: StatusBadgeProps) {
  return (
    <span className={`status-badge status-badge--${variant}`}>
      <span className="status-badge__dot" />
      {children}
    </span>
  )
}
