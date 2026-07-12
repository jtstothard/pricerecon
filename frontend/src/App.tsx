import { BrowserRouter, Routes, Route } from 'react-router-dom'
import AppShell from './components/layout/AppShell'
import TopActionBar from './components/layout/TopActionBar'
import WatchList from './components/WatchList'
import WatchDetail from './components/WatchDetail'
import './App.css'

function App() {
  return (
    <BrowserRouter>
      <AppShell>
        <Routes>
          <Route
            path="/"
            element={(
              <>
                <TopActionBar
                  eyebrow="Operations control center"
                  title="Watch dashboard"
                  description="Scan priority watches, source posture, and the next action without digging through detail pages."
                  actions={(
                    <>
                      <button className="btn btn-secondary">Refresh</button>
                      <button className="btn btn-secondary">Export</button>
                      <button className="btn btn-primary">+ New watch</button>
                    </>
                  )}
                />
                <WatchList />
              </>
            )}
          />
          <Route
            path="/watch/:id"
            element={(
              <>
                <TopActionBar
                  eyebrow="Watch detail"
                  title="Watch overview"
                  description="Inspect current listings, price history, and event stream for a single watch."
                  actions={<button className="btn btn-primary">Check now</button>}
                />
                <WatchDetail />
              </>
            )}
          />
        </Routes>
      </AppShell>
    </BrowserRouter>
  )
}

export default App
