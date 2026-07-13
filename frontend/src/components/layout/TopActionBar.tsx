import type { ReactNode } from 'react'

interface TopActionBarProps {
  eyebrow?: string
  title: string
  description?: string
  actions?: ReactNode
}

export default function TopActionBar({ eyebrow, title, description, actions }: TopActionBarProps) {
  return (
    <div className="app-shell__topbar">
      <div className="page-title">
        {eyebrow ? <div className="page-title__eyebrow">{eyebrow}</div> : null}
        <h1 id="page-title" tabIndex={-1}>{title}</h1>
        {description ? <p className="page-title__description">{description}</p> : null}
      </div>
      {actions ? <div className="page-actions">{actions}</div> : null}
    </div>
  )
}
