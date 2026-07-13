import { NavLink } from 'react-router-dom'

const sections = [
  { to: '/', label: 'Watch queue', metric: '' },
  { to: '/events', label: 'Event stream', metric: '' },
  { to: '/connectors', label: 'Connectors', metric: '' },
]

const ops = [
  { to: '/notifications', label: 'Notifications' },
  { to: '/runs', label: 'Runs & history' },
  { to: '/exports', label: 'Exports' },
  { to: '/settings', label: 'Settings' },
]

export default function SidebarNav() {
  return (
    <div>
      <div className="app-shell__brand">
        <div className="app-shell__brand-mark">P</div>
        <div className="app-shell__brand-copy">
          <div className="app-shell__brand-name">PriceRecon</div>
        </div>
      </div>

      <nav className="sidebar-nav" aria-label="Primary">
        {sections.map(item => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === '/'}
            className={({ isActive }: { isActive: boolean }) => `sidebar-nav__link${isActive ? ' is-active' : ''}`}
          >
            <span className="sidebar-nav__link-label">
              <span className="sidebar-nav__dot" />
              {item.label}
            </span>
            <span className="sidebar-nav__metric">{item.metric}</span>
          </NavLink>
        ))}

        <div className="sidebar-nav__section">Operations</div>
        {ops.map(item => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }: { isActive: boolean }) => `sidebar-nav__link${isActive ? ' is-active' : ''}`}
          >
            <span className="sidebar-nav__link-label">{item.label}</span>
          </NavLink>
        ))}
      </nav>


    </div>
  )
}
