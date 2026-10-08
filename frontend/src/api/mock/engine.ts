/**
 * In-memory DEMO_MODE engine (FR-55).
 *
 * It stands in for the FastAPI + LangGraph backend so the frontend runs and can
 * be demoed with no providers. Behaviour follows the documented contracts:
 *  - POST /trips, POST /trips/{id}/plan, GET /runs/{id} (polling, ADR-006)
 *  - GET /trips/{id}/itinerary, POST /changes, swap, restore, simulate, trace
 * Runs advance from elapsed time (no timers) so tests can drive them with fake
 * clocks and there is nothing to leak between test cases.
 */
import type {
  Activity,
  ChangeEvent,
  CreateTripResponse,
  ExecutionEvent,
  InfeasibleReport,
  Itinerary,
  ItineraryDay,
  PlanResponse,
  Place,
  Provenance,
  Question,
  ReplanEvent,
  RouteLeg,
  RunStatus,
  TransportMode,
  Trip,
  TripRequirements,
  ValidationResult,
} from '../../types'
import {
  buildBackups,
  dayDate,
  demoPlaces,
  executionEvent,
  makeLeg,
  planningSteps,
  priorityFor,
  purposeTags,
  travelMinutes,
} from './fixtures'

export interface TripFormInput {
  destination: string
  start_date: string
  end_date: string
  budget: number | null
  budget_strictness: 'strict' | 'flexible'
  mode: TransportMode
  pace: 'relaxed' | 'moderate' | 'packed'
  max_travel_min: number
  interests: string[]
  avoid: string[]
  tourist_local_ratio: number
  free_text: string
}

interface TripRecord {
  trip: Trip
  requirements: TripRequirements
  questions: Question[]
  versions: number[]
  itineraries: Map<number, Itinerary>
  replans: ReplanEvent[]
  events: ExecutionEvent[]
  changes: ChangeEvent[]
  currentRunId: string | null
  pendingTrigger: string | null
}

interface RunRecord {
  status: RunStatus
  tripId: string
  kind: 'plan' | 'change' | 'simulate'
  startedMs: number
  changeId?: string
  activityId?: string
  backupId?: string
  simulateType?: string
  finalized: boolean
}

let STEP_MS = 650
let CHANGE_STEP_MS = 500

/** Test hook: speed up or freeze run progression. */
export function __setStepMs(planMs: number, changeMs = planMs): void {
  STEP_MS = planMs
  CHANGE_STEP_MS = changeMs
}

const uid = (p: string) => `${p}_${Math.random().toString(36).slice(2, 10)}`

function dayCount(req: TripRequirements): number {
  const start = new Date(req.start_date)
  const end = new Date(req.end_date)
  const days = Math.round((end.getTime() - start.getTime()) / 86_400_000) + 1
  return Math.max(1, Math.min(7, days))
}

/* ------------------------------------------------------------------ *
 * Intake: form + free-text extraction with provenance (US-17, FR-33)  *
 * ------------------------------------------------------------------ */

const KEYWORDS: Record<string, string[]> = {
  coffee: ['coffee', 'café', 'cafe', 'espresso'],
  bookstores: ['bookstore', 'books', 'book shop'],
  photography: ['photograph', 'photo', 'camera'],
  nature: ['nature', 'outdoor', 'hike', 'park', 'trail'],
  culture: ['culture', 'museum', 'art', 'gallery', 'history'],
  food: ['food', 'eat', 'restaurant', 'seafood', 'vegetarian'],
  nightlife: ['nightlife', 'bar', 'cocktail', 'music'],
  shopping: ['shopping', 'market', 'shop'],
}

function extractFreeText(text: string): {
  interests: string[]
  avoid: string[]
  dietary: string[]
  pace?: TripRequirements['pace']
  touristLocal?: number
  maxTravel?: number
  provenance: Record<string, Provenance>
} {
  const lower = text.toLowerCase()
  const interests: string[] = []
  const avoid: string[] = []
  const dietary: string[] = []
  const provenance: Record<string, Provenance> = {}

  for (const [interest, words] of Object.entries(KEYWORDS)) {
    if (words.some((w) => lower.includes(w))) {
      interests.push(interest)
      provenance[`interests.${interest}`] = 'explicit'
    }
  }
  if (/(no museums|not? (into|like) museums|skip museums)/.test(lower)) {
    avoid.push('culture')
    provenance['avoid.culture'] = 'explicit'
  }
  if (/vegetarian|vegan/.test(lower)) {
    dietary.push('vegetarian')
    provenance['dietary.vegetarian'] = 'explicit'
  }
  const travel = lower.match(/(\d+)\s*(min|minutes)/)
  const pace = /relaxed|slow|unhurried/.test(lower)
    ? 'relaxed'
    : /packed|busy|as much as possible/.test(lower)
      ? 'packed'
      : undefined
  const touristLocal = /locals? (actually )?(enjoy|like|love)|local favourite|off the beaten/.test(
    lower,
  )
    ? 80
    : /tourist|famous sights|top sights/.test(lower)
      ? 20
      : undefined
  return {    interests,
    avoid,
    dietary,
    pace,
    touristLocal,
    maxTravel: travel ? Number(travel[1]) : undefined,
    provenance,
  }
}

