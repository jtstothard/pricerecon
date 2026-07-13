import '../styles/pages.css'
import { usePageTitle } from '../hooks/usePageTitle'

export default function Events() {
  usePageTitle('Events')
  return (
    <div className="page">
      <h1 id="page-title" tabIndex={-1}>Event Stream</h1>
      <p className="page-empty-state">
        No events recorded yet. Watch execution events and system notifications will appear here.
      </p>
    </div>
  )
}