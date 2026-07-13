import { BrowserRouter, Routes, Route } from 'react-router-dom'
import AppShell from './components/layout/AppShell'
import WatchList from './components/WatchList'
import WatchDetail from './components/WatchDetail'
import Notifications from './pages/Notifications'
import Runs from './pages/Runs'
import Exports from './pages/Exports'
import Settings from './pages/Settings'
import Events from './pages/Events'
import Connectors from './pages/Connectors'
import './App.css'

function App() {
  return (
    <BrowserRouter>
      <AppShell>
        <Routes>
          <Route path="/" element={<WatchList />} />
          <Route
            path="/watch/:id"
            element={<WatchDetail />}
          />
          <Route path="/notifications" element={<Notifications />} />
          <Route path="/runs" element={<Runs />} />
          <Route path="/exports" element={<Exports />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="/events" element={<Events />} />
          <Route path="/connectors" element={<Connectors />} />
        </Routes>
      </AppShell>
    </BrowserRouter>
  )
}

export default App
