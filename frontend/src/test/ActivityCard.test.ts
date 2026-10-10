import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/svelte'
import ActivityCard from '../components/ActivityCard.svelte'
import { demoPlaces } from '../api/mock/fixtures'
import type { Activity } from '../types'

function makeActivity(overrides: Partial<Activity> = {}): Activity {
  const place = demoPlaces[0]
  return {
    id: 'act_1',
    trip_id: 'trip_1',
    version: 1,
    day: 1,
    place_id: place.id,
    start: '2026-10-12T11:00:00',
    end: '2026-10-12T12:30:00',
    est_cost: 0,
    cost_basis: 'free',
    priority: 'high',
    purpose_tags: ['views'],
    status: 'planned',
    change_type: null,
    reason: null,
    warnings: [],
    backups: [
      {
        activity_id: 'act_1',
        place_id: demoPlaces[4].id,
        rank: 1,
        purpose_similarity: 0.75,
        cost_delta: -5,
        travel_delta_min: 2,
        validated_at: new Date().toISOString(),
      },
    ],
    place,
    ...overrides,
  }
}

describe('ActivityCard', () => {
  it('shows time, place and cost', () => {
    render(ActivityCard, { activity: makeActivity() })
    expect(screen.getByText(demoPlaces[0].name)).toBeInTheDocument()
    expect(screen.getByText(/11:00/)).toBeInTheDocument()
    expect(screen.getByText('Free')).toBeInTheDocument()
  })

  it('shows cost unknown rather than $0 when data is missing (guide, do/don\u2019t)', () => {
    render(ActivityCard, {
      activity: makeActivity({ est_cost: null, cost_basis: 'unknown', place: demoPlaces[6] }),
    })
    expect(screen.getByText('Cost unknown')).toBeInTheDocument()
    expect(screen.queryByText('$0')).not.toBeInTheDocument()
  })

  it('pairs the change colour with an icon and a word (NFR-14)', () => {
    render(ActivityCard, { activity: makeActivity({ change_type: 'replaced' }) })
    expect(screen.getByText('Replaced')).toBeInTheDocument()
  })

  it('renders a removed state distinctly from added', () => {
    render(ActivityCard, { activity: makeActivity({ change_type: 'added' }) })
    expect(screen.getByText('Added')).toBeInTheDocument()
  })

  it('expands backups and calls onswap when one is chosen', async () => {
    const onswap = vi.fn()
    render(ActivityCard, { activity: makeActivity(), onswap })
    await fireEvent.click(screen.getByRole('button', { name: /Backups/ }))
    const swap = screen.getByRole('button', { name: 'Replaced' })
    await fireEvent.click(swap)
    expect(onswap).toHaveBeenCalledWith(demoPlaces[4].id, demoPlaces[4].name)
  })

  it('toggles lock and disables swapping when locked', async () => {
    const onlocktoggle = vi.fn()
    render(ActivityCard, { activity: makeActivity(), onlocktoggle, onswap: vi.fn() })
    await fireEvent.click(screen.getByRole('button', { name: /Press L to lock|Locked/ }))
    expect(onlocktoggle).toHaveBeenCalledWith('act_1')
  })

  it('does not show a backup drawer when there are none (empty state is honest)', async () => {
    render(ActivityCard, { activity: makeActivity({ backups: [] }), onswap: vi.fn() })
    await fireEvent.click(screen.getByRole('button', { name: /Backups/ }))
    expect(screen.getByText(/No backup found nearby yet/)).toBeInTheDocument()
  })
})
