import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/svelte'
import ChangeSummaryPanel from '../components/ChangeSummaryPanel.svelte'
import { demoPlaces } from '../api/mock/fixtures'
import type { Activity, Itinerary, ReplanEvent } from '../types'

function act(id: string, placeIndex: number, extra: Partial<Activity> = {}): Activity {
  const place = demoPlaces[placeIndex]
  return {
    id, trip_id: 't', version: 1, day: 1, place_id: place.id, place,
    start: '2026-11-20T10:00:00-08:00', end: '2026-11-20T11:00:00-08:00',
    est_cost: 0, cost_basis: 'free', priority: 'medium', purpose_tags: [], status: 'planned',
    change_type: null, reason: null, warnings: [], backups: [], ...extra,
  }
}

function itinerary(version: number, activities: Activity[]): Itinerary {
  return {
    trip_id: 't', version, created_at: '', score: 1, validation: [],
    days: [{ day: 1, date: '2026-11-20', activities, legs: [], warnings: [] }],
  }
}

describe('ChangeSummaryPanel', () => {
  it('does not also list a replaced activity as removed', () => {
    const previous = itinerary(1, [act('a', 0), act('b', 1)])
    const current = itinerary(2, [act('a', 2, { change_type: 'replaced' }), act('b', 1)])
    const replan: ReplanEvent = {
      id: 'r', trip_id: 't', from_version: 1, to_version: 2, trigger_id: 'c',
      diff: { changed: ['a'], moved: [], preserved: ['b'], added: [], removed: [] },
      reasons: { a: 'It is closed today.' }, iterations: 1, trigger_text: 'it closed',
    }

    render(ChangeSummaryPanel, { replan, itinerary: current, previous, onundo: vi.fn(), onclose: vi.fn() })

    expect(screen.getByText(/Because it closed, we changed 1 activity and kept 1/)).toBeInTheDocument()
    expect(screen.queryByText('Removed')).not.toBeInTheDocument()
  })
})
