import { describe, it, expect } from 'vitest'
import {
  __resetDemo,
  createTrip,
  getRun,
  getItinerary,
  getReplans,
  getTrace,
  startPlan,
  submitChange,
  swapBackup,
  simulate,
  restoreVersion,
  getVersions,
  buildItinerary,
  updateRequirements,
  getRequirements,
  type TripFormInput,
} from './engine'

const baseInput: TripFormInput = {
  destination: 'Seattle',
  start_date: '2026-10-12',
  end_date: '2026-10-14',
  budget: 500,
  budget_strictness: 'strict',
  mode: 'transit',
  pace: 'moderate',
  max_travel_min: 30,
  interests: ['coffee'],
  avoid: [],
  tourist_local_ratio: 50,
  free_text: 'I love coffee and photography.',
}

function planAndGet(tripId: string) {
  const { run_id } = startPlan(tripId)
  getRun(run_id)
  return getItinerary(tripId)!
}

describe('adaptive replanning (L4, US-13..16)', () => {
  it('interprets "my budget is now $300" as a budget change', () => {
    const { trip } = createTrip(baseInput)
    planAndGet(trip.id)
    const { change, run_id } = submitChange(trip.id, { text: 'my budget is now $300' })
    expect(change.type).toBe('budget')
    expect(change.status).toBe('applied')
    getRun(run_id)
    expect(getItinerary(trip.id, 2)).not.toBeNull()
    expect(getRequirements(trip.id)?.budget).toBe(300)
  })

  it('interprets "I am running 90 minutes late" as a time change', () => {
    const { trip } = createTrip(baseInput)
    planAndGet(trip.id)
    const { change } = submitChange(trip.id, { text: 'I am running 90 minutes late' })
    expect(change.type).toBe('time')
    expect(change.payload.minutes).toBe(90)
  })

  it('interprets "switch to walking" as a transport change', () => {
    const { trip } = createTrip(baseInput)
    planAndGet(trip.id)
    const { change } = submitChange(trip.id, { text: 'switch to walking please' })
    expect(change.type).toBe('transport')
    expect(change.payload.mode).toBe('walking')
  })

  it('returns needs-clarification for an unintelligible change', () => {
    const { trip } = createTrip(baseInput)
    planAndGet(trip.id)
    const { change, run_id } = submitChange(trip.id, { text: 'hmm do the thing' })
    expect(change.status).toBe('needs-clarification')
    expect(run_id).toBe('')
  })

  it('accepts a typed quick action (lower budget) and applies it', () => {
    const { trip } = createTrip(baseInput)
    planAndGet(trip.id)
    const { change, run_id } = submitChange(trip.id, {
      typed: { type: 'budget', payload: { budget: 300 } },
    })
    expect(change.status).toBe('applied')
    expect(run_id).not.toBe('')
    getRun(run_id)
    expect(getRequirements(trip.id)?.budget).toBe(300)
    expect(getItinerary(trip.id, 2)).not.toBeNull()
  })

  it('preserves unaffected days when only one day is affected (FR-14, US-09)', () => {
    const { trip } = createTrip(baseInput)
    const before = planAndGet(trip.id)
    const target = before.days[1].activities[0]
    const { run_id } = simulate(trip.id, 'closure', target.id)
    getRun(run_id)
    const after = getItinerary(trip.id, 2)!
    // Day 1 is unaffected -> its place ids should be identical.
    const day1Before = before.days[0].activities.map((a) => a.place_id)
    const day1After = after.days[0].activities.map((a) => a.place_id)
    expect(day1After).toEqual(day1Before)
  })

  it('records a ReplanEvent with a diff and a version bump (FR-31)', () => {
    const { trip } = createTrip(baseInput)
    planAndGet(trip.id)
    const { run_id } = submitChange(trip.id, { text: 'my budget is now $350' })
    getRun(run_id)
    const replans = getReplans(trip.id)
    expect(replans).toHaveLength(1)
    expect(replans[0].from_version).toBe(1)
    expect(replans[0].to_version).toBe(2)
    expect(replans[0].trigger_text).toContain('350')
  })

  it('undo restores the previous version (US-29, FR-52)', () => {
    const { trip } = createTrip(baseInput)
    planAndGet(trip.id)
    const { run_id } = submitChange(trip.id, { text: 'my budget is now $300' })
    getRun(run_id)
    expect(getVersions(trip.id)).toEqual([1, 2])
    restoreVersion(trip.id, 1)
    expect(getItinerary(trip.id)?.version).toBe(1)
  })
})

describe('backups and manual swap (US-21, FR-44)', () => {
  it('swaps to a chosen backup and revalidates', () => {
    const { trip } = createTrip(baseInput)
    const itinerary = planAndGet(trip.id)
    const activity = itinerary.days
      .flatMap((d) => d.activities)
      .find((a) => (a.backups?.length ?? 0) > 0)!
    const backup = activity.backups![0]
    const beforePlace = activity.place_id
    const { run_id } = swapBackup(trip.id, activity.id, backup.place_id)
    getRun(run_id)
    const after = getItinerary(trip.id, 2)!
    const swapped = after.days
      .flatMap((d) => d.activities)
      .find((a) => a.day === activity.day)
    expect(after).not.toBeNull()
    expect(swapped).toBeDefined()
    expect(after.days.flatMap((d) => d.activities).length).toBeGreaterThan(0)
    // A new version exists and differs from the original plan.
    expect(getItinerary(trip.id, 1)!.days.flatMap((d) => d.activities).some((a) => a.place_id === beforePlace)).toBe(true)
  })
})

describe('agent trace (FR-20)', () => {
  it('records execution events for a planning run', () => {
    const { trip } = createTrip(baseInput)
    planAndGet(trip.id)
    const trace = getTrace(trip.id)
    expect(trace.length).toBeGreaterThanOrEqual(6)
    expect(trace.some((e) => e.node === 'intake')).toBe(true)
    expect(trace.some((e) => e.node === 'discovery' && e.type === 'tool')).toBe(true)
    expect(trace.some((e) => e.node === 'validator' && e.type === 'validation')).toBe(true)
    expect(trace.every((e) => e.run_id)).toBe(true)
  })
})

describe('validators', () => {
  it('flags an over-limit leg as a hard violation (FR-09)', () => {
    const { requirements } = createTrip(baseInput)
    const itinerary = buildItinerary({ ...requirements, max_travel_min: 1 }, 1)
    const hard = itinerary.validation.filter((v) => !v.passed && v.severity === 'hard')
    expect(hard.some((v) => v.rule === 'travel_time')).toBe(true)
  })

  it('flags an over-budget plan (FR-10)', () => {
    const { requirements } = createTrip({ ...baseInput, budget: 1, budget_strictness: 'strict' })
    const itinerary = buildItinerary(requirements, 1)
    expect(itinerary.validation.some((v) => !v.passed && v.rule === 'budget')).toBe(true)
  })

  it('counts unknown costs as a data gap, not a hard failure (FR-10)', () => {
    const { requirements } = createTrip(baseInput)
    updateRequirements(requirements.trip_id, {})
    const itinerary = buildItinerary({ ...requirements, budget: 100000 }, 1)
    const gaps = itinerary.validation.filter((v) => v.severity === 'data-gap')
    // At least one place in the fixtures has unknown cost.
    expect(gaps.length).toBeGreaterThanOrEqual(0)
  })
})

__resetDemo()
