import { describe, it, expect, vi, afterEach } from 'vitest'
import { checkHealth } from '../api/client'

describe('backend health probe (repo contract GET /api/health)', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('returns the parsed health payload when the backend is up', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ status: 'ok', demo_mode: true }),
      }),
    )
    const health = await checkHealth()
    expect(fetch).toHaveBeenCalledWith('/api/health')
    expect(health).toEqual({ status: 'ok', demo_mode: true })
  })

  it('returns null when the backend is unreachable', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('down')))
    expect(await checkHealth()).toBeNull()
  })

  it('returns null on a non-OK response', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false }))
    expect(await checkHealth()).toBeNull()
  })
})
