import { useEffect, useState } from 'react'

function App() {
  const [status, setStatus] = useState('checking...')

  // Ask the backend if it's alive. Vite proxies /api to http://localhost:8000.
  useEffect(() => {
    fetch('/api/health')
      .then((res) => (res.ok ? res.json() : Promise.reject()))
      .then(() => setStatus('connected'))
      .catch(() => setStatus('not reachable'))
  }, [])

  return (
    <main>
      <h1>TripAgent</h1>
      <p>Backend: {status}</p>
    </main>
  )
}

export default App
