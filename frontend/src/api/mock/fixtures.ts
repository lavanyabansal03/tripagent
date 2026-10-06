/**
 * Recorded fixtures for DEMO_MODE (FR-55). These stand in for Mapbox +
 * Foursquare results so the whole flow runs offline and deterministically.
 * Two demo cities are tuned; Seattle is the primary one (Sprint review demo).
 */
import type {
  Activity,
  Backup,
  ExecutionEvent,
  ExperienceCategory,
  LocalSignal,
  Place,
  RouteLeg,
  TransportMode,
} from '../../types'

const NOW = Date.now()
const daysAgo = (n: number) => new Date(NOW - n * 86_400_000).toISOString()

interface PlaceSeed {
  id: string
  name: string
  address: string
  lat: number
  lng: number
  categories: string[]
  experience_types: ExperienceCategory[]
  price_level: 1 | 2 | 3 | 4 | null
  est_cost_low: number | null
  est_cost_high: number | null
  cost_basis: Place['cost_basis']
  hours: string | null
  rating: number | null
  review_count: number | null
  popularity: number | null
  local_signal: LocalSignal
  tip?: string
  ageDays?: number
}

const seeds: PlaceSeed[] = [
  {
    id: 'pl_pike_place',
    name: 'Pike Place Market',
    address: '85 Pike St, Seattle',
    lat: 47.6097,
    lng: -122.3425,
    categories: ['market', 'landmark'],
    experience_types: ['landmark', 'food', 'shopping'],
    price_level: null,
    est_cost_low: 0,
    est_cost_high: 0,
    cost_basis: 'free',
    hours: '09:00-18:00',
    rating: 4.6,
    review_count: 58210,
    popularity: 0.99,
    local_signal: 'tourist',
    tip: 'Go before 10am to see the fish throw without the crush.',
  },
  {
    id: 'pl_storyville',
    name: 'Storyville Coffee Pike Place',
    address: '94 Pike St #34, Seattle',
    lat: 47.6096,
    lng: -122.3416,
    categories: ['cafe'],
    experience_types: ['cafe', 'food'],
    price_level: 1,
    est_cost_low: 8,
    est_cost_high: 15,
    cost_basis: 'price_level',
    hours: '07:00-19:00',
    rating: 4.7,
    review_count: 3120,
    popularity: 0.82,
    local_signal: 'local',
    tip: 'Third-floor windows look over the market clock.',
  },
  {
    id: 'pl_starbucks_reserve',
    name: 'Starbucks Reserve Roastery',
    address: '1124 Pike St, Seattle',
    lat: 47.614,
    lng: -122.328,
    categories: ['cafe', 'roastery'],
    experience_types: ['cafe', 'food'],
    price_level: 2,
    est_cost_low: 10,
    est_cost_high: 25,
    cost_basis: 'price_level',
    hours: '07:00-22:00',
    rating: 4.5,
    review_count: 9840,
    popularity: 0.9,
    local_signal: 'tourist',
    tip: 'Ask for the barrel-aged cold brew.',
  },
  {
    id: 'pl_elliott_bay',
    name: 'Elliott Bay Book Company',
    address: '1521 10th Ave, Seattle',
    lat: 47.623,
    lng: -122.3207,
    categories: ['bookstore'],
    experience_types: ['shopping', 'culture'],
    price_level: null,
    est_cost_low: 0,
    est_cost_high: 0,
    cost_basis: 'free',
    hours: '10:00-22:00',
    rating: 4.8,
    review_count: 2740,
    popularity: 0.78,
    local_signal: 'local',
    tip: 'Downstairs readings most evenings.',
  },
  {
    id: 'pl_discovery_park',
    name: 'Discovery Park',
    address: '3801 Discovery Park Blvd, Seattle',
    lat: 47.6605,
    lng: -122.4068,
    categories: ['park', 'trail'],
    experience_types: ['nature'],
    price_level: null,
    est_cost_low: 0,
    est_cost_high: 0,
    cost_basis: 'free',
    hours: '06:00-23:00',
    rating: 4.8,
    review_count: 6210,
    popularity: 0.74,
    local_signal: 'local',
    tip: 'Loop Trail to the lighthouse is the classic walk.',
  },
  {
    id: 'pl_kerry_park',
    name: 'Kerry Park',
    address: '211 W Highland Dr, Seattle',
    lat: 47.6295,
    lng: -122.3599,
    categories: ['viewpoint'],
    experience_types: ['landmark', 'nature'],
    price_level: null,
    est_cost_low: 0,
    est_cost_high: 0,
    cost_basis: 'free',
    hours: '00:00-23:59',
    rating: 4.8,
    review_count: 14320,
    popularity: 0.93,
    local_signal: 'tourist',
    tip: 'Best at golden hour, tripod-friendly rail.',
  },
  {
    id: 'pl_chihuly',
    name: 'Chihuly Garden and Glass',
    address: '305 Harrison St, Seattle',
    lat: 47.6205,
    lng: -122.3509,
    categories: ['museum', 'gallery'],
    experience_types: ['culture'],
    price_level: 3,
    est_cost_low: 32,
    est_cost_high: 40,
    cost_basis: 'price_level',
    hours: '10:00-18:00',
    rating: 4.7,
    review_count: 21140,
    popularity: 0.94,
    local_signal: 'tourist',
  },
  {
    id: 'pl_mopop',
    name: 'Museum of Pop Culture',
    address: '325 5th Ave N, Seattle',
    lat: 47.6215,
    lng: -122.3484,
    categories: ['museum'],
    experience_types: ['culture'],
    price_level: 3,
    est_cost_low: 30,
    est_cost_high: 38,
    cost_basis: 'price_level',
    hours: '10:00-17:00',
    rating: 4.5,
    review_count: 18760,
    popularity: 0.91,
    local_signal: 'tourist',
  },
  {
    id: 'pl_space_needle',
    name: 'Space Needle',
    address: '400 Broad St, Seattle',
    lat: 47.6205,
    lng: -122.3493,
    categories: ['landmark'],
    experience_types: ['landmark'],
    price_level: 4,
    est_cost_low: 35,
    est_cost_high: 42,
    cost_basis: 'price_level',
    hours: '10:00-21:00',
    rating: 4.6,
    review_count: 49730,
    popularity: 0.98,
    local_signal: 'tourist',
  },
  {
    id: 'pl_sculpture_park',
    name: 'Olympic Sculpture Park',
    address: '2901 Western Ave, Seattle',
    lat: 47.6166,
    lng: -122.3552,
    categories: ['park', 'gallery'],
    experience_types: ['culture', 'nature'],
    price_level: null,
    est_cost_low: 0,
    est_cost_high: 0,
    cost_basis: 'free',
    hours: '05:00-21:00',
    rating: 4.6,
    review_count: 4870,
    popularity: 0.72,
    local_signal: 'local',
  },
  {
    id: 'pl_fremont_troll',
    name: 'Fremont Troll',
    address: 'N 36th St, Seattle',
    lat: 47.651,
    lng: -122.3473,
    categories: ['public-art'],
    experience_types: ['landmark'],
    price_level: null,
    est_cost_low: 0,
    est_cost_high: 0,
    cost_basis: 'free',
    hours: '00:00-23:59',
    rating: 4.4,
    review_count: 5120,
    popularity: 0.7,
    local_signal: 'hidden',
  },
  {
    id: 'pl_gas_works',
    name: 'Gas Works Park',
    address: '2101 N Northlake Way, Seattle',
    lat: 47.6456,
    lng: -122.3344,
    categories: ['park'],
    experience_types: ['nature', 'landmark'],
    price_level: null,
    est_cost_low: 0,
    est_cost_high: 0,
    cost_basis: 'free',
    hours: '06:00-22:00',
    rating: 4.7,
    review_count: 8140,
    popularity: 0.8,
    local_signal: 'local',
    tip: 'Kite hill has the skyline view.',
  },
  {
    id: 'pl_canon',
    name: 'Canon',
    address: '928 12th Ave, Seattle',
    lat: 47.6233,
    lng: -122.3197,
    categories: ['bar', 'cocktails'],
    experience_types: ['nightlife'],
    price_level: 3,
    est_cost_low: 25,
    est_cost_high: 60,
    cost_basis: 'price_level',
    hours: '17:00-01:00',
    rating: 4.6,
    review_count: 2210,
    popularity: 0.69,
    local_signal: 'local',
  },
  {
    id: 'pl_needle_and_thread',
    name: 'Needle & Thread',
    address: '1100 E Pike St, Seattle',
    lat: 47.614,
    lng: -122.3185,
    categories: ['bar', 'cocktails'],
    experience_types: ['nightlife'],
    price_level: 2,
    est_cost_low: 14,
    est_cost_high: 30,
    cost_basis: 'price_level',
    hours: '17:00-02:00',
    rating: 4.5,
    review_count: 980,
    popularity: 0.55,
    local_signal: 'hidden',
    tip: 'Hidden behind a coffee shop; ask for the back room.',
  },
  {
    id: 'pl_walrus',
    name: 'The Walrus and the Carpenter',
    address: '4743 Ballard Ave NW, Seattle',
    lat: 47.6687,
    lng: -122.3847,
    categories: ['restaurant', 'seafood'],
    experience_types: ['food'],
    price_level: 3,
    est_cost_low: 30,
    est_cost_high: 55,
    cost_basis: 'price_level',
    hours: '16:00-22:00',
    rating: 4.7,
    review_count: 3480,
    popularity: 0.76,
    local_signal: 'local',
    tip: 'Walk in early or wait; oysters are the point.',
  },
  {
    id: 'pl_ballard_locks',
    name: 'Hiram M. Chittenden Locks',
    address: '3015 NW 54th St, Seattle',
    lat: 47.6656,
    lng: -122.3973,
    categories: ['park', 'landmark'],
    experience_types: ['nature', 'landmark'],
    price_level: null,
    est_cost_low: 0,
    est_cost_high: 0,
    cost_basis: 'free',
    hours: '07:00-21:00',
    rating: 4.7,
    review_count: 9360,
    popularity: 0.83,
    local_signal: 'local',
  },
  {
    id: 'pl_uw_quad',
    name: 'University of Washington Quad',
    address: '4069 Spokane Ln, Seattle',
    lat: 47.6573,
    lng: -122.3077,
    categories: ['campus', 'park'],
    experience_types: ['nature', 'culture'],
    price_level: null,
    est_cost_low: 0,
    est_cost_high: 0,
    cost_basis: 'free',
    hours: '00:00-23:59',
    rating: 4.7,
    review_count: 3210,
    popularity: 0.66,
    local_signal: 'hidden',
  },
  {
    id: 'pl_terra_plata',
    name: 'Terra Plata',
    address: '1501 Melrose Ave, Seattle',
    lat: 47.6236,
    lng: -122.3205,
    categories: ['restaurant'],
    experience_types: ['food'],
    price_level: 3,
    est_cost_low: 30,
    est_cost_high: 50,
    cost_basis: 'price_level',
    hours: '11:00-22:00',
    rating: 4.5,
    review_count: 1980,
    popularity: 0.64,
    local_signal: 'local',
  },
  {
    id: 'pl_victrola',
    name: 'Victrola Coffee Roasters',
    address: '310 E Pike St, Seattle',
    lat: 47.614,
    lng: -122.3207,
    categories: ['cafe'],
    experience_types: ['cafe'],
    price_level: 1,
    est_cost_low: 6,
    est_cost_high: 14,
    cost_basis: 'price_level',
    hours: '06:00-19:00',
    rating: 4.6,
    review_count: 1640,
    popularity: 0.6,
    local_signal: 'hidden',
  },
  {
    id: 'pl_central_library',
    name: 'Seattle Central Library',
    address: '1000 4th Ave, Seattle',
    lat: 47.6062,
    lng: -122.3324,
    categories: ['library', 'architecture'],
    experience_types: ['culture', 'landmark'],
    price_level: null,
    est_cost_low: 0,
    est_cost_high: 0,
    cost_basis: 'free',
    hours: '10:00-20:00',
    rating: 4.7,
    review_count: 6210,
    popularity: 0.85,
    local_signal: 'tourist',
    tip: 'The Book Spiral on level 10 is worth the walk up.',
  },
  {
    id: 'pl_alki_beach',
    name: 'Alki Beach Park',
    address: '1702 Alki Ave SW, Seattle',
    lat: 47.5796,
    lng: -122.41,
    categories: ['beach', 'park'],
    experience_types: ['nature'],
    price_level: null,
    est_cost_low: 0,
    est_cost_high: 0,
    cost_basis: 'free',
    hours: '04:00-23:30',
    rating: 4.6,
    review_count: 7420,
    popularity: 0.79,
    local_signal: 'local',
  },
]

