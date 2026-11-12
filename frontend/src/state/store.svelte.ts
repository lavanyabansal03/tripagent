/**
 * Central app state. Svelte 5 runes in a module singleton so any component can
 * import it without prop drilling.
 *
 * Runes live as `$state` fields of a single reactive object: assigning to a
 * field is always allowed, including from inside methods.
 */
import type {
  ChangeEvent,
  ExecutionEvent,
  InfeasibleReport,
  Itinerary,
  ReplanEvent,
  RunStatus,
  Trip,
  TripRequirements,
} from '../types'
import { api, mockEngine, type TripFormInput } from '../api/client'

export type Route =
  | { name: 'setup' }
  | { name: 'planning'; tripId: string; runId: string; needsClarify: boolean }
  | { name: 'itinerary' }

const initial = {
  trip: null as Trip | null,
  requirements: null as TripRequirements | null,
  itinerary: null as Itinerary | null,
  run: null as RunStatus | null,
  trace: [] as ExecutionEvent[],
  replans: [] as ReplanEvent[],
  versions: [] as number[],
  route: { name: 'setup' } as Route,
  error: null as string | null,
  busy: false,
  infeasible: null as InfeasibleReport | null,
  activeDay: 1,
  showChangeSummary: false,
  questionCount: 0,
  // The last trip form, so "Edit trip details" can bring it back filled in.
  lastForm: null as TripFormInput | null,
  // A5's question when a change was unclear ("Which place is closed: A or B?").
  clarifyQuestion: null as string | null,
  // The version before the current one, for the change summary (from the API).
  previousItinerary: null as Itinerary | null,
  // True from "Build my plan" until the plan is back. In live mode the request itself
  // takes the whole planning time, so this is what shows progress and blocks a 2nd click.
  planning: false,
  // Why the last Swap / Undo / Adjust trip / Simulate did not work (shown on the plan page).
  actionError: null as string | null,
}

const state = $state({ ...initial })

function delay(ms: number) {
  return new Promise<void>((resolve) => setTimeout(resolve, ms))
}

/** The text (or i18n key) of an error, for the screen. */
function messageOf(error: unknown, fallback: string): string {
  return error instanceof Error && error.message ? error.message : fallback
}

/**
 * Run one change to the plan (Adjust trip, Swap, Undo, Simulate). A failure never
 * escapes as an unhandled error: it becomes `actionError`, and the plan stays as it was.
 */
async function runChange<T>(work: () => Promise<T>): Promise<T | null> {
  state.busy = true
  state.actionError = null
  const runBefore = state.run
  try {
    const result = await work()
    // The request worked but this change's run failed (the backend kept the plan).
    // Only a NEW run counts: an older failed run must not come back after Undo.
    const run = state.run
    if (run && run !== runBefore && run.status === 'failed' && run.phase === 'adapt') {
      state.actionError = run.message || 'errors.changeFailed'
    }
    return result
  } catch (error) {
    const message = messageOf(error, 'errors.changeFailed')
    // The generic text talks about planning; for a change, say the plan is unchanged.
    state.actionError = message === 'errors.unknown' ? 'errors.changeFailed' : message
    return null
  } finally {
    state.busy = false
  }
}

/**
 * Keep the trip id in the address bar (?trip=...) so a page refresh can load the
 * same trip again instead of going back to an empty form. null removes it.
 */
export function rememberTripInUrl(tripId: string | null) {
  if (typeof window === 'undefined') return
  const url = new URL(window.location.href)
  if (tripId) url.searchParams.set('trip', tripId)
  else url.searchParams.delete('trip')
  window.history.replaceState(window.history.state, '', url)
}

/** The trip id from the address bar, if there is one. */
export function tripIdFromUrl(): string | null {
  if (typeof window === 'undefined') return null
  return new URL(window.location.href).searchParams.get('trip')
}

