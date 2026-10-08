/**
 * Domain types for the TripAgent frontend.
 *
 * Mirrors Architecture & Agent Design, Section 9.1 (entities) and the REST
 * contracts in Section 9.2. Shared model changes require two reviewers, so this
 * file is treated as a contract: keep it in lockstep with the backend Pydantic
 * models.
 */

export type Provenance = 'explicit' | 'inferred' | 'default'

export type Severity = 'hard' | 'soft' | 'data-gap'

export type ChangeType = 'added' | 'replaced' | 'moved' | 'removed' | 'kept'

export type ActivityStatus = 'planned' | 'done' | 'locked' | 'cancelled'

export type Priority = 'high' | 'medium' | 'low'

export type TransportMode = 'walking' | 'transit' | 'driving' | 'cycling'

export type Pace = 'relaxed' | 'moderate' | 'packed'

export type BudgetStrictness = 'strict' | 'flexible'

/** Eight experience categories share a colour-blind-safe palette + icon. */
export type ExperienceCategory =
  | 'food'
  | 'cafe'
  | 'nature'
  | 'culture'
  | 'shopping'
  | 'nightlife'
  | 'event'
  | 'landmark'

export type LocalSignal = 'tourist' | 'local' | 'hidden' | 'unknown'

export type CostBasis = 'known' | 'price_level' | 'free' | 'unknown'

export type TerminalState = 'PASS' | 'INFEASIBLE' | 'NEEDS_USER' | 'ERROR'

export interface LatLng {
  lat: number
  lng: number
}

export interface Trip {
  id: string
  destination: string
  start_date: string
  end_date: string
  status: 'draft' | 'planning' | 'planned' | 'adapting' | 'infeasible' | 'error'
  current_version: number
  created_at: string
}

export interface TripRequirements {
  trip_id: string
  version: number
  destination: string
  start_date: string
  end_date: string
  budget: number | null
  budget_strictness: BudgetStrictness
  mode: TransportMode
  pace: Pace
  interests: string[]
  avoid: string[]
  tourist_local_ratio: number // 0 = famous sights, 100 = local favourites
  max_travel_min: number
  daily_start: string // "09:00"
  daily_end: string // "20:00"
  dietary: string[]
  accessibility: string[]
  free_text: string
  provenance: Record<string, Provenance>
}

export interface Place {
  id: string
  sources: Array<'mapbox' | 'foursquare' | 'seed'>
  provider_ids: Record<string, string>
  name: string
  categories: string[]
  experience_types: ExperienceCategory[]
  lat: number
  lng: number
  address: string
  price_level?: 1 | 2 | 3 | 4 | null
  est_cost_low?: number | null
  est_cost_high?: number | null
  cost_basis: CostBasis
  hours?: string | null
  rating?: number | null
  review_count?: number | null
  popularity?: number | null
  local_signal: LocalSignal
  field_provenance: Record<string, Provenance>
  retrieved_at: string
  /** Free-text note from the provider; rendered as quoted data, never markup. */
  tip?: string | null
}

export interface EventItem {
  id: string
  provider: string
  name: string
  venue_place_id: string | null
  starts_at: string
  ends_at: string | null
  price: number | null
  url: string | null
  retrieved_at: string
}

export interface ItineraryVersion {
  trip_id: string
  version: number
  created_by: 'plan' | 'replan'
  parent_version: number | null
  score: number
  created_at: string
}

export interface Backup {
  activity_id: string
  place_id: string
  rank: number
  purpose_similarity: number
  cost_delta: number
  travel_delta_min: number
  validated_at: string
}

export interface Activity {
  id: string
  trip_id: string
  version: number
  day: number
  place_id: string
  start: string // ISO-ish "2026-10-12T11:00"
  end: string
  est_cost: number | null
  cost_basis: CostBasis
  priority: Priority
  purpose_tags: string[]
  status: ActivityStatus
  /** Populated by the API from the ReplanEvent diff; null on the initial plan. */
  change_type?: ChangeType | null
  reason?: string | null
  warnings?: ValidationResult[]
  backups?: Backup[]
  place: Place
}

export interface ValidationResult {
  id: string
  trip_id: string
  version: number
  rule: string
  passed: boolean
  severity: Severity
  message: string
  activity_ids: string[]
}

export interface ChangeEvent {
  id: string
  trip_id: string
  source: 'user' | 'environment' | 'simulated'
  type:
    | 'budget'
    | 'time'
    | 'preference'
    | 'transport'
    | 'closure'
    | 'weather'
    | 'unknown'
  payload: Record<string, unknown>
  raw_text: string
  status: 'received' | 'interpreting' | 'needs-clarification' | 'applied' | 'rejected'
}

export interface ReplanDiff {
  changed: string[]
  moved: string[]
  preserved: string[]
  added: string[]
  removed: string[]
}

export interface ReplanEvent {
  id: string
  trip_id: string
  from_version: number
  to_version: number
  trigger_id: string
  diff: ReplanDiff
  reasons: Record<string, string>
  iterations: number
  trigger_text: string
}

export interface ExecutionEvent {
  id: string
  trip_id: string
  run_id: string
  node: string
  type: 'node' | 'tool' | 'llm' | 'validation' | 'loop'
  iteration: number
  status: 'started' | 'ok' | 'failed' | 'degraded' | 'skipped'
  duration_ms: number
  metadata: Record<string, unknown>
  ts: string
}

export interface Question {
  id: string
  field: string
  text: string
  options?: string[]
}

export interface DayCluster {
  day: number
  place_ids: string[]
  centroid: LatLng
}

export interface RouteLeg {
  from_activity_id: string
  to_activity_id: string
  mode: TransportMode
  duration_min: number
  distance_km: number
  geometry: LatLng[]
  changed: boolean
}

export interface ItineraryDay {
  day: number
  date: string
  activities: Activity[]
  legs: RouteLeg[]
  warnings: ValidationResult[]
}

export interface Itinerary {
  trip_id: string
  version: number
  days: ItineraryDay[]
  validation: ValidationResult[]
  score: number
  created_at: string
}

/** GET /runs/{run_id} — polling shape (ADR-006). */
export interface RunStatus {
  run_id: string
  trip_id: string
  status: 'queued' | 'running' | 'done' | 'failed' | 'infeasible' | 'needs-user'
  phase: 'intake' | 'plan' | 'repair' | 'adapt' | 'done'
  step: string
  step_index: number
  step_count: number
  terminal: TerminalState | null
  message?: string | null
  infeasible?: InfeasibleReport | null
  started_at: string
}

export interface InfeasibleReport {
  blocking_rule: string
  explanation: string
  suggestions: Array<{ label: string; change: Partial<ChangeEvent> }>
}

/** POST /trips response. */
export interface CreateTripResponse {
  trip: Trip
  requirements: TripRequirements
  questions: Question[]
}

export interface PlanResponse {
  run_id: string
}