export const demoPlaces: Place[] = seeds.map((s) => ({
  id: s.id,
  sources: ['mapbox', 'foursquare'],
  provider_ids: { mapbox: s.id, foursquare: `fsq_${s.id.slice(3)}` },
  name: s.name,
  categories: s.categories,
  experience_types: s.experience_types,
  lat: s.lat,
  lng: s.lng,
  address: s.address,
  price_level: s.price_level,
  est_cost_low: s.est_cost_low,
  est_cost_high: s.est_cost_high,
  cost_basis: s.cost_basis,
  hours: s.hours,
  rating: s.rating,
  review_count: s.review_count,
  popularity: s.popularity,
  local_signal: s.local_signal,
  field_provenance: {
    hours: 'explicit',
    price_level: 'inferred',
    rating: 'explicit',
    local_signal: 'inferred',
  },
  retrieved_at: daysAgo(s.ageDays ?? 1),
  tip: s.tip ?? null,
}))

export const placesById = new Map(demoPlaces.map((p) => [p.id, p]))

/** Deterministic pseudo-travel time between two places, in minutes. */
export function travelMinutes(a: Place, b: Place, mode: TransportMode): number {
  const R = 6371
  const dLat = ((b.lat - a.lat) * Math.PI) / 180
  const dLng = ((b.lng - a.lng) * Math.PI) / 180
  const lat1 = (a.lat * Math.PI) / 180
  const lat2 = (b.lat * Math.PI) / 180
  const h =
    Math.sin(dLat / 2) ** 2 + Math.cos(lat1) * Math.cos(lat2) * Math.sin(dLng / 2) ** 2
  const km = 2 * R * Math.asin(Math.sqrt(h))
  const speed = { walking: 4.5, cycling: 14, transit: 18, driving: 26 }[mode]
  const overhead = mode === 'transit' ? 8 : mode === 'walking' ? 0 : 4
  return Math.max(4, Math.round((km / speed) * 60 + overhead))
}

