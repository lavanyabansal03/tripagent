/**
 * Map helpers — projection for the schematic fallback and bounds fitting.
 * The map is a reasoning tool, not decoration (Design Principle 5): it drives
 * clustering, travel times and the route diff.
 */
import type { Itinerary, LatLng, Place } from '../types'
import { categoryToken } from './visuals'

export interface Bounds {
  minLat: number
  maxLat: number
  minLng: number
  maxLng: number
}

export function collectPoints(itinerary: Itinerary | null, day?: number): Place[] {
  if (!itinerary) return []
  const days = day ? itinerary.days.filter((d) => d.day === day) : itinerary.days
  return days.flatMap((d) => d.activities.map((a) => a.place))
}

export function boundsFor(places: Place[], pad = 0.15): Bounds {
  if (places.length === 0) return { minLat: 47.55, maxLat: 47.7, minLng: -122.45, maxLng: -122.28 }
  const lats = places.map((p) => p.lat)
  const lngs = places.map((p) => p.lng)
  const minLat = Math.min(...lats)
  const maxLat = Math.max(...lats)
  const minLng = Math.min(...lngs)
  const maxLng = Math.max(...lngs)
  const latPad = Math.max((maxLat - minLat) * pad, 0.004)
  const lngPad = Math.max((maxLng - minLng) * pad, 0.004)
  return {
    minLat: minLat - latPad,
    maxLat: maxLat + latPad,
    minLng: minLng - lngPad,
    maxLng: maxLng + lngPad,
  }
}

/** Equirectangular projection into a 0..width / 0..height viewport. */
export function projectToView(
  point: LatLng,
  bounds: Bounds,
  width: number,
  height: number,
): { x: number; y: number } {
  const x = ((point.lng - bounds.minLng) / (bounds.maxLng - bounds.minLng)) * width
  const y = ((bounds.maxLat - point.lat) / (bounds.maxLat - bounds.minLat)) * height
  return { x, y }
}

export function markerFill(category: string | undefined): string {
  return categoryToken(category)
}

export const MAPBOX_STYLE = 'mapbox://styles/mapbox/light-v11'
export const MAPBOX_STYLE_DARK = 'mapbox://styles/mapbox/dark-v11'
