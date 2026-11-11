import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/svelte'
import BackupDrawer from '../components/BackupDrawer.svelte'
import { demoPlaces } from '../api/mock/fixtures'
import type { Activity, Place } from '../types'

// A place that exists only in the live API answer, not in the demo fixtures.
const livePlace: Place = {
  ...demoPlaces[1],
  id: 'geoapify:abc123',
  name: 'Live Corner Cafe',
  hours: null,
  est_cost_low: null,
  est_cost_high: null,
  cost_basis: 'unknown',
}

function makeActivity(): Activity {
  const place = demoPlaces[0]
  return {
    id: 'act_1',
    trip_id: 'trip_1',
    version: 1,
    day: 1,
    place_id: place.id,
    start: '2026-11-12T10:00:00-08:00',
    end: '2026-11-12T11:00:00-08:00',
    est_cost: 10,
    cost_basis: 'known',
    priority: 'medium',
    purpose_tags: ['food'],
    status: 'planned',
    change_type: null,
    reason: null,
    warnings: [],
    backups: [
      {
        activity_id: 'act_1',
        place_id: livePlace.id,
        rank: 1,
        purpose_similarity: 1,
        cost_delta: null,
        travel_delta_min: 4,
        validated_at: '2026-11-11T10:00:00Z',
        place: livePlace,
        unknown: ['hours', 'price'],
      },
    ],
    place,
  }
}

describe('BackupDrawer with live backups', () => {
  it('shows the backup place name, unknown hours and unknown cost', async () => {
    render(BackupDrawer, { activity: makeActivity(), onswap: vi.fn() })
    await fireEvent.click(screen.getByRole('button', { expanded: false }))

    expect(screen.getByText('Live Corner Cafe')).toBeInTheDocument()
    expect(screen.getByText('Hours not listed. Check before you go.')).toBeInTheDocument()
    expect(screen.getByText('Cost unknown')).toBeInTheDocument()
    expect(screen.queryByText('geoapify:abc123')).not.toBeInTheDocument()
  })
})