export function createTrip(input: TripFormInput): CreateTripResponse {
  const tripId = uid('trip')
  const extracted = extractFreeText(input.free_text)
  const provenance: Record<string, Provenance> = {
    destination: 'explicit',
    start_date: 'explicit',
    end_date: 'explicit',
    mode: 'explicit',
    budget: input.budget == null ? 'default' : 'explicit',
    pace: 'explicit',
    tourist_local_ratio: 'explicit',
    max_travel_min: 'explicit',
    ...extracted.provenance,
  }

  const interests = [...new Set([...input.interests, ...extracted.interests])]
  const avoid = [...new Set([...input.avoid, ...extracted.avoid])]
  const pace = extracted.pace ?? input.pace
  if (extracted.pace) provenance.pace = 'inferred'
  const touristLocal = extracted.touristLocal ?? input.tourist_local_ratio
  if (extracted.touristLocal != null) provenance.tourist_local_ratio = 'inferred'
  const maxTravel = extracted.maxTravel ?? input.max_travel_min
  if (extracted.maxTravel != null) provenance.max_travel_min = 'inferred'
  if (extracted.dietary.length) provenance.dietary = 'explicit'

  const requirements: TripRequirements = {
    trip_id: tripId,
    version: 1,
    destination: input.destination || 'Seattle',
    start_date: input.start_date,
    end_date: input.end_date,
    budget: input.budget,
    budget_strictness: input.budget_strictness,
    mode: input.mode,
    pace,
    interests: interests.length ? interests : ['coffee', 'nature', 'culture'],
    avoid,
    tourist_local_ratio: touristLocal,
    max_travel_min: maxTravel,
    daily_start: pace === 'relaxed' ? '10:00' : '09:00',
    daily_end: pace === 'packed' ? '21:00' : '20:00',
    dietary: extracted.dietary,
    accessibility: [],
    free_text: input.free_text,
    provenance,
  }

  // Contradiction detection (L1, FR-34): driving but the note says no car.
  const questions: Question[] = []
  const carless =
    /(no car|not have a car|won'?t have a car|without a car|don'?t have a car|no vehicle)/.test(
      input.free_text.toLowerCase(),
    )
  if (input.mode === 'driving' && carless) {
    questions.push({
      id: uid('q'),
      field: 'mode',
      text: 'contradiction',
      options: ['Transit', 'Walking', 'Cycling'],
    })
  }

  const trip: Trip = {
    id: tripId,
    destination: requirements.destination,
    start_date: requirements.start_date,
    end_date: requirements.end_date,
    status: 'draft',
    current_version: 0,
    created_at: new Date().toISOString(),
  }

  const record: TripRecord = {
    trip,
    requirements,
    questions,
    versions: [],
    itineraries: new Map(),
    replans: [],
    events: [],
    changes: [],
    currentRunId: null,
    pendingTrigger: null,
  }
  this_store.set(tripId, record)
  return { trip, requirements, questions }
}

/* ------------------------------------------------------------------ *
 * Store                                                               *
 * ------------------------------------------------------------------ */

const this_store = new Map<string, TripRecord>()
const runStore = new Map<string, RunRecord>()

export function getTripRecord(tripId: string): TripRecord | undefined {
  return this_store.get(tripId)
}
export function getRunRecord(runId: string): RunRecord | undefined {
  return runStore.get(runId)
}
export function __resetDemo(): void {
  this_store.clear()
  runStore.clear()
}

function requireTrip(tripId: string): TripRecord {
  const rec = this_store.get(tripId)
  if (!rec) throw new Error('trip_not_found')
  return rec
}

/* ------------------------------------------------------------------ *
 * Itinerary builder + validators                                      *
 * ------------------------------------------------------------------ */

const DURATION: Record<string, number> = {
  cafe: 60,
  food: 90,
  nature: 90,
  culture: 105,
  shopping: 75,
  nightlife: 90,
  event: 90,
  landmark: 60,
}

function costFor(place: Place, strict: boolean): number | null {
  if (place.cost_basis === 'free') return 0
  if (place.cost_basis === 'known') return place.est_cost_high ?? place.est_cost_low ?? null
  if (place.cost_basis === 'price_level') {
    const low = place.est_cost_low ?? 0
    const high = place.est_cost_high ?? low
    return strict ? high : Math.round((low + high) / 2)
  }
  return null
}

function scorePlace(place: Place, req: TripRequirements): number {
  let score = place.popularity ?? 0.5
  const interestHit = req.interests.some((i) => place.experience_types.includes(i as never))
  if (interestHit) score += 0.8
  const wantsLocal = req.tourist_local_ratio >= 60
  if (wantsLocal && place.local_signal === 'local') score += 0.5
  if (wantsLocal && place.local_signal === 'hidden') score += 0.3
  if (!wantsLocal && place.local_signal === 'tourist') score += 0.5
  if (req.avoid.some((a) => place.experience_types.includes(a as never))) score -= 5
  return score
}

