import type { ReactNode } from 'react'
import SidebarNav from './SidebarNav'
import MobileNavToggle from './MobileNav'

interface AppShellProps {
  children: ReactNode
}

export default function AppShell({ children }: AppShellProps) {
  return (
    <div className="app-shell">
      <a href="#page-title" className="skip-link">Skip to main content</a>
      <aside className="app-shell__sidebar">
        <SidebarNav />
      </aside>
      <main id="main-content" className="app-shell__main">
        <div className="app-shell__topbar">
          <MobileNavToggle />
        </div>
        <div className="page-content">{children}</div>
      </main>
    </div>
  )
}