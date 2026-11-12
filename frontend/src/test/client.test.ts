import { describe, it, expect, vi, afterEach } from 'vitest'

// DEMO_MODE is read once when client.ts loads, so each test loads it fresh
// after setting the environment variable.
async function loadLiveClient() {
  vi.stubEnv('VITE_DEMO_MODE', 'false')
  vi.resetModules()
  return import('../api/client')
}

const form = {
  destination: 'Seattle',
  start_date: '2026-11-10',
  end_date: '2026-11-11',
  budget: 500,
  budget_strictness: 'strict' as const,
  mode: 'transit' as const,
  pace: 'moderate' as const,
  max_travel_min: 30,
  interests: [],
  avoid: [],
  tourist_local_ratio: 50,
  free_text: 'Museums, no more than 20 minutes between stops.',
  touched: ['destination'],
}

describe('live API client', () => {
  afterEach(() => {
    vi.unstubAllEnvs()
    vi.unstubAllGlobals()
  })

  it('sends the touched fields so the note can replace untouched defaults', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 201,
      json: async () => ({ trip: {}, requirements: {}, questions: [] }),
    })
    vi.stubGlobal('fetch', fetchMock)
    const { api } = await loadLiveClient()

    await api.createTrip(form)

    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toBe('/api/trips')
    expect(JSON.parse(init.body)).toEqual(form)
  })
})

describe('live API client changes', () => {
  afterEach(() => {
    vi.unstubAllEnvs()
    vi.unstubAllGlobals()
  })

  it('sends the day on screen with a change', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ run_id: 'r1', change: {} }),
    })
    vi.stubGlobal('fetch', fetchMock)
    const { api, CHANGES_AVAILABLE } = await loadLiveClient()

    await api.submitChange('t1', { text: "I'm 90 minutes late", day: 2 })

    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toBe('/api/trips/t1/changes')
    expect(JSON.parse(init.body)).toEqual({ text: "I'm 90 minutes late", day: 2 })
    expect(CHANGES_AVAILABLE).toBe(true)
  })
})