export function makeLeg(
  from: Activity,
  to: Activity,
  mode: TransportMode,
  changed = false,
): RouteLeg {
  const a = from.place
  const b = to.place
  return {
    from_activity_id: from.id,
    to_activity_id: to.id,
    mode,
    duration_min: travelMinutes(a, b, mode),
    distance_km: Number(
      (
        2 *
        6371 *
        Math.asin(
          Math.sqrt(
            Math.sin((((b.lat - a.lat) * Math.PI) / 180) / 2) ** 2 +
              Math.cos((a.lat * Math.PI) / 180) *
                Math.cos((b.lat * Math.PI) / 180) *
                Math.sin((((b.lng - a.lng) * Math.PI) / 180) / 2) ** 2,
          ),
        )
      ).toFixed(2),
    ),
    geometry: [
      { lat: a.lat, lng: a.lng },
      { lat: b.lat, lng: b.lng },
    ],
    changed,
  }
}

/** Purpose tags used by the Backup Agent (FR-40) and repair (FR-43). */
export function purposeTags(place: Place): string[] {
  const map: Partial<Record<ExperienceCategory, string>> = {
    food: 'food',
    cafe: 'food',
    nature: 'relaxation',
    culture: 'culture',
    shopping: 'shopping',
    nightlife: 'nightlife',
    event: 'event',
    landmark: 'views',
  }
  const tags = new Set<string>()
  for (const c of place.experience_types) if (map[c]) tags.add(map[c]!)
  if (place.experience_types.includes('landmark') || place.experience_types.includes('nature')) {
    tags.add('views')
  }
  return [...tags]
}

