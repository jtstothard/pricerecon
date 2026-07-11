import { BrowserRouter, Routes, Route, Link } from 'react-router-dom'
import WatchList from './components/WatchList'
import WatchDetail from './components/WatchDetail'
import './App.css'

function App() {
  return (
    <BrowserRouter>
      <div className="app">
        <header className="app-header">
          <h1>PriceRecon Dashboard</h1>
          <nav>
            <Link to="/">Watches</Link>
          </nav>
        </header>
        <main className="app-main">
          <Routes>
            <Route path="/" element={<WatchList />} />
            <Route path="/watch/:id" element={<WatchDetail />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}

export default App