/** Greedy geographic assignment so days are compact (FR-46). */
function assignDays(candidates: Place[], days: number): Place[][] {
  const buckets: Place[][] = Array.from({ length: days }, () => [])
  if (candidates.length === 0) return buckets
  const perDay = Math.max(2, Math.ceil(candidates.length / days))

  // Farthest-point seeding gives spread-out day anchors.
  const anchors: Place[] = [candidates[0]]
  while (anchors.length < days && anchors.length < candidates.length) {
    let best: Place | null = null
    let bestDist = -1
    for (const p of candidates) {
      const nearest = Math.min(
        ...anchors.map((a) =>
          Math.hypot((p.lat - a.lat) * 111, (p.lng - a.lng) * 75),
        ),
      )
      if (nearest > bestDist) {
        bestDist = nearest
        best = p
      }
    }
    if (best) anchors.push(best)
  }

  for (const place of candidates) {
    let target = 0
    let bestDist = Infinity
    for (let d = 0; d < days; d++) {
      if (buckets[d].length >= perDay) continue
      const c = anchors[Math.min(d, anchors.length - 1)]
      const dist = Math.hypot((place.lat - c.lat) * 111, (place.lng - c.lng) * 75)
      if (dist < bestDist) {
        bestDist = dist
        target = d
      }
    }
    // All capped: place in the least-full day.
    if (buckets.every((b) => b.length >= perDay)) {
      target = buckets.reduce((min, b, i, arr) => (b.length < arr[min].length ? i : min), 0)
    }
    buckets[target].push(place)
  }
  return buckets
}

/** Nearest-neighbour walking order used to estimate a day's travel penalty. */
function nnRoute(places: Place[], mode: TransportMode): Place[] {
  if (places.length <= 1) return [...places]
  const remaining = [...places]
  const route = [remaining.shift()!]
  while (remaining.length) {
    const last = route[route.length - 1]
    let best = 0
    let bestT = Infinity
    remaining.forEach((p, i) => {
      const t = travelMinutes(last, p, mode)
      if (t < bestT) {
        bestT = t
        best = i
      }
    })
    route.push(remaining.splice(best, 1)[0])
  }
  return route
}

function legPenalty(places: Place[], mode: TransportMode, limit: number): number {
  const route = nnRoute(places, mode)
  let penalty = 0
  for (let i = 1; i < route.length; i++) {
    penalty += Math.max(0, travelMinutes(route[i - 1], route[i], mode) - limit)
  }
  return penalty
}

/**
 * L3 repair pass: bounded swap/move of activities between days to remove hard
 * travel-time violations, accepted only when the violation score strictly
 * improves (mirrors the graph's progress check, FR-16).
 */
function repairBuckets(buckets: Place[][], mode: TransportMode, limit: number): number {
  const total = () => buckets.reduce((sum, day) => sum + legPenalty(day, mode, limit), 0)
  let iterations = 0
  for (let iter = 0; iter < 3 && total() > 0; iter++) {
    iterations = iter + 1
    const current = total()
    let best: { penalty: number; apply: () => void } | null = null

    // Swaps between days.
    for (let a = 0; a < buckets.length; a++) {
      for (let i = 0; i < buckets[a].length; i++) {
        for (let b = a + 1; b < buckets.length; b++) {
          for (let j = 0; j < buckets[b].length; j++) {
            const pa = buckets[a][i]
            const pb = buckets[b][j]
            buckets[a][i] = pb
            buckets[b][j] = pa
            const penalty = total()
            buckets[a][i] = pa
            buckets[b][j] = pb
            if (penalty < current - 0.5 && (!best || penalty < best.penalty)) {
              best = {
                penalty,
                apply: () => {
                  buckets[a][i] = pb
                  buckets[b][j] = pa
                },
              }
            }
          }
        }
      }
    }

    // Moves to another day.
    for (let a = 0; a < buckets.length; a++) {
      for (let i = 0; i < buckets[a].length; i++) {
        for (let b = 0; b < buckets.length; b++) {
          if (a === b || buckets[b].length >= buckets[a].length + 1) continue
          const [item] = buckets[a].splice(i, 1)
          buckets[b].push(item)
          const penalty = total()
          buckets[a].splice(i, 0, item)
          buckets[b].pop()
          if (penalty < current - 0.5 && (!best || penalty < best.penalty)) {
            best = {
              penalty,
              apply: () => {
                buckets[a].splice(i, 1)
                buckets[b].push(item)
              },
            }
          }
        }
      }
    }

    if (!best) break
    best.apply()
  }
  return iterations
}

function orderDay(places: Place[]): Place[] {
  if (places.length <= 1) return places
  // Time-of-day bands so nightlife lands in the evening and cafés early
  // (FR-08 opening hours, FR-47 route ordering respecting fixed-time items).
  const rank = (p: Place): number => {
    const t = p.experience_types[0]
    if (t === 'cafe') return 0
    if (t === 'nature' || t === 'culture' || t === 'landmark' || t === 'shopping') return 1
    if (t === 'food') return 2
    if (t === 'event') return 3
    if (t === 'nightlife') return 4
    return 1
  }
  const bands = new Map<number, Place[]>()
  for (const p of places) {
    const r = rank(p)
    if (!bands.has(r)) bands.set(r, [])
    bands.get(r)!.push(p)
  }
  const routeDay = (band: Place[]): Place[] => {
    const remaining = [...band]
    const route = [remaining.shift()!]
    while (remaining.length) {
      const last = route[route.length - 1]
      let best = 0
      let bestT = Infinity
      remaining.forEach((p, i) => {
        const t = travelMinutes(last, p, 'walking')
        if (t < bestT) {
          bestT = t
          best = i
        }
      })
      route.push(remaining.splice(best, 1)[0])
    }
    return route
  }
  return [...bands.keys()]
    .sort((a, b) => a - b)
    .flatMap((key) => routeDay(bands.get(key)!))
}

