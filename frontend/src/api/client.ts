/**
 * API client. One interface, two transports:
 *  - DEMO_MODE -> the in-memory mock engine (FR-55, deterministic, offline)
 *  - live      -> the FastAPI backend at /api
 * Components never know which is active.
 */
import type {
  Activity,
  ChangeEvent,
  CreateTripResponse,
  ExecutionEvent,
  Itinerary,
  PlanResponse,
  ReplanEvent,
  RunStatus,
  Trip,
  TripRequirements,
} from '../types'
import type { TripFormInput } from './mock/engine'
import * as mock from './mock/engine'

export const DEMO_MODE = import.meta.env.VITE_DEMO_MODE !== 'false'

const BASE = '/api'

export interface HealthStatus {
  status: string
  demo_mode: boolean
}

/**
 * Probe the backend's `/api/health` (the contract already in the repo).
 * Used to show connection state; the app itself still runs on fixtures in
 * DEMO_MODE, which is the default while the trip endpoints are being built.
 */
export async function checkHealth(): Promise<HealthStatus | null> {
  try {
    const res = await fetch(`${BASE}/health`)
    if (!res.ok) return null
    return (await res.json()) as HealthStatus
  } catch {
    return null
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  })
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(text || `Request failed: ${res.status}`)
  }
  if (res.status === 204) return undefined as T
  return (await res.json()) as T
}

export const api = {
  createTrip(input: TripFormInput): Promise<CreateTripResponse> {
    if (DEMO_MODE) return Promise.resolve(mock.createTrip(input))
    return request<CreateTripResponse>('/trips', {
      method: 'POST',
      body: JSON.stringify({ ...input, free_text: input.free_text }),
    })
  },

  answerQuestions(tripId: string, answers: Record<string, string>): Promise<TripRequirements> {
    if (DEMO_MODE) return Promise.resolve(mock.answerQuestions(tripId, answers))
    return request<TripRequirements>(`/trips/${tripId}/answers`, {
      method: 'POST',
      body: JSON.stringify({ answers }),
    })
  },

  plan(tripId: string): Promise<PlanResponse> {
    if (DEMO_MODE) return Promise.resolve(mock.startPlan(tripId))
    return request<PlanResponse>(`/trips/${tripId}/plan`, { method: 'POST' })
  },

  getRun(runId: string): Promise<RunStatus> {
    if (DEMO_MODE) return Promise.resolve(mock.getRun(runId))
    return request<RunStatus>(`/runs/${runId}`)
  },

  getItinerary(tripId: string, version?: number): Promise<Itinerary | null> {
    if (DEMO_MODE) return Promise.resolve(mock.getItinerary(tripId, version))
    const q = version ? `?version=${version}` : ''
    return request<Itinerary | null>(`/trips/${tripId}/itinerary${q}`)
  },

  getTrip(tripId: string): Promise<Trip | null> {
    if (DEMO_MODE) return Promise.resolve(mock.getTrip(tripId))
    return request<Trip | null>(`/trips/${tripId}`)
  },

  getRequirements(tripId: string): Promise<TripRequirements | null> {
    if (DEMO_MODE) return Promise.resolve(mock.getRequirements(tripId))
    return request<TripRequirements | null>(`/trips/${tripId}/requirements`)
  },

  submitChange(
    tripId: string,
    input: { text?: string; typed?: Partial<ChangeEvent> },
  ): Promise<{ run_id: string; change: ChangeEvent }> {
    if (DEMO_MODE) return Promise.resolve(mock.submitChange(tripId, input))
    return request<{ run_id: string; change: ChangeEvent }>(`/trips/${tripId}/changes`, {
      method: 'POST',
      body: JSON.stringify(input),
    })
  },

  swapBackup(tripId: string, activityId: string, backupId: string): Promise<PlanResponse> {
    if (DEMO_MODE) return Promise.resolve(mock.swapBackup(tripId, activityId, backupId))
    return request<PlanResponse>(`/trips/${tripId}/activities/${activityId}/swap`, {
      method: 'POST',
      body: JSON.stringify({ backup_id: backupId }),
    })
  },

  restoreVersion(tripId: string, version: number): Promise<{ version: number }> {
    if (DEMO_MODE) return Promise.resolve({ version: mock.restoreVersion(tripId, version) })
    return request<{ version: number }>(`/trips/${tripId}/versions/${version}/restore`, {
      method: 'POST',
    })
  },

  simulate(tripId: string, type: string, activityId?: string): Promise<PlanResponse> {
    if (DEMO_MODE) return Promise.resolve(mock.simulate(tripId, type, activityId))
    return request<PlanResponse>(`/trips/${tripId}/simulate`, {
      method: 'POST',
      body: JSON.stringify({ type, activity_id: activityId }),
    })
  },

  getTrace(tripId: string): Promise<ExecutionEvent[]> {
    if (DEMO_MODE) return Promise.resolve(mock.getTrace(tripId))
    return request<ExecutionEvent[]>(`/trips/${tripId}/trace`)
  },

  getVersions(tripId: string): Promise<number[]> {
    if (DEMO_MODE) return Promise.resolve(mock.getVersions(tripId))
    return request<number[]>(`/trips/${tripId}/versions`)
  },

  getReplans(tripId: string): Promise<ReplanEvent[]> {
    if (DEMO_MODE) return Promise.resolve(mock.getReplans(tripId))
    return request<ReplanEvent[]>(`/trips/${tripId}/replans`)
  },
}

/** Convenience for tests and the route store. */
export const __mock = mock
export type { TripFormInput }
export { mock as mockEngine }
export type { Activity }
