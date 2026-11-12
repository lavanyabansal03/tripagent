import { beforeEach, describe, expect, it } from 'vitest'
import { rememberTripInUrl, store, tripIdFromUrl } from '../state/store.svelte'
import type { TripFormInput } from '../api/client'

// Tests run in demo mode, so the built-in demo engine plays the backend.
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

describe('trip survives a page refresh', () => {
  beforeEach(() => {
    store.reset()
    window.history.replaceState(null, '', '/')
  })

  it('puts the trip id in the address bar when a trip is created', async () => {
    const trip = await store.createTrip(input)
    expect(tripIdFromUrl()).toBe(trip.id)
    expect(window.location.search).toBe(`?trip=${trip.id}`)
  })

  it('brings back a trip that has no plan yet on the understood page', async () => {
    const trip = await store.createTrip(input)
    store.reset() // what a refresh does: all state is gone
    expect(await store.restoreTrip(trip.id)).toBe(true)
    expect(store.trip?.id).toBe(trip.id)
    expect(store.route.name).toBe('planning')
  })

  it('brings back the plan when the trip has one', async () => {
    const trip = await store.createTrip(input)
    await store.startPlanning(trip.id)
    expect(store.route.name).toBe('itinerary')
    store.reset()
    expect(await store.restoreTrip(trip.id)).toBe(true)
    expect(store.route.name).toBe('itinerary')
    expect(store.itinerary).not.toBeNull()
  })

  it('goes back to the empty form for an unknown trip and cleans the address bar', async () => {
    rememberTripInUrl('no-such-trip')
    expect(await store.restoreTrip('no-such-trip')).toBe(false)
    expect(store.route.name).toBe('setup')
    expect(tripIdFromUrl()).toBeNull()
  })

  it('starting over removes the trip from the address bar', async () => {
    await store.createTrip(input)
    store.reset()
    expect(tripIdFromUrl()).toBeNull()
  })
})