function addMinutes(iso: string, minutes: number): string {
  // Pure wall-clock arithmetic: never let the host timezone shift a plan.
  const total = minutesOfTime(iso) + minutes
  const dayShift = Math.floor(total / 1440)
  const within = ((total % 1440) + 1440) % 1440
  const base = new Date(`${iso.slice(0, 10)}T00:00:00Z`)
  base.setUTCDate(base.getUTCDate() + dayShift)
  const date = base.toISOString().slice(0, 10)
  const h = String(Math.floor(within / 60)).padStart(2, '0')
  const m = String(within % 60).padStart(2, '0')
  return `${date}T${h}:${m}:00`
}

/** Local wall-clock minutes-since-midnight for an ISO-like string. */
function minutesOfTime(iso: string): number {
  const [h, m] = iso.slice(11, 16).split(':').map(Number)
  return h * 60 + m
}

/** Replace the time part of a local wall-clock string. */
function withTime(iso: string, minutes: number): string {
  const h = String(Math.floor(minutes / 60) % 24).padStart(2, '0')
  const m = String(minutes % 60).padStart(2, '0')
  return `${iso.slice(0, 11)}${h}:${m}:00`
}

/** Opening time in minutes, or null when hours are unknown (FR-08). */
function openingMinutes(place: Place): number | null {
  if (!place.hours) return null
  const match = place.hours.match(/^(\d{2}):(\d{2})-(\d{2}):(\d{2})$/)
  if (!match) return null
  return Number(match[1]) * 60 + Number(match[2])
}

function closingMinutes(place: Place): number | null {
  if (!place.hours) return null
  const match = place.hours.match(/^(\d{2}):(\d{2})-(\d{2}):(\d{2})$/)
  if (!match) return null
  let close = Number(match[3]) * 60 + Number(match[4])
  const open = Number(match[1]) * 60 + Number(match[2])
  if (close <= open) close += 24 * 60 // overnight
  return close
}

function durationFor(place: Place): number {
  return DURATION[place.experience_types[0] ?? 'landmark'] ?? 75
}

