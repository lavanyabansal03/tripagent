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
}

const state = $state({ ...initial })

function delay(ms: number) {
  return new Promise<void>((resolve) => setTimeout(resolve, ms))
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
  },

  async createTrip(input: TripFormInput) {
    state.busy = true
    state.error = null
    try {
      const { trip, requirements } = await api.createTrip(input)
      state.trip = trip
      state.requirements = requirements
      state.itinerary = null
      state.activeDay = 1
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
    state.error = null
    state.infeasible = null
    try {
      const { run_id } = await api.plan(tripId)
      state.route = { name: 'planning', tripId, runId: run_id, needsClarify: false }
      await store.pollRun(tripId, run_id)
    } catch (e) {
      state.error = e instanceof Error ? e.message : 'errors.unknown'
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
  },

  async submitChange(text: string) {
    if (!state.trip) return null
    state.busy = true
    state.error = null
    try {
      const { run_id, change } = await api.submitChange(state.trip.id, { text })
      if (!run_id) {
        state.error = 'adjust.needsClarification'
        return change
      }
      await store.pollRun(state.trip.id, run_id)
      state.showChangeSummary = true
      state.route = { name: 'itinerary' }
      return change
    } finally {
      state.busy = false
    }
  },

  async submitTypedChange(typed: Partial<ChangeEvent>) {
    if (!state.trip) return null
    state.busy = true
    try {
      const { run_id } = await api.submitChange(state.trip.id, { typed })
      if (run_id) {
        await store.pollRun(state.trip.id, run_id)
        state.showChangeSummary = true
        state.route = { name: 'itinerary' }
      }
    } finally {
      state.busy = false
    }
  },

  async swap(tripId: string, activityId: string, backupId: string) {
    const { run_id } = await api.swapBackup(tripId, activityId, backupId)
    await store.pollRun(tripId, run_id)
    state.showChangeSummary = true
  },

  async simulate(type: string, activityId?: string) {
    if (!state.trip) return
    const { run_id } = await api.simulate(state.trip.id, type, activityId)
    await store.pollRun(state.trip.id, run_id)
    state.showChangeSummary = true
  },

  async undo() {
    if (!state.trip || state.versions.length < 2) return
    const currentIndex = state.versions.indexOf(state.trip.current_version)
    const previous = state.versions[currentIndex - 1]
    if (previous == null) return
    await api.restoreVersion(state.trip.id, previous)
    await store.reload(state.trip.id)
    state.showChangeSummary = false
  },
}
