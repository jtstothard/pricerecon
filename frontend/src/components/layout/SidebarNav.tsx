import { NavLink } from 'react-router-dom'
import { useData } from '../../context/DataContext'

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

export default function SidebarNav() {
  const { metrics, loading } = useData()

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
            <span className="sidebar-nav__metric">
              {loading ? '—' : String(metrics[item.metricKey])}
            </span>
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