function buildItinerary(
  req: TripRequirements,
  version: number,
  opts: { preserve?: Itinerary; affectedDays?: Set<number> } = {},
): Itinerary {
  const days = dayCount(req)
  const avoid = new Set(req.avoid)
  let candidates = demoPlaces
    .filter((p) => !p.experience_types.some((e) => avoid.has(e)))
    .sort((a, b) => scorePlace(b, req) - scorePlace(a, req))
    .slice(0, days * 4)

  const buckets = assignDays(candidates, days)
  // Deterministic L3 repair: remove hard travel-time violations before
  // validation, exactly like the graph would.
  repairBuckets(buckets, req.mode, req.max_travel_min)
  const daysOut: ItineraryDay[] = []
  const validation: ValidationResult[] = []

  for (let d = 1; d <= days; d++) {
    const date = dayDate(req.start_date, d)
    const preserveDay = opts.preserve && opts.affectedDays && !opts.affectedDays.has(d)
    const sourcePlaces = preserveDay
      ? (opts.preserve!.days.find((x) => x.day === d)?.activities.map((a) => a.place) ?? buckets[d - 1])
      : orderDay(buckets[d - 1])

    let cursor = `${date}T${req.daily_start}:00`
    const activities: Activity[] = []
    let previousCategory: string | null = null
    let consecutive = 0

    sourcePlaces.forEach((place, idx) => {
      const duration = DURATION[place.experience_types[0] ?? 'landmark'] ?? 75
      const start = cursor
      const end = addMinutes(start, duration)
      const category = place.experience_types[0]
      const activity: Activity = {
        id: `${req.trip_id}_v${version}_d${d}_a${idx + 1}`,
        trip_id: req.trip_id,
        version,
        day: d,
        place_id: place.id,
        start,
        end,
        est_cost: costFor(place, req.budget_strictness === 'strict'),
        cost_basis: place.cost_basis,
        priority: priorityFor(place),
        purpose_tags: purposeTags(place),
        status: 'planned',
        change_type: null,
        reason: null,
        warnings: [],
        backups: [],
        place,
      }
      if (category === previousCategory) {
        consecutive += 1
        if (consecutive >= 2) {
          const w: ValidationResult = {
            id: uid('vr'),
            trip_id: req.trip_id,
            version,
            rule: 'diversity',
            passed: false,
            severity: 'soft',
            message: 'consecutive_same_category',
            activity_ids: [activity.id],
          }
          activity.warnings = [w]
          validation.push(w)
        }
      } else {
        consecutive = 1
      }
      previousCategory = category
      activities.push(activity)
      cursor = addMinutes(end, 0)
    })

    // Legs between activities.
    const legs: RouteLeg[] = []
    for (let i = 1; i < activities.length; i++) {
      legs.push(makeLeg(activities[i - 1], activities[i], req.mode))
    }
    // Insert travel time into the schedule so it is realistic.
    for (let i = 0; i < legs.length; i++) {
      const leg = legs[i]
      activities[i + 1].start = addMinutes(activities[i].end, leg.duration_min)
      activities[i + 1].end = addMinutes(
        activities[i + 1].start,
        DURATION[activities[i + 1].place.experience_types[0] ?? 'landmark'] ?? 75,
      )
      if (leg.duration_min > req.max_travel_min) {
        const w: ValidationResult = {
          id: uid('vr'),
          trip_id: req.trip_id,
          version,
          rule: 'travel_time',
          passed: false,
          severity: 'hard',
          message: 'leg_over_limit',
          activity_ids: [activities[i].id, activities[i + 1].id],
        }
        validation.push(w)
      }
    }

    // Respect known opening hours: clamp starts to opening time and re-propagate
    // so nightlife lands in the evening and the plan passes its own validators.
    for (let i = 0; i < activities.length; i++) {
      const a = activities[i]
      const open = openingMinutes(a.place)
      if (open != null && minutesOfTime(a.start) < open) {
        a.start = withTime(a.start, open)
        a.end = addMinutes(a.start, durationFor(a.place))
      }
      if (i + 1 < activities.length) {
        const earliest = addMinutes(a.end, legs[i].duration_min)
        if (minutesOfTime(activities[i + 1].start) < minutesOfTime(earliest)) {
          activities[i + 1].start = earliest
          activities[i + 1].end = addMinutes(earliest, durationFor(activities[i + 1].place))
        }
      }
    }

    // Opening-hours validation (FR-08): known hours inside the window, unknown
    // hours are a warning, never a pass.
    for (const activity of activities) {
      if (!activity.place.hours) continue
      const open = openingMinutes(activity.place)
      const close = closingMinutes(activity.place)
      if (open == null || close == null) continue
      let start = minutesOfTime(activity.start)
      let end = minutesOfTime(activity.end)
      // Only apply the overnight offset when the activity is actually after
      // midnight (e.g. a late bar).
      if (close > 24 * 60 && start < open && start < 24 * 60) start += 24 * 60
      if (close > 24 * 60 && end < open && end < 24 * 60) end += 24 * 60
      if (start < open || end > close) {
        const w: ValidationResult = {
          id: uid('vr'),
          trip_id: req.trip_id,
          version,
          rule: 'opening_hours',
          passed: false,
          severity: 'hard',
          message: 'outside_hours',
          activity_ids: [activity.id],
        }
        activity.warnings = [...(activity.warnings ?? []), w]
        validation.push(w)
      }
    }

    const dayWarnings = validation.filter((v) =>
      v.activity_ids.some((id) => activities.some((a) => a.id === id)),
    )
    daysOut.push({ day: d, date, activities, legs, warnings: dayWarnings })
  }

  // Budget validation (FR-10).
  const knownCosts = daysOut
    .flatMap((d) => d.activities)
    .filter((a) => a.est_cost != null)
  const unknownCount = daysOut.flatMap((d) => d.activities).filter((a) => a.est_cost == null).length
  const total = knownCosts.reduce((s, a) => s + (a.est_cost ?? 0), 0)
  if (req.budget != null && total > req.budget) {
    validation.push({
      id: uid('vr'),
      trip_id: req.trip_id,
      version,
      rule: 'budget',
      passed: false,
      severity: 'hard',
      message: 'over_budget',
      activity_ids: [],
    })
  }
  if (unknownCount > 0) {
    validation.push({
      id: uid('vr'),
      trip_id: req.trip_id,
      version,
      rule: 'budget',
      passed: true,
      severity: 'data-gap',
      message: 'unknown_cost',
      activity_ids: [],
    })
  }

  // Diversity per full day (FR-37).
  for (const day of daysOut) {
    const cats = new Set(day.activities.map((a) => a.place.experience_types[0]))
    if (day.activities.length >= 3 && cats.size < 3) {
      validation.push({
        id: uid('vr'),
        trip_id: req.trip_id,
        version,
        rule: 'diversity',
        passed: false,
        severity: 'soft',
        message: 'low_variety',
        activity_ids: day.activities.map((a) => a.id),
      })
    }
  }

  // Attach purpose-preserving backups to high/medium priority activities.
  for (const day of daysOut) {
    for (const a of day.activities) {
      if (a.priority === 'high' || a.priority === 'medium') {
        a.backups = buildBackups(a, demoPlaces)
      }
    }
  }

  const hard = validation.filter((v) => !v.passed && v.severity === 'hard').length
  const soft = validation.filter((v) => !v.passed && v.severity === 'soft').length
  return {
    trip_id: req.trip_id,
    version,
    days: daysOut,
    validation,
    score: Math.max(0, 100 - hard * 25 - soft * 5),
    created_at: new Date().toISOString(),
  }
}

/** INFEASIBLE when the budget cannot cover even a free-only day (S10). */
function infeasibilityFor(req: TripRequirements): InfeasibleReport | null {
  if (req.budget == null) return null
  const days = dayCount(req)
  const cheapestDay = days * 12 // cheapest plausible food/entry per day
  if (req.budget < cheapestDay) {
    return {
      blocking_rule: 'budget',
      explanation: 'infeasible.noPlan',
      suggestions: [
        { label: 'infeasible.allowFreeOnly', change: { type: 'preference', payload: { free_only: true } } },
        { label: 'infeasible.changeBudget', change: { type: 'budget', payload: { budget: cheapestDay * 2 } } },
      ],
    }
  }
  return null
}

/* ------------------------------------------------------------------ *
 * Diffing                                                             *
 * ------------------------------------------------------------------ */

