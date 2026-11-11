import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/svelte'
import MapView from '../components/MapView.svelte'
import { demoPlaces } from '../api/mock/fixtures'
import type { Itinerary, Place } from '../types'

/** A one-day plan with the given places (only the fields the map reads). */
function planWith(places: Place[]): Itinerary {
  return {
    trip_id: 'trip_1',
    version: 1,
    score: 1,
    created_at: '2026-11-11T00:00:00Z',
    validation: [],
    days: [
      {
        day: 1,
        date: '2026-11-18',
        legs: [],
        activities: places.map((place, i) => ({ id: `act_${i}`, place, place_id: place.id })),
      },
    ],
  } as unknown as Itinerary
}

describe('MapView places credit', () => {
  it('shows "Powered by Geoapify" and the OpenStreetMap credit for Geoapify places', () => {
    const place: Place = { ...demoPlaces[0], sources: ['geoapify'] }
    render(MapView, { itinerary: planWith([place]), day: 1 })
    const credit = screen.getByTestId('places-credit')
    expect(credit).toHaveTextContent('Powered by Geoapify')
    expect(credit).toHaveTextContent('© OpenStreetMap contributors')
    expect(screen.getByRole('link', { name: 'Powered by Geoapify' })).toHaveAttribute(
      'href',
      'https://www.geoapify.com/',
    )
  })

  it('shows no Geoapify credit when no place came from Geoapify', () => {
    const place: Place = { ...demoPlaces[0], sources: ['seed'] }
    render(MapView, { itinerary: planWith([place]), day: 1 })
    expect(screen.queryByTestId('places-credit')).not.toBeInTheDocument()
  })
})
