import { useState } from 'react'
import { NavLink } from 'react-router-dom'

interface MobileNavProps {
  isOpen: boolean
  onClose: () => void
}

function MobileNav({ isOpen, onClose }: MobileNavProps) {
  if (!isOpen) return null

  const sections = [
    { to: '/', label: 'Watch queue', metric: '38 watches' },
    { to: '/events', label: 'Event stream', metric: '12 recent' },
    { to: '/connectors', label: 'Connectors', metric: '9 online' },
  ]

  const ops = [
    'Notifications',
    'Runs & history',
    'Exports',
    'Settings',
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
              <span className="sidebar-nav__metric">{item.metric}</span>
            </NavLink>
          ))}

          <div className="sidebar-nav__section">Operations</div>
          {ops.map(label => (
            <a key={label} href="/" onClick={onClose} className="sidebar-nav__link">
              <span className="sidebar-nav__link-label">{label}</span>
            </a>
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