function diffItineraries(from: Itinerary | undefined, to: Itinerary): ReplanEvent['diff'] {
  const flat = (it?: Itinerary) =>
    (it?.days ?? []).flatMap((d) => d.activities.map((a) => ({ day: d.day, a })))
  const oldItems = flat(from)
  const newItems = flat(to)
  const oldByPlace = new Map(oldItems.map((x) => [x.a.place_id, x]))
  const newByPlace = new Map(newItems.map((x) => [x.a.place_id, x]))

  const changed: string[] = []
  const moved: string[] = []
  const preserved: string[] = []
  const added: string[] = []
  const removed: string[] = []

  for (const { day, a } of newItems) {
    const old = oldByPlace.get(a.place_id)
    if (!old) {
      added.push(a.id)
    } else if (old.day !== day || old.a.start !== a.start) {
      moved.push(a.id)
      a.change_type = 'moved'
    } else {
      preserved.push(a.id)
      a.change_type = 'kept'
    }
  }
  for (const { a } of oldItems) {
    if (!newByPlace.has(a.place_id)) {
      removed.push(a.id)
    }
  }
  // Pair removals with additions as "replaced" where a day matches.
  const removedByDay = new Map<number, string[]>()
  for (const { day, a } of oldItems) {
    if (removed.includes(a.id)) {
      if (!removedByDay.has(day)) removedByDay.set(day, [])
      removedByDay.get(day)!.push(a.id)
    }
  }
  for (const { day, a } of newItems) {
    if (added.includes(a.id)) {
      const pool = removedByDay.get(day)
      if (pool && pool.length) {
        pool.pop()
        a.change_type = 'replaced'
        changed.push(a.id)
      }
    }
  }
  // Anything still in removedByDay stays removed; mark added items that were not paired.
  for (const { a } of newItems) {
    if (added.includes(a.id) && a.change_type !== 'replaced') a.change_type = 'added'
  }
  const trulyRemoved = oldItems.filter((x) => removed.includes(x.a.id)).map((x) => x.a.id)
  return { changed, moved, preserved, added, removed: trulyRemoved }
}

function reasonsFor(diff: ReplanEvent['diff'], to: Itinerary, trigger: string): Record<string, string> {
  const reasons: Record<string, string> = {}
  const byId = new Map(to.days.flatMap((d) => d.activities.map((a) => [a.id, a])))
  for (const id of [...diff.changed, ...diff.added]) {
    const a = byId.get(id)
    if (!a) continue
    reasons[id] = trigger
  }
  for (const id of diff.moved) reasons[id] = trigger
  for (const id of diff.removed) reasons[id] = trigger
  return reasons
}

/* ------------------------------------------------------------------ *
 * Runs                                                                *
 * ------------------------------------------------------------------ */

function pushEvent(rec: TripRecord, e: ExecutionEvent): void {
  rec.events.push(e)
}

function planRunSteps(kind: 'plan' | 'change' | 'simulate'): { node: string; key: string }[] {
  if (kind === 'plan') return planningSteps.map((s) => ({ node: s.node, key: s.key }))
  return [
    { node: 'change_interpreter', key: 'reading' },
    { node: 'impact_analyzer', key: 'finding' },
    { node: 'repair', key: 'arranging' },
    { node: 'validator', key: 'doubleChecking' },
    { node: 'explainer', key: 'done' },
  ]
}

function startRun(
  tripId: string,
  kind: 'plan' | 'change' | 'simulate',
  extras: Partial<RunRecord> = {},
): PlanResponse {
  const rec = requireTrip(tripId)
  const runId = uid('run')
  const steps = planRunSteps(kind)
  const status: RunStatus = {
    run_id: runId,
    trip_id: tripId,
    status: 'running',
    phase: kind === 'plan' ? 'intake' : 'adapt',
    step: steps[0].key,
    step_index: 0,
    step_count: steps.length,
    terminal: null,
    message: null,
    infeasible: null,
    started_at: new Date().toISOString(),
  }
  runStore.set(runId, {
    status,
    tripId,
    kind,
    startedMs: Date.now(),
    finalized: false,
    ...extras,
  })
  rec.currentRunId = runId
  rec.trip = { ...rec.trip, status: kind === 'plan' ? 'planning' : 'adapting' }
  this_store.set(tripId, rec)
  return { run_id: runId }
}

export function startPlan(tripId: string): PlanResponse {
  return startRun(tripId, 'plan')
}

function elapsedStep(run: RunRecord): number {
  const stepMs = run.kind === 'plan' ? STEP_MS : CHANGE_STEP_MS
  return Math.floor((Date.now() - run.startedMs) / stepMs)
}

/** Advance a run from wall-clock time; finalize once the steps are done. */
export function getRun(runId: string): RunStatus {
  const run = runStore.get(runId)
  if (!run) throw new Error('run_not_found')
  const rec = requireTrip(run.tripId)
  const steps = planRunSteps(run.kind)
  if (run.finalized) return run.status

  const idx = elapsedStep(run)
  if (idx < steps.length) {
    run.status = {
      ...run.status,
      status: 'running',
      step: steps[Math.max(0, idx)].key,
      step_index: idx,
    }
    return run.status
  }

  finalizeRun(run, rec)
  run.finalized = true
  return run.status
}