export function priorityFor(place: Place): Activity['priority'] {
  if (place.local_signal === 'local' || place.local_signal === 'hidden') return 'high'
  if (place.experience_types.includes('food') || place.experience_types.includes('culture'))
    return 'medium'
  return 'low'
}

/** Purpose-preserving backups, ranked by shared tags then cost (FR-41/43). */
export function buildBackups(activity: Activity, all: Place[]): Backup[] {
  const original = purposeTags(activity.place)
  const originalTypes = activity.place.experience_types
  const candidates = all.filter((p) => p.id !== activity.place.id)
  const scored = candidates
    .map((p) => {
      const types = p.experience_types
      const typeOverlap = types.some((e) => originalTypes.includes(e))
      const tags = purposeTags(p)
      const shared = tags.filter((tag) => original.includes(tag)).length
      // Same experience type OR shared purpose tag counts as a candidate.
      const similarity = original.length ? Math.max(shared / original.length, typeOverlap ? 0.5 : 0) : 0
      return { place: p, similarity }
    })
    .filter((x) => x.similarity > 0)
    .sort((a, b) => b.similarity - a.similarity || (a.place.est_cost_high ?? 0) - (b.place.est_cost_high ?? 0))
    .slice(0, 2)

  return scored.map((x, i) => ({
    activity_id: activity.id,
    place_id: x.place.id,
    rank: i + 1,
    purpose_similarity: x.similarity,
    cost_delta: (x.place.est_cost_high ?? 0) - (activity.est_cost ?? 0),
    travel_delta_min: 0,
    validated_at: new Date(NOW - 3_600_000).toISOString(),
  }))
}

/** Step messages map to real graph nodes (UX Copy, "Planning in progress"). */
export const planningSteps = [
  { node: 'intake', key: 'reading' },
  { node: 'discovery', key: 'finding' },
  { node: 'travel_matrix', key: 'checking' },
  { node: 'planner', key: 'arranging' },
  { node: 'backup', key: 'backups' },
  { node: 'validator', key: 'doubleChecking' },
] as const

export function executionEvent(
  partial: Omit<ExecutionEvent, 'id' | 'ts'> & { ts?: string },
): ExecutionEvent {
  return {
    id: `ev_${Math.random().toString(36).slice(2, 10)}`,
    ts: partial.ts ?? new Date().toISOString(),
    ...partial,
  }
}

export function dayDate(startIso: string, day: number): string {
  const d = new Date(startIso)
  d.setDate(d.getDate() + (day - 1))
  return d.toISOString().slice(0, 10)
}
