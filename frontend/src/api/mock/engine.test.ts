import { describe, it, expect } from 'vitest'
import { __setStepMs, __resetDemo, createTrip, getTrip, startPlan, getRun, getItinerary, type TripFormInput } from './engine'

const baseInput: TripFormInput = {
  destination: 'Seattle',
  start_date: '2026-10-12',
  end_date: '2026-10-14',
  budget: 500,
  budget_strictness: 'strict',
  mode: 'transit',
  pace: 'moderate',
  max_travel_min: 30,
  interests: [],
  avoid: [],
  tourist_local_ratio: 50,
  free_text: 'First time in Seattle. I love coffee, bookstores and photography, want places locals enjoy.',
}

function plan(input: Partial<TripFormInput> = {}) {
  const { trip } = createTrip({ ...baseInput, ...input })
  const { run_id } = startPlan(trip.id)
  getRun(run_id)
  return { tripId: trip.id, itinerary: getItinerary(trip.id) }
}

describe('intake (US-17, FR-33)', () => {
  it('extracts interests from free text and labels provenance', () => {
    const { requirements } = createTrip({ ...baseInput })
    expect(requirements.interests).toContain('coffee')
    expect(requirements.interests).toContain('bookstores')
    expect(requirements.provenance['interests.coffee']).toBe('explicit')
    expect(requirements.provenance.budget).toBe('explicit')
  })

  it('infers the tourist/local ratio from "places locals enjoy"', () => {
    const { requirements } = createTrip({ ...baseInput })
    expect(requirements.tourist_local_ratio).toBe(80)
    expect(requirements.provenance.tourist_local_ratio).toBe('inferred')
  })

  it('asks a clarification question when the form contradicts the text (FR-34)', () => {
    const { questions } = createTrip({
      ...baseInput,
      mode: 'driving',
      free_text: 'I will not have a car on this trip.',
    })
    expect(questions).toHaveLength(1)
    expect(questions[0].field).toBe('mode')
    expect(questions[0].text).toBe('contradiction')
  })
})

describe('initial plan (US-03, G-01)', () => {
  it('produces a multi-day itinerary with activities and legs', () => {
    const { itinerary } = plan()
    expect(itinerary).not.toBeNull()
    expect(itinerary!.version).toBe(1)
    expect(itinerary!.days).toHaveLength(3)
    expect(itinerary!.days[0].activities.length).toBeGreaterThan(0)
    expect(itinerary!.days[0].legs.length).toBe(itinerary!.days[0].activities.length - 1)
  })

  it('attaches purpose-preserving backups to priority activities (FR-41)', () => {
    const { itinerary } = plan()
    const priority = itinerary!.days
      .flatMap((d) => d.activities)
      .filter((a) => a.priority !== 'low')
    expect(priority.length).toBeGreaterThan(0)
    for (const activity of priority) {
      expect(activity.backups!.length).toBeGreaterThanOrEqual(1)
      expect(activity.backups!.length).toBeLessThanOrEqual(2)
      for (const backup of activity.backups!) {
        expect(backup.purpose_similarity).toBeGreaterThan(0)
      }
    }
  })

  it('respects the avoid list as a hard rule (FR-08)', () => {
    const { itinerary } = plan({ avoid: ['culture'] })
    const all = itinerary!.days.flatMap((d) => d.activities)
    expect(all.every((a) => !a.place.experience_types.includes('culture'))).toBe(true)
  })

  it('passes hard constraints after the L3 repair pass (G1)', () => {
    const { itinerary } = plan()
    const hard = itinerary!.validation.filter((v) => !v.passed && v.severity === 'hard')
    // A 3-day Seattle plan with a 30-minute limit may still leave soft warnings,
    // but every known opening-hours and travel rule must hold.
    expect(hard.filter((v) => v.rule === 'travel_time')).toHaveLength(0)
    expect(hard.filter((v) => v.rule === 'opening_hours')).toHaveLength(0)
  })
})

describe('infeasibility (FR-17, S10)', () => {
  it('reports INFEASIBLE with suggestions when the budget is far too low', () => {
    const { trip } = createTrip({ ...baseInput, budget: 5 })
    const { run_id } = startPlan(trip.id)
    const status = getRun(run_id)
    expect(status.status).toBe('infeasible')
    expect(status.terminal).toBe('INFEASIBLE')
    expect(status.infeasible?.blocking_rule).toBe('budget')
    expect(status.infeasible?.suggestions.length).toBeGreaterThan(0)
  })
})

describe('demo mode', () => {
  it('is deterministic in structure across runs', () => {
    __resetDemo()
    const first = plan()
    __resetDemo()
    const second = plan()
    expect(first.itinerary!.days.length).toBe(second.itinerary!.days.length)
    expect(first.itinerary!.days[0].activities.length).toBe(second.itinerary!.days[0].activities.length)
  })

  it('persists the trip with a current version', () => {
    const { tripId } = plan()
    expect(getTrip(tripId)?.current_version).toBe(1)
  })
})

// Keep the module-level step override from leaking to other suites.
__setStepMs(0)