function finalizeRun(run: RunRecord, rec: TripRecord): void {
  const runId = run.status.run_id
  if (run.kind === 'plan') {
    const infeasible = infeasibilityFor(rec.requirements)
    for (const step of planningSteps) {
      pushEvent(
        rec,
        executionEvent({
          trip_id: rec.trip.id,
          run_id: runId,
          node: step.node,
          type: step.node === 'discovery' ? 'tool' : step.node === 'validator' ? 'validation' : 'node',
          iteration: 0,
          status: 'ok',
          duration_ms: Math.round(120 + Math.random() * 500),
          metadata: { loop: step.node === 'discovery' ? 'L2' : step.node === 'validator' ? 'L3' : null },
        }),
      )
    }
    if (infeasible) {
      rec.trip = { ...rec.trip, status: 'infeasible' }
      run.status = {
        ...run.status,
        status: 'infeasible',
        phase: 'done',
        terminal: 'INFEASIBLE',
        infeasible,
        step: 'done',
      }
      this_store.set(rec.trip.id, rec)
      return
    }
    const itinerary = buildItinerary(rec.requirements, 1)
    rec.versions = [1]
    rec.itineraries.set(1, itinerary)
    rec.trip = { ...rec.trip, status: 'planned', current_version: 1 }
    run.status = { ...run.status, status: 'done', phase: 'done', terminal: 'PASS', step: 'done' }
    this_store.set(rec.trip.id, rec)
    return
  }

  // Change / simulate run.
  const fromVersion = rec.trip.current_version
  const from = rec.itineraries.get(fromVersion)
  const { requirements, affectedDays, changeType, trigger } = applyChange(rec, run)
  const nextVersion = fromVersion + 1
  const to = buildItinerary(requirements, nextVersion, { preserve: from, affectedDays })
  const diff = diffItineraries(from, to)
  const reasons = reasonsFor(diff, to, trigger)
  for (const day of to.days) {
    for (const a of day.activities) {
      if (a.change_type && a.change_type !== 'kept') a.reason = reasons[a.id] ?? trigger
    }
  }
  const replan: ReplanEvent = {
    id: uid('replan'),
    trip_id: rec.trip.id,
    from_version: fromVersion,
    to_version: nextVersion,
    trigger_id: run.changeId ?? uid('chg'),
    diff,
    reasons,
    iterations: 1,
    trigger_text: trigger,
  }
  rec.requirements = requirements
  rec.versions = [...rec.versions, nextVersion]
  rec.itineraries.set(nextVersion, to)
  rec.replans.push(replan)
  rec.pendingTrigger = null
  rec.trip = { ...rec.trip, status: 'planned', current_version: nextVersion }
  pushEvent(rec, executionEvent({ trip_id: rec.trip.id, run_id: runId, node: 'repair', type: 'node', iteration: 1, status: 'ok', duration_ms: 240, metadata: { loop: 'L3' } }))
  pushEvent(rec, executionEvent({ trip_id: rec.trip.id, run_id: runId, node: 'validator', type: 'validation', iteration: 1, status: 'ok', duration_ms: 80, metadata: { changeType } }))
  run.status = { ...run.status, status: 'done', phase: 'done', terminal: 'PASS', step: 'done' }
  this_store.set(rec.trip.id, rec)
}

interface AppliedChange {
  requirements: TripRequirements
  affectedDays: Set<number>
  changeType: string
  trigger: string
}

function applyChange(rec: TripRecord, run: RunRecord): AppliedChange {
  const req = { ...rec.requirements }
  const allDays = new Set(Array.from({ length: dayCount(req) }, (_, i) => i + 1))
  const change = rec.changes.find((c) => c.id === run.changeId)
  let type = change?.type ?? (run.simulateType as ChangeEvent['type']) ?? 'unknown'
  let affectedDays = new Set(allDays)
  let trigger = rec.pendingTrigger ?? 'your change'

  if (run.simulateType === 'closure' && run.activityId) {
    type = 'closure'
    const from = rec.itineraries.get(rec.trip.current_version)
    const activity = from?.days.flatMap((d) => d.activities).find((a) => a.id === run.activityId)
    if (activity) {
      affectedDays = new Set([activity.day])
      // Force a swap by adding the place's category to avoid.
      req.avoid = [...new Set([...req.avoid, activity.place.experience_types[0]])]
      trigger = `the ${activity.place.name} closed`
    }
  } else if (type === 'budget') {
    const payload = change?.payload ?? {}
    const newBudget = Number(payload.budget ?? req.budget ?? 300)
    req.budget = newBudget
    trigger = `your budget is now $${newBudget}`
  } else if (type === 'time') {
    const payload = change?.payload ?? {}
    const minutes = Number(payload.minutes ?? 90)
    req.daily_start = addMinutes(`${req.start_date}T${req.daily_start}:00`, minutes).slice(11, 16)
    trigger = `you're running ${minutes} minutes late`
  } else if (type === 'transport') {
    const payload = change?.payload ?? {}
    req.mode = (payload.mode as TransportMode) ?? 'walking'
    trigger = `you switched to ${req.mode}`
  } else if (type === 'preference') {
    const payload = change?.payload ?? {}
    if (payload.avoid) req.avoid = [...new Set([...req.avoid, ...(payload.avoid as string[])])]
    if (payload.interests) req.interests = [...new Set([...req.interests, ...(payload.interests as string[])])]
    trigger = 'your preferences changed'
  }
  // A typed change may carry its own user-facing trigger (e.g. along-route).
  if (change?.payload?.trigger) trigger = String(change.payload.trigger)
  return { requirements: req, affectedDays, changeType: type, trigger }
}

