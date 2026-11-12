/**
 * The live app must show what is happening when planning or a change goes wrong.
 * Each test was a real problem in live mode (2026-11-12):
 * - "Build my plan" stayed clickable for the whole plan, so a double click planned twice;
 * - a failed plan request or a failed Swap / Undo / Adjust trip showed nothing;
 * - error text was raw JSON ({"detail": ...}), or the literal key "errors.unknown".
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/svelte'
import { api, errorMessage, type TripFormInput } from '../api/client'
import { store } from '../state/store.svelte'
import type { RunStatus } from '../types'
import InfeasibleNotice from '../components/InfeasibleNotice.svelte'

const input: TripFormInput = {
  destination: 'Seattle',
  start_date: '2026-11-18',
  end_date: '2026-11-19',
  budget: 500,
  budget_strictness: 'strict',
  mode: 'walking',
  pace: 'moderate',
  max_travel_min: 30,
  interests: ['coffee'],
  avoid: [],
  tourist_local_ratio: 50,
  free_text: '',
  touched: [],
}

const CHANGE_FAILED = "We couldn't apply that change. Your plan is unchanged."

function failedChangeRun(runId: string): RunStatus {
  return {
    run_id: runId,
    trip_id: 't',
    status: 'failed',
    phase: 'adapt',
    step: 'failed',
    step_index: 5,
    step_count: 5,
    terminal: 'ERROR',
    message: CHANGE_FAILED,
    started_at: '2026-11-12T00:00:00Z',
  }
}

async function plannedTrip() {
  const trip = await store.createTrip(input)
  await store.startPlanning(trip.id)
  expect(store.route.name).toBe('itinerary')
  return trip
}

beforeEach(() => {
  store.reset()
  window.history.replaceState(null, '', '/')
})

afterEach(() => {
  vi.restoreAllMocks()
})

// --- readable error messages -------------------------------------------------------------

describe('errorMessage', () => {
  it('uses the backend sentence instead of raw JSON', () => {
    expect(errorMessage(409, '{"detail":"A change is already being applied"}')).toBe(
      'A change is already being applied',
    )
  })

  it('uses the first problem of a rejected form value', () => {
    const body = '{"detail":[{"msg":"Value error, Trip dates must use YYYY-MM-DD format"}]}'
    expect(errorMessage(422, body)).toBe('Trip dates must use YYYY-MM-DD format')
  })

  it('gives the copy-guide text for a server crash or an unreadable answer', () => {
    expect(errorMessage(500, 'Internal Server Error')).toBe('errors.unknown')
    expect(errorMessage(404, '<html>not found</html>')).toBe('errors.unknown')
  })
})

// --- Build my plan -----------------------------------------------------------------------

describe('Build my plan', () => {
  it('plans once when clicked twice while the first plan is still running', async () => {
    const trip = await store.createTrip(input)
    const realPlan = api.plan.bind(api)
    const plan = vi.spyOn(api, 'plan').mockImplementation(async (tripId) => {
      await new Promise((resolve) => setTimeout(resolve, 20)) // live mode: the request is slow
      return realPlan(tripId)
    })

    const first = store.startPlanning(trip.id)
    expect(store.planning).toBe(true)
    const second = store.startPlanning(trip.id)
    await Promise.all([first, second])

    expect(plan).toHaveBeenCalledTimes(1)
    expect(store.planning).toBe(false)
    expect(store.route.name).toBe('itinerary')
  })

  it('keeps the error to show with Try again when the plan request fails', async () => {
    const trip = await store.createTrip(input)
    vi.spyOn(api, 'plan').mockRejectedValue(new Error('errors.unknown'))

    await store.startPlanning(trip.id)

    expect(store.error).toBe('errors.unknown')
    expect(store.planning).toBe(false) // so Try again is possible
  })
})

// --- changes to the plan -----------------------------------------------------------------

describe('a change that fails', () => {
  it('shows why a Swap was refused instead of failing silently', async () => {
    const trip = await plannedTrip()
    vi.spyOn(api, 'swapBackup').mockRejectedValue(new Error('A change is already being applied'))

    await expect(store.swap(trip.id, 'a1', 'b1')).resolves.toBeUndefined()

    expect(store.actionError).toBe('A change is already being applied')
    expect(store.busy).toBe(false)
  })

  it('says the plan is unchanged when the server cannot be reached', async () => {
    const trip = await plannedTrip()
    vi.spyOn(api, 'swapBackup').mockRejectedValue(new Error('errors.unknown')) // offline

    await store.swap(trip.id, 'a1', 'b1')

    expect(store.actionError).toBe('errors.changeFailed') // not the "while planning" text
  })

  it('shows the message of a change run that failed on the server', async () => {
    const trip = await plannedTrip()
    vi.spyOn(api, 'swapBackup').mockResolvedValue({ run_id: 'r-failed' })
    vi.spyOn(api, 'getRun').mockResolvedValue(failedChangeRun('r-failed'))

    await store.swap(trip.id, 'a1', 'b1')

    expect(store.actionError).toBe(CHANGE_FAILED)
  })

  it('does not bring back an older failure on the next action', async () => {
    const trip = await plannedTrip()
    vi.spyOn(api, 'swapBackup').mockResolvedValue({ run_id: 'r-failed' })
    vi.spyOn(api, 'getRun').mockResolvedValue(failedChangeRun('r-failed'))
    await store.swap(trip.id, 'a1', 'b1')
    store.clearActionError()

    // Next: a change that only needs one more detail (no new run).
    vi.spyOn(api, 'submitChange').mockResolvedValue({
      run_id: '',
      change: { payload: { question: 'How many minutes late are you?' } } as never,
    })
    await store.submitTypedChange({ type: 'time' })

    expect(store.actionError).toBeNull()
    expect(store.clarifyQuestion).toBe('How many minutes late are you?')
  })
})

// --- the notice --------------------------------------------------------------------------

describe('InfeasibleNotice', () => {
  it('says planning failed, translates the message and offers Try again', async () => {
    const onretry = vi.fn()
    render(InfeasibleNotice, {
      report: { blocking_rule: 'error', explanation: 'errors.unknown', suggestions: [] },
      onretry,
    })

    expect(screen.getByRole('heading')).toHaveTextContent("We couldn't finish planning.")
    expect(screen.getByText(/Something went wrong while planning/)).toBeInTheDocument()
    await fireEvent.click(screen.getByRole('button', { name: 'Try again' }))
    expect(onretry).toHaveBeenCalledTimes(1)
  })

  it('keeps the "couldn\'t fit" title and no Try again for a trip that cannot fit', () => {
    render(InfeasibleNotice, {
      report: { blocking_rule: 'budget', explanation: 'Too expensive.', suggestions: [] },
    })

    expect(screen.getByRole('heading')).toHaveTextContent("We couldn't fit this trip")
    expect(screen.queryByRole('button', { name: 'Try again' })).toBeNull()
  })
})
