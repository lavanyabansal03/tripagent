import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'

type LogEntry = { step: string; message: string; attempt?: number }
type TripRun = {
  thread_id: string
  status: 'running' | 'awaiting_input' | 'completed' | 'failed'
  question: { prompt: string; fields: string[]; attempt: number; max_attempts: number } | null
  trip: { start_date?: string; end_date?: string } | null
  places: { name: string; category: string }[]
  logs: LogEntry[]
  explanation: string | null
}

function App() {
  const [status, setStatus] = useState('checking...')
  const [destination, setDestination] = useState('')
  const [interests, setInterests] = useState('')
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')
  const [run, setRun] = useState<TripRun | null>(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  // Ask the backend if it's alive. Vite proxies /api to http://localhost:8000.
  useEffect(() => {
    fetch('/api/health')
      .then((res) => (res.ok ? res.json() : Promise.reject()))
      .then(() => setStatus('connected'))
      .catch(() => setStatus('not reachable'))
  }, [])

  async function submitTrip(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError('')
    setBusy(true)
    try {
      const response = await fetch('/api/trips/plan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          destination,
          interests: interests.split(',').map((item) => item.trim()).filter(Boolean),
          ...(startDate ? { start_date: startDate } : {}),
          ...(endDate ? { end_date: endDate } : {}),
        }),
      })
      if (!response.ok) throw new Error((await response.json()).detail ?? 'Could not plan this trip')
      setRun(await response.json())
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not reach the backend')
    } finally {
      setBusy(false)
    }
  }

  async function submitAnswer(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!run) return
    setError('')
    setBusy(true)
    try {
      const response = await fetch(`/api/trips/${run.thread_id}/answer`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...(startDate ? { start_date: startDate } : {}),
          ...(endDate ? { end_date: endDate } : {}),
        }),
      })
      if (!response.ok) throw new Error((await response.json()).detail ?? 'Could not send your answer')
      setRun(await response.json())
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not reach the backend')
    } finally {
      setBusy(false)
    }
  }

  return (
    <main style={{ maxWidth: 760, margin: '48px auto', padding: '0 24px', fontFamily: 'system-ui' }}>
      <header style={{ marginBottom: 32 }}>
        <p style={{ color: '#64748b', marginBottom: 4 }}>A tiny LangGraph demo</p>
        <h1 style={{ margin: '0 0 8px' }}>TripAgent</h1>
        <p style={{ color: '#475569', margin: 0 }}>Backend: {status}</p>
      </header>

      <section style={{ padding: 24, border: '1px solid #cbd5e1', borderRadius: 12 }}>
        <h2 style={{ marginTop: 0 }}>Plan a trip</h2>
        <form onSubmit={submitTrip} style={{ display: 'grid', gap: 14 }}>
          <label>
            Destination
            <input required value={destination} onChange={(event) => setDestination(event.target.value)}
              placeholder="Lisbon" style={inputStyle} />
          </label>
          <label>
            Interests (comma-separated)
            <input value={interests} onChange={(event) => setInterests(event.target.value)}
              placeholder="food, museums, walking" style={inputStyle} />
          </label>
          <div style={{ display: 'flex', gap: 12 }}>
            <label style={{ flex: 1 }}>
              Start date
              <input type="date" value={startDate} onChange={(event) => setStartDate(event.target.value)}
                style={inputStyle} />
            </label>
            <label style={{ flex: 1 }}>
              End date
              <input type="date" value={endDate} onChange={(event) => setEndDate(event.target.value)}
                style={inputStyle} />
            </label>
          </div>
          <button disabled={busy} style={buttonStyle}>{busy ? 'Working…' : 'Start planning'}</button>
        </form>
      </section>

      {error && <p role="alert" style={{ color: '#b91c1c' }}>{error}</p>}

      {run && <section style={{ marginTop: 24, display: 'grid', gap: 16 }}>
        <div style={{ padding: 20, background: '#f1f5f9', borderRadius: 12 }}>
          <h2 style={{ margin: '0 0 8px' }}>Status: {run.status.replace('_', ' ')}</h2>
          {run.question && <>
            <p>{run.question.prompt} (question {run.question.attempt} of {run.question.max_attempts})</p>
            <form onSubmit={submitAnswer} style={{ display: 'grid', gap: 12 }}>
              {run.question.fields.includes('start_date') && <label>
                Start date
                <input type="date" value={startDate} onChange={(event) => setStartDate(event.target.value)}
                  style={inputStyle} />
              </label>}
              {run.question.fields.includes('end_date') && <label>
                End date
                <input type="date" value={endDate} onChange={(event) => setEndDate(event.target.value)}
                  style={inputStyle} />
              </label>}
              <button disabled={busy} style={buttonStyle}>{busy ? 'Continuing…' : 'Answer and continue'}</button>
            </form>
          </>}
          {run.explanation && <p>{run.explanation}</p>}
        </div>

        {run.places.length > 0 && <div>
          <h2>Sample places</h2>
          <ul>{run.places.map((place) => <li key={place.name}>{place.name} — {place.category}</li>)}</ul>
        </div>}

        <div>
          <h2>Workflow log</h2>
          <ol>{run.logs.map((entry, index) => <li key={`${entry.step}-${index}`}>
            <strong>{entry.step}</strong>: {entry.message}
            {entry.attempt ? ` (try ${entry.attempt})` : ''}
          </li>)}</ol>
        </div>
      </section>}
    </main>
  )
}

const inputStyle = { display: 'block', boxSizing: 'border-box' as const, width: '100%', marginTop: 6, padding: 10 }
const buttonStyle = { justifySelf: 'start', padding: '10px 16px', cursor: 'pointer' }

export default App
