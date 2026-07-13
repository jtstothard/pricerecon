import { useState } from 'react'
import { NavLink } from 'react-router-dom'
import { useData } from '../../context/DataContext'

interface MobileNavProps {
  isOpen: boolean
  onClose: () => void
}

function MobileNav({ isOpen, onClose }: MobileNavProps) {
  const { metrics, loading } = useData()

  const sections = [
    { to: '/', label: 'Watch queue', metricKey: 'totalWatches' as const },
    { to: '/events', label: 'Event stream', metricKey: 'totalEvents' as const },
    { to: '/connectors', label: 'Connectors', metricKey: 'healthySources' as const },
  ]

  const ops = [
    { to: '/notifications', label: 'Notifications' },
    { to: '/runs', label: 'Runs & history' },
    { to: '/exports', label: 'Exports' },
    { to: '/settings', label: 'Settings' },
  ]

  return (
    <>
      <div className={`mobile-nav-overlay${isOpen ? ' is-open' : ''}`} onClick={onClose} />
      <div className={`mobile-nav-panel${isOpen ? ' is-open' : ''}`}>
        <div className="mobile-nav-header">
          <div className="app-shell__brand">
            <div className="app-shell__brand-mark">P</div>
            <div className="app-shell__brand-copy">
              <div className="app-shell__brand-name">PriceRecon</div>
            </div>
          </div>
          <button
            className="mobile-nav-close"
            onClick={onClose}
            aria-label="Close menu"
          >
            ✕
          </button>
        </div>

        <nav className="sidebar-nav" aria-label="Primary">
          {sections.map(item => (
            <NavLink
              key={item.label}
              to={item.to}
              end={item.to === '/'}
              onClick={onClose}
              className={({ isActive }) => `sidebar-nav__link${isActive ? ' is-active' : ''}`}
            >
              <span className="sidebar-nav__link-label">
                <span className="sidebar-nav__dot" />
                {item.label}
              </span>
              <span className="sidebar-nav__metric">
                {loading ? '—' : String(metrics[item.metricKey])}
              </span>
            </NavLink>
          ))}

          <div className="sidebar-nav__section">Operations</div>
          {ops.map(item => (
            <NavLink
              key={item.label}
              to={item.to}
              onClick={onClose}
              className={({ isActive }) => `sidebar-nav__link${isActive ? ' is-active' : ''}`}
            >
              <span className="sidebar-nav__link-label">{item.label}</span>
            </NavLink>
          ))}
        </nav>
      </div>
    </>
  )
}

export default function MobileNavToggle() {
  const [isOpen, setIsOpen] = useState(false)

  return (
    <>
      <button
        className="mobile-nav-toggle"
        onClick={() => setIsOpen(true)}
        aria-label="Open menu"
        aria-expanded={isOpen}
      >
        <span className="mobile-nav-toggle__line" />
        <span className="mobile-nav-toggle__line" />
        <span className="mobile-nav-toggle__line" />
      </button>
      <MobileNav isOpen={isOpen} onClose={() => setIsOpen(false)} />
    </>
  )
}