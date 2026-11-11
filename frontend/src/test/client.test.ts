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