export const store = {
  get trip() {
    return state.trip
  },
  get requirements() {
    return state.requirements
  },
  get itinerary() {
    return state.itinerary
  },
  get run() {
    return state.run
  },
  get trace() {
    return state.trace
  },
  get replans() {
    return state.replans
  },
  get versions() {
    return state.versions
  },
  get route() {
    return state.route
  },
  get error() {
    return state.error
  },
  get busy() {
    return state.busy
  },
  get infeasible() {
    return state.infeasible
  },
  get activeDay() {
    return state.activeDay
  },
  get showChangeSummary() {
    return state.showChangeSummary
  },
  get planning() {
    return state.planning
  },
  get actionError() {
    return state.actionError
  },
  clearActionError() {
    state.actionError = null
  },

  setRoute(route: Route) {
    state.route = route
  },
  setActiveDay(day: number) {
    state.activeDay = day
  },
  setShowChangeSummary(value: boolean) {
    state.showChangeSummary = value
  },
  setError(message: string | null) {
    state.error = message
  },
  reset() {
    Object.assign(state, initial)
    rememberTripInUrl(null)
  },

  /**
   * Bring back a trip after a page refresh. Shows the plan if there is one, otherwise
   * the "Here's what we understood" page. Returns false (and clears the address bar)
   * when the backend no longer knows the trip.
   */
  async restoreTrip(tripId: string): Promise<boolean> {
    try {
      const trip = await api.getTrip(tripId)
      if (!trip) throw new Error('Trip not found')
      state.trip = trip
      state.requirements = await api.getRequirements(tripId)
    } catch {
      rememberTripInUrl(null)
      return false
    }
    try {
      await store.reload(tripId)
    } catch {
      // No plan yet: the itinerary call fails, which is fine.
    }
    state.activeDay = 1
    state.route = state.itinerary
      ? { name: 'itinerary' }
      : { name: 'planning', tripId, runId: '', needsClarify: false }
    return true
  },

  get lastForm() {
    return state.lastForm
  },

  /** Back to the form with the traveller's last answers ("Edit trip details"). */
  editTrip() {
    state.error = null
    state.route = { name: 'setup' }
  },

  async createTrip(input: TripFormInput) {
    state.busy = true
    state.error = null
    state.lastForm = { ...input, interests: [...input.interests], avoid: [...input.avoid] }
    try {
      const { trip, requirements } = await api.createTrip(input)
      state.trip = trip
      state.requirements = requirements
      state.itinerary = null
      state.activeDay = 1
      rememberTripInUrl(trip.id)
      const rec = mockEngine.getTripRecord(trip.id)
      const hasQuestions = Boolean(rec && rec.questions.length)
      state.questionCount = rec?.questions.length ?? 0
      state.route = {
        name: 'planning',
        tripId: trip.id,
        runId: '',
        needsClarify: hasQuestions,
      }
      return trip
    } catch (e) {
      state.error = e instanceof Error ? e.message : 'errors.unknown'
      throw e
    } finally {
      state.busy = false
    }
  },

  async submitAnswers(tripId: string, answers: Record<string, string>) {
    state.busy = true
    try {
      state.requirements = await api.answerQuestions(tripId, answers)
      state.route = { name: 'planning', tripId, runId: '', needsClarify: false }
    } catch (e) {
      state.error = e instanceof Error ? e.message : 'errors.unknown'
    } finally {
      state.busy = false
    }
  },

  async startPlanning(tripId: string) {
    if (state.planning) return // a second click while the first plan is still running
    state.planning = true
    state.error = null
    state.infeasible = null
    state.run = null // forget an earlier failed run, so progress starts fresh
    try {
      const { run_id } = await api.plan(tripId)
      state.route = { name: 'planning', tripId, runId: run_id, needsClarify: false }
      await store.pollRun(tripId, run_id)
    } catch (e) {
      state.error = messageOf(e, 'errors.unknown')
    } finally {
      state.planning = false
    }
  },

  async pollRun(tripId: string, runId: string) {
    // Polling, ADR-006: once per second while the run is active.
    for (;;) {
      const status = await api.getRun(runId)
      state.run = status
      if (status.status === 'done') break
      if (status.status === 'infeasible') {
        state.infeasible = status.infeasible ?? null
        break
      }
      if (status.status === 'failed') {
        state.error = status.message ?? 'errors.unknown'
        // Show why in the "couldn't plan" notice (for example "We couldn't find any places").
        state.infeasible = status.infeasible ?? null
        break
      }
      if (status.status === 'needs-user') break
      await delay(120)
    }
    await store.reload(tripId)
    if (state.itinerary) state.route = { name: 'itinerary' }
  },

  async reload(tripId: string) {
    const [trip, requirements, itinerary, trace, replans, versions] = await Promise.all([
      api.getTrip(tripId),
      api.getRequirements(tripId),
      api.getItinerary(tripId),
      api.getTrace(tripId),
      api.getReplans(tripId),
      api.getVersions(tripId),
    ])
    state.trip = trip
    state.requirements = requirements
    state.itinerary = itinerary
    state.trace = trace
    state.replans = replans
    state.versions = versions
    const index = trip ? versions.indexOf(trip.current_version) : -1
    const previous = index > 0 ? versions[index - 1] : null
    state.previousItinerary = previous ? await api.getItinerary(tripId, previous) : null
  },

  get clarifyQuestion() {
    return state.clarifyQuestion
  },
  get previousItinerary() {
    return state.previousItinerary
  },
  clearQuestion() {
    state.clarifyQuestion = null
  },

  async submitChange(text: string) {
    const trip = state.trip
    if (!trip) return null
    state.clarifyQuestion = null
    return runChange(async () => {
      const { run_id, change } = await api.submitChange(trip.id, {
        text,
        day: state.activeDay,
      })
      if (!run_id) {
        // A5 needs one detail; the Adjust dialog shows its question.
        state.clarifyQuestion = String(change?.payload?.question ?? '') || 'adjust.needsClarification'
        return change
      }
      await store.pollRun(trip.id, run_id)
      state.showChangeSummary = true
      state.route = { name: 'itinerary' }
      return change
    })
  },

  async submitTypedChange(typed: Partial<ChangeEvent>) {
    const trip = state.trip
    if (!trip) return null
    state.clarifyQuestion = null
    await runChange(async () => {
      const { run_id, change } = await api.submitChange(trip.id, {
        typed,
        day: state.activeDay,
      })
      if (!run_id) {
        state.clarifyQuestion = String(change?.payload?.question ?? '') || 'adjust.needsClarification'
        return
      }
      await store.pollRun(trip.id, run_id)
      state.showChangeSummary = true
      state.route = { name: 'itinerary' }
    })
  },

  async swap(tripId: string, activityId: string, backupId: string) {
    await runChange(async () => {
      const { run_id } = await api.swapBackup(tripId, activityId, backupId)
      await store.pollRun(tripId, run_id)
      state.showChangeSummary = true
    })
  },

  async simulate(type: string, activityId?: string) {
    const trip = state.trip
    if (!trip) return
    await runChange(async () => {
      const { run_id } = await api.simulate(trip.id, type, activityId)
      await store.pollRun(trip.id, run_id)
      state.showChangeSummary = true
    })
  },

  async undo() {
    const trip = state.trip
    if (!trip || state.versions.length < 2) return
    const currentIndex = state.versions.indexOf(trip.current_version)
    const previous = state.versions[currentIndex - 1]
    if (previous == null) return
    await runChange(async () => {
      await api.restoreVersion(trip.id, previous)
      await store.reload(trip.id)
      state.showChangeSummary = false
    })
  },
}