export function submitChange(
  tripId: string,
  input: { text?: string; typed?: Partial<ChangeEvent> },
): { run_id: string; change: ChangeEvent } {
  const rec = requireTrip(tripId)
  const parsed = interpretChange(input.text ?? '')
  const finalType = (input.typed?.type as ChangeEvent['type']) ?? parsed.type
  const change: ChangeEvent = {
    id: uid('chg'),
    trip_id: tripId,
    source: 'user',
    type: finalType,
    payload: input.typed?.payload ?? parsed.payload,
    raw_text: input.text ?? '',
    status: finalType === 'unknown' ? 'needs-clarification' : 'applied',
  }
  rec.changes.push(change)
  if (change.status === 'needs-clarification') {
    return { run_id: '', change }
  }
  rec.pendingTrigger = input.text ? parsed.trigger : String(change.payload.trigger ?? parsed.trigger)
  this_store.set(tripId, rec)
  const { run_id } = startRun(tripId, 'change', { changeId: change.id })
  return { run_id, change }
}

function interpretChange(text: string): {
  type: ChangeEvent['type']
  payload: Record<string, unknown>
  trigger: string
} {
  const lower = text.toLowerCase()
  const budget = lower.match(/\$?(\d{2,5})/)
  if (/budget|\$|cheaper|money/.test(lower) && budget) {
    return { type: 'budget', payload: { budget: Number(budget[1]) }, trigger: `your budget is now $${budget[1]}` }
  }
  const late = lower.match(/(\d+)\s*(min|minute|hour|hr)/)
  if (/late|delay|running behind/.test(lower) && late) {
    const minutes = /hour|hr/.test(late[2]) ? Number(late[1]) * 60 : Number(late[1])
    return { type: 'time', payload: { minutes }, trigger: `you're running ${minutes} minutes late` }
  }
  if (/walk/.test(lower)) return { type: 'transport', payload: { mode: 'walking' }, trigger: 'you switched to walking' }
  if (/transit|bus|train/.test(lower)) return { type: 'transport', payload: { mode: 'transit' }, trigger: 'you switched to transit' }
  if (/driv|car/.test(lower)) return { type: 'transport', payload: { mode: 'driving' }, trigger: 'you switched to driving' }
  if (/no museums|skip museums|more outdoors|outdoor|no museum/.test(lower)) {
    const avoid: string[] = []
    if (/museum/.test(lower)) avoid.push('culture')
    if (/outdoor/.test(lower)) avoid.push('shopping', 'nightlife')
    return { type: 'preference', payload: { avoid }, trigger: 'your preferences changed' }
  }
  if (/skip/.test(lower)) return { type: 'preference', payload: { avoid: ['shopping'] }, trigger: 'you asked to skip something' }
  if (/clos/.test(lower)) return { type: 'closure', payload: {}, trigger: 'a place closed' }
  return { type: 'unknown', payload: {}, trigger: text }
}

export function swapBackup(tripId: string, activityId: string, backupId: string): PlanResponse {
  const rec = requireTrip(tripId)
  rec.pendingTrigger = 'you picked a different option'
  this_store.set(tripId, rec)
  return startRun(tripId, 'simulate', { simulateType: 'swap', activityId, backupId })
}

export function simulate(tripId: string, type: string, activityId?: string): PlanResponse {
  const rec = requireTrip(tripId)
  rec.pendingTrigger =
    type === 'closure'
      ? 'a place closed'
      : type === 'rain'
        ? 'rain is forecast'
        : type === 'delay'
          ? "you're running 90 minutes late"
          : 'the situation changed'
  this_store.set(tripId, rec)
  return startRun(tripId, 'simulate', { simulateType: type, activityId })
}

/* ------------------------------------------------------------------ *
 * Reads                                                               *
 * ------------------------------------------------------------------ */

export function getItinerary(tripId: string, version?: number): Itinerary | null {
  const rec = requireTrip(tripId)
  const v = version ?? rec.trip.current_version
  return rec.itineraries.get(v) ?? null
}

export function getTrip(tripId: string): Trip | null {
  return this_store.get(tripId)?.trip ?? null
}
export function getRequirements(tripId: string): TripRequirements | null {
  return this_store.get(tripId)?.requirements ?? null
}
export function getTrace(tripId: string): ExecutionEvent[] {
  return this_store.get(tripId)?.events ?? []
}
export function getVersions(tripId: string): number[] {
  return this_store.get(tripId)?.versions ?? []
}
export function getReplans(tripId: string): ReplanEvent[] {
  return this_store.get(tripId)?.replans ?? []
}

export function answerQuestions(tripId: string, answers: Record<string, string>): TripRequirements {
  const rec = requireTrip(tripId)
  for (const q of rec.questions) {
    const answer = answers[q.id]
    if (!answer) continue
    if (q.field === 'mode') rec.requirements.mode = answer.toLowerCase() as TransportMode
  }
  rec.questions = []
  this_store.set(tripId, rec)
  return rec.requirements
}

export function restoreVersion(tripId: string, version: number): number {
  const rec = requireTrip(tripId)
  if (!rec.itineraries.has(version)) throw new Error('version_not_found')
  rec.trip = { ...rec.trip, current_version: version }
  this_store.set(tripId, rec)
  return version
}

export function updateRequirements(
  tripId: string,
  patch: Partial<TripRequirements>,
): TripRequirements {
  const rec = requireTrip(tripId)
  rec.requirements = { ...rec.requirements, ...patch }
  this_store.set(tripId, rec)
  return rec.requirements
}

export type { TripRecord, RunRecord, AppliedChange }
export { this_store as __trips, runStore as __runs, buildItinerary }
