import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/svelte'
import ChangeSummaryPanel from '../components/ChangeSummaryPanel.svelte'
import InfeasibleNotice from '../components/InfeasibleNotice.svelte'
import { buildItinerary } from '../api/mock/engine'
import type { Itinerary, ReplanEvent, TripRequirements } from '../types'

const requirements: TripRequirements = {
  trip_id: 'trip_1',
  version: 1,
  destination: 'Seattle',
  start_date: '2026-10-12',
  end_date: '2026-10-13',
  budget: 400,
  budget_strictness: 'strict',
  mode: 'transit',
  pace: 'moderate',
  interests: ['coffee'],
  avoid: [],
  tourist_local_ratio: 50,
  max_travel_min: 30,
  daily_start: '09:00',
  daily_end: '20:00',
  dietary: [],
  accessibility: [],
  free_text: '',
  provenance: {},
}

function seededItinerary(): Itinerary {
  const plan = buildItinerary(requirements, 1)
  // Mark states to exercise each change group.
  plan.days[0].activities[0].change_type = 'replaced'
  plan.days[0].activities[1].change_type = 'moved'
  if (plan.days[0].activities[2]) plan.days[0].activities[2].change_type = 'added'
  return plan
}

const replan: ReplanEvent = {
  id: 'replan_1',
  trip_id: 'trip_1',
  from_version: 1,
  to_version: 2,
  trigger_id: 'chg_1',
  diff: { changed: [], moved: [], preserved: [], added: [], removed: [] },
  reasons: {},
  iterations: 1,
  trigger_text: 'your budget is now $300',
}

describe('ChangeSummaryPanel', () => {
  it('states the trigger in the user\u2019s words and groups changes', () => {
    render(ChangeSummaryPanel, {
      replan,
      itinerary: seededItinerary(),
      onundo: vi.fn(),
      onclose: vi.fn(),
    })
    expect(screen.getByText(/Because your budget is now \$300/)).toBeInTheDocument()
    expect(screen.getByText('Replaced')).toBeInTheDocument()
    expect(screen.getByText('Moved')).toBeInTheDocument()
    expect(screen.getByText('Added')).toBeInTheDocument()
  })

  it('offers Undo and Looks good after a replan', async () => {
    const onundo = vi.fn()
    render(ChangeSummaryPanel, {
      replan,
      itinerary: seededItinerary(),
      onundo,
      onclose: vi.fn(),
    })
    await fireEvent.click(screen.getByRole('button', { name: /Undo changes/ }))
    expect(onundo).toHaveBeenCalled()
    expect(screen.getByRole('button', { name: /Looks good/ })).toBeInTheDocument()
  })

  it('uses approval wording in approval mode (FR-53)', () => {
    render(ChangeSummaryPanel, {
      replan,
      itinerary: seededItinerary(),
      approvalMode: true,
      onundo: vi.fn(),
      onclose: vi.fn(),
    })
    expect(screen.getByText('This is a bigger change')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Apply changes/ })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Keep my plan/ })).toBeInTheDocument()
  })
})

describe('InfeasibleNotice', () => {
  it('explains the blocking constraint and offers relaxations', () => {
    render(InfeasibleNotice, {
      report: {
        blocking_rule: 'budget',
        explanation: 'infeasible.noPlan',
        suggestions: [
          { label: 'infeasible.allowFreeOnly', change: {} },
          { label: 'infeasible.changeBudget', change: {} },
        ],
      },
      city: 'Seattle',
      budget: 150,
    })
    expect(screen.getByRole('heading', { name: /We couldn't fit this trip/ })).toBeInTheDocument()
    expect(screen.getByText(/Seattle/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Allow free-only days/ })).toBeInTheDocument()
  })
})
