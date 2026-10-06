# TripAgent: Architecture & Agent Design

_Agents, loops, state, maps, APIs and architecture decisions_

| Field | Value |
|---|---|
| Owner role | Engineering (Tech Lead) |
| Team | Product Owner / Engineering Manager; five engineers in role areas: Preferences, Validation, Agent Graph, Tools, Frontend & Maps |
| Version | 2.3 (October 5, 2026) |
| Status | Living document, updated each sprint |
| Method | System design framework + Architecture Decision Records |

## 1. Purpose and Reading Guide

This document is the engineering blueprint for TripAgent. It answers three questions for the team: **which agents exist and what each one is allowed to do**, **which loops drive the system and how every loop is guaranteed to stop**, and **how the pieces (API, graph, tools, validators, database, map, UI) connect**. It follows a standard system-design flow (requirements, high-level design, deep dive, reliability, trade-offs) and records the major decisions as Architecture Decision Records (ADRs) in Section 11.

| If you are... | Read first |
|---|---|
| New to the project | Sections 2, 3 and 5 (the agent roster and the loop catalogue) |
| Building a graph node | Sections 4, 5, 6 and 7 (state, loops, node contracts) |
| Building tools or map features | Sections 8 and 9 |
| Deploying or debugging | Sections 10 and 12 |
| Reviewing a design choice | Section 11 (ADRs) |

## 2. Design Principles

1. **The LLM proposes; deterministic code disposes.** Language models interpret text, choose among options and explain. Code does arithmetic, time math, constraint checks and routing decisions.
2. **Every loop has an exit.** Each loop has an iteration counter in state, a hard cap, a progress check and a named terminal state (PASS, INFEASIBLE, NEEDS_USER, ERROR).
3. **Repair, do not regenerate.** A change produces a patch to the current itinerary version, not a new trip.
4. **Tools are the source of truth for the world.** Places, travel times, hours and events come from providers with `source` and `retrieved_at`; the LLM never invents them.
5. **State is structured.** Nodes read and write typed Pydantic objects in a shared TripState. Prompts are rendered from state only at the moment of an LLM call.
6. **The map is a reasoning tool, not decoration.** Travel matrices, clustering, nearby search and route order feed planning and validation.
7. **Everything leaves a trace.** Every node run, tool call, validation result and replan writes an ExecutionEvent.
8. **Simple infrastructure.** One FastAPI service, one LangGraph workflow, one relational database. No queues, microservices or vector stores in the MVP.

## 3. The Agent Roster

In TripAgent the word "agent" means a graph node that uses an LLM to make a decision, often in combination with tools. Nodes that only run code are called **deterministic nodes**. Being explicit about the difference is the most important design decision in the project, because it tells each engineer where probabilistic behaviour is allowed.

| # | Component | Type | Responsibility | Owner (lead) |
|---|---|---|---|---|
| A1 | Intake Agent | LLM + schema | Turns the form plus the "Tell us more about your trip" text into TripRequirements. Marks each field as explicit, inferred or missing. Detects contradictions. | Preferences Eng. |
| A2 | Discovery Agent | LLM tool-caller | Plans search queries across experience types (tourist, local, hidden, food, nature, culture, nightlife, free, events) and calls search tools until coverage targets are met. | Tools Eng. |
| D1 | Ranker and Diversifier | Deterministic | Scores candidates (preference match, travel time, cost, local/tourist fit, freshness) and applies a diversity re-rank so days are not repetitive. | Preferences Eng. |
| A3 | Itinerary Planner Agent | Hybrid | Deterministic geographic clustering assigns candidates to days; the LLM proposes an ordering and pacing per day; a deterministic scheduler assigns exact times using the travel matrix. | Agent Graph Eng. |
| A4 | Backup Agent | Hybrid | For each priority activity, tags its purpose (for example "food + culture") and pre-computes two validated, purpose-preserving alternatives. | Tools Eng. + Preferences Eng. |
| D2 | Validator | Deterministic | Runs schedule, hours, travel-time, budget, preference, diversity and freshness checks. Never an LLM. | Validation Eng. |
| D3 | Router (Supervisor) | Deterministic | LangGraph conditional edges that read validation results and counters to choose the next node. Kept deterministic so control flow is testable. | Agent Graph Eng. |
| A5 | Change Interpreter Agent | LLM + schema | Turns "I'm 90 minutes late" or "budget is now $300" into a typed ChangeEvent. Asks the user when the change is ambiguous. | Preferences Eng. |
| D4 | Impact Analyzer | Deterministic | Given a ChangeEvent and the current itinerary, computes the affected set: activities, time windows and routes that are now invalid or at risk. | Validation Eng. |
| A6 | Repair Agent (Replanner) | Hybrid | Tries stored backups first, then targeted tool search (nearby, along route, cheaper, indoor). The LLM chooses among only the feasible candidates, favouring purpose preservation and minimal change. | Agent Graph Eng. |
| A7 | Explainer Agent | LLM (grounded) | Writes the change summary and reasons from the structured ReplanEvent diff only. Cannot introduce facts not in the diff. | Frontend & Maps Eng. + Preferences Eng. |

> **Why not one big "travel agent" prompt?** A single prompt cannot be unit-tested, cannot be forced to respect hard constraints and cannot be partially re-run. Splitting into small agents with typed inputs and outputs lets five people build in parallel against mocks, and lets the validator catch LLM mistakes before users see them.

### 3.1 Agent contracts

Every agent has the same contract shape. If an agent cannot produce a valid output after its retry budget, it returns an error object instead of guessing.

```
class AgentResult(BaseModel, Generic[T]):
    ok: bool
    output: T | None            # typed payload, validated by Pydantic
    error: AgentError | None    # code, message, retryable
    tokens_used: int
    tool_calls: int
    trace_ids: list[str]        # ExecutionEvent ids written during this run
```

| Agent | Input (from state) | Output (to state) | LLM output format | Retry budget |
|---|---|---|---|---|
| Intake | raw form, free text | TripRequirements, open_questions | JSON schema (structured output) | 2 parse retries |
| Discovery | TripRequirements | candidate_places, coverage report | Tool calls | 8 tool calls, 1 re-plan |
| Planner | ranked candidates, clusters, matrix | itinerary draft (ordering only) | JSON: day -> ordered place_ids | 2 parse retries |
| Backup | itinerary, candidates | backups per activity, purpose tags | JSON: purpose tags | 1 retry; deterministic fallback |
| Change Interpreter | user message, current trip | ChangeEvent or clarification | JSON schema | 2 parse retries |
| Repair | affected set, backups, new candidates | ItineraryPatch | JSON: chosen candidate ids + reason | 3 repair iterations |
| Explainer | ReplanEvent diff | ChangeSummary text | JSON: per-change reason strings | 1 retry; template fallback |

## 4. Shared State (TripState)

State is the single shared memory for the graph. It is persisted after every node so a workflow can be inspected, resumed or replayed.

```
class TripState(TypedDict):
    trip_id: str
    version: int                         # +1 on every accepted replan
    requirements: TripRequirements       # dates, budget, mode, pace, interests, avoid,
                                         # tourist_local_ratio, max_travel_min, ...
    field_provenance: dict[str, Literal["explicit", "inferred", "default"]]
    open_questions: list[Question]       # clarification loop
    candidate_places: list[Place]        # source, retrieved_at, experience_types
    travel_matrix: TravelMatrix | None   # per mode, per cluster
    clusters: list[DayCluster]
    itinerary: Itinerary                 # days -> activities (planned|done|locked|cancelled)
    backups: dict[str, list[Backup]]     # activity_id -> ranked purpose-preserving alts
    validation: list[ValidationResult]
    pending_change: ChangeEvent | None
    affected: AffectedSet | None
    replan_history: list[ReplanEvent]

    # loop control
    phase: Literal["intake", "plan", "repair", "adapt", "done"]
    counters: dict[str, int]             # clarify, discovery_calls, repair_iter, cascade
    last_violation_score: float          # used for the progress check
    terminal: Literal["PASS","INFEASIBLE","NEEDS_USER","ERROR"] | None
    events: list[str]                    # ExecutionEvent ids
```

Rules: nodes return partial updates, never mutate other nodes' fields; `itinerary` is only written by Planner and Repair; `validation` is only written by the Validator; activities with status `done` or `locked` are read-only for every node.

## 5. The Loop Catalogue

TripAgent is agentic because of its loops. There are seven runtime loops and two engineering loops. Each runtime loop below lists its trigger, body, exit conditions and guardrails. The loop limits are configuration values in `backend/app/config.py` (loop settings) so tests can lower them.

| Loop | Kind | Runs when | Hard cap | Terminal states |
|---|---|---|---|---|
| L1 Clarification | Human-in-the-loop | Required fields missing or contradictory | 2 rounds | continue / NEEDS_USER |
| L2 Discovery (tool-use) | ReAct / tool loop | Building candidate pool | 8 tool calls | coverage met / partial coverage |
| L3 Plan-Validate-Repair | Core control loop | After first itinerary draft | 3 repair iterations | PASS / INFEASIBLE |
| L4 Adaptive replanning | Event-driven outer loop | User or environment change | 1 event at a time; each uses L3 | new version / unchanged + explanation |
| L5 Backup cascade | Fallback loop | An activity becomes invalid | depth 4 (2 backups, 2 searches) | replaced / removed / escalate |
| L6 Tool retry and fallback | Reliability loop | Provider error or timeout | 2 retries + 1 fallback | result / degraded / ERROR |
| L7 Approval (P1) | Human-in-the-loop | Major change proposed | 1 proposal per event | accepted / rejected |

### 5.1 L1: Clarification loop

```
Intake Agent -> requirements + open_questions
  if blocking question (no destination, no dates, budget < 0, contradictions):
      ask user (UI shows 1-3 questions) -> merge answers -> Intake Agent again
  exit: no blocking questions  -> continue to Discovery
        counters.clarify == 2  -> NEEDS_USER (show what is still missing)
```

Non-blocking gaps are filled with documented defaults and marked `default` in field_provenance, so the UI can show "We assumed a moderate pace. Change it?" instead of silently guessing.

### 5.2 L2: Discovery tool loop

```
Discovery Agent sees: requirements + coverage report
  THINK  which experience types / neighbourhoods are under-covered?
  ACT    search_places(...) | category_search(...) | search_events(dates)
  OBSERVE normalized Places appended; coverage report recomputed (deterministic)
repeat until:
  coverage met (>= 3 per required interest, >= 2 local, >= 2 free)  -> exit
  counters.discovery_calls == 8                    -> exit, partial coverage flag
  2 consecutive calls add < 2 new unique places    -> exit (no progress)
```

The coverage report is computed by code, not judged by the LLM. The LLM only decides what to search next. Duplicate places are merged by provider id and by name + distance under 50 m.

### 5.3 L3: Plan-Validate-Repair (the core loop)

```
Planner -> Scheduler -> Backup Agent -> VALIDATOR
                                           |
               +--------- PASS ------------+---- FAIL (hard violations)
               v                                     v
          persist version                   counters.repair_iter += 1
          terminal = PASS                   progress check: score < last_violation_score ?
                                                     |            |
                                                    yes           no (stalled twice)
                                                     v            v
                                              Repair Agent    INFEASIBLE + explanation
                                                     |
                                                     +--> VALIDATOR (again)
exit when repair_iter == 3 -> INFEASIBLE with the unresolved constraints listed
```

**Violation score** = 100 x hard violations + soft penalty. The progress check stops "thrashing", where the repair agent swaps A for B and then B back for A. Soft-constraint failures (weak diversity, slightly long walks) do not trigger repair on their own; they lower the plan score and are shown to the user.

### 5.4 L4: Adaptive replanning (event loop)

```
WAIT for event
  user:        "budget is now $300" | "I'm 90 min late" | "no museums" | "walk"
  environment: venue closed | event cancelled | (P1) rain forecast
-> Change Interpreter (A5) -> ChangeEvent (validated; ambiguous -> L1-style question)
-> apply change to requirements (new requirements version)
-> Impact Analyzer (D4): affected activities, time windows, routes
-> for each affected activity: Backup cascade (L5)
-> Scheduler re-times only the affected day(s); routes recomputed for changed legs
-> VALIDATOR -> L3 repair iterations if needed
-> Explainer (A7) -> ChangeSummary (changed / moved / preserved / removed + reasons)
-> persist itinerary version N+1 (version N kept for undo) -> WAIT
```

Only one change event is processed at a time per trip (a simple per-trip lock). Events arriving mid-run are queued in the database and processed next, which avoids two replans editing the same itinerary.

### 5.5 L5: Backup cascade

```
activity X invalid (closed, too expensive, too far, rain, sold out)
  1. stored backup #1  -> revalidate against CURRENT constraints -> ok? use it
  2. stored backup #2  -> revalidate                              -> ok? use it
  3. live search: same purpose, within 10 min of neighbours / along route
  4. live search: widened radius (20 min) or relaxed soft preference
  5. none feasible -> remove X, stretch neighbours or leave free time, and explain
```

Backups are **purpose-preserving**: a $40 cooking class tagged "food + culture" is replaced by a $15 food market with a demo before it is replaced by just another restaurant. Candidates are ranked by purpose similarity first, then travel impact, then cost.

### 5.6 L6: Tool retry and fallback

```
call provider
  timeout / 5xx / 429 -> retry with exponential backoff (0.5 s, 1.5 s)
  still failing        -> fallback: cache (< 24 h) -> secondary provider -> fixture
  still failing        -> degraded flag in state; node decides whether to continue
  4xx (bad request)    -> no retry; ERROR event with sanitized message
```

### 5.7 L7: Approval loop (P1)

If a proposed replan changes more than 2 activities, raises cost, or removes a user-locked activity, the plan is shown as a proposal (before/after on the map) and the user chooses **Apply changes** or **Keep my plan**. This is the only place the agent pauses for consent; it uses LangGraph interrupt support and resumes from the persisted state.

### 5.8 Engineering loops

| Loop | Cadence | What happens |
|---|---|---|
| E1 Evaluation loop | Every PR touching agents or validators | Run the scenario benchmark (Test Strategy, Section 6). Metrics are compared with the last main-branch run; a drop blocks merge. |
| E2 Scrum inspect-adapt loop | Every sprint | Plan -> build -> demo -> retro -> adjust backlog. Velocity from Sprint 1 recalibrates Sprints 2-4. |

### 5.9 Loop engineering checklist

Every new loop must pass this checklist in code review:

- Counter stored in TripState, not a local variable (survives resume).
- Hard cap read from config.
- Progress measure that must strictly improve, or the loop exits early.
- Named terminal states with a user-facing message for each.
- Idempotent body: re-running an iteration after a crash does not duplicate activities or events.
- One ExecutionEvent per iteration with the counter value.
- A test that forces the cap and asserts the terminal state.

## 6. Full Workflow Graph

```
                       START
                         |
                    [A1 Intake] <---- L1 clarification ----> user
                         |
                  [A2 Discovery] <--- L2 tool loop ---> search / events tools
                         |
               [D1 Rank + Diversify]
                         |
          [Map: cluster + travel matrix]
                         |
                 [A3 Planner + Scheduler]
                         |
                  [A4 Backup Agent]
                         |
                    [D2 Validator] ----PASS----> [Persist vN] --> END (await events)
                         |                                ^
                        FAIL                              |
                         v                                |
                   [D3 Router] -- cap/stall --> INFEASIBLE + explanation
                         |
                  [A6 Repair Agent] <-- L5 backup cascade
                         |
                    (back to D2)

  EVENT (user or environment)
     -> [A5 Change Interpreter] -> [D4 Impact Analyzer] -> [A6 Repair] -> [D2 Validator]
     -> [A7 Explainer] -> (P1: L7 approval) -> [Persist vN+1]
```

## 7. Validation Pipeline

Validators are pure functions: `(itinerary, requirements, matrix) -> list[ValidationResult]`. They run in a fixed order so results are reproducible.

| Order | Validator | Hard or soft | Rule (default) |
|---|---|---|---|
| 1 | Schema | Hard | All activities reference known places; times parse; day within trip dates. |
| 2 | Schedule overlap | Hard | No two activities overlap; each activity fits inside daily start/end. |
| 3 | Opening hours | Hard if data exists | Activity window inside known hours; unknown hours produce a warning, never a pass. |
| 4 | Travel time | Hard | Leg time for chosen mode <= max_travel_min and <= gap between activities. |
| 5 | Budget | Hard or configurable | Sum of known costs <= budget; unknown costs counted and reported. |
| 6 | Avoid list | Hard | No activity category in `avoid`. |
| 7 | Preference coverage | Soft | Each stated interest appears at least once per trip. |
| 8 | Diversity | Soft | >= 3 distinct categories per full day; <= 2 consecutive same category; tourist/local ratio within 20% of target. |
| 9 | Freshness | Soft | Events retrieved < 24 h ago; place data < 7 days; stale items labelled. |
| 10 | Geographic efficiency | Soft | Total daily travel <= 25% of active day time. |
| 11 | Backup coverage | Soft | Every high-priority activity has >= 1 valid backup. |

## 8. Maps as a Reasoning Tool

All map operations sit behind internal tool interfaces so providers can be swapped or mocked.

```
search_places(query, near: LatLng, categories, radius_min, mode) -> list[Place]
category_search(category, bbox | near)                        -> list[Place]
search_along_route(route: Route, category, max_detour_min)    -> list[Place]
get_route(origin, dest, mode, depart_at)                      -> Route
get_travel_matrix(points: list[LatLng], mode)                 -> TravelMatrix
search_events(city, start, end, categories)                   -> list[Event] (P1)
get_weather(city, start, end)                                 -> Forecast (P2)
```

| Map capability | Used by | How it drives decisions |
|---|---|---|
| Travel matrix per mode | Planner, Validator, Repair | Feeds scheduling and the travel-time rule; recomputed when the user switches walking/transit/driving. |
| Geographic clustering | Planner | Groups candidates into day-sized neighbourhoods (k-medoids on travel time, k = number of days) so days are compact. |
| Route ordering | Scheduler | Nearest-neighbour start plus 2-opt improvement within a day, while respecting fixed-time items (reservations, events). |
| Nearby search | Repair, Backup | Finds replacements within N minutes of the previous and next activity, not of the city centre. |
| Along-route search (P1) | Repair, user request | "Find me coffee on the way" searches around the current leg with a max detour. |
| Route diff | UI | After a replan, changed legs are drawn with a distinct style and a legend; preserved legs stay unchanged. |

> ⚠️ **Provider limits to design around (verify in the Sprint 1 spike):** matrix endpoints cap the number of coordinates per request, so matrices are computed per day-cluster rather than for the whole city; POI providers differ in coverage of prices, opening hours and popularity; transit routing coverage varies by provider and city. Cache routes and matrices by (points, mode, hour) to control cost.

## 9. Data Model and API

> **Target vs current model.** Section 9.1 is the fuller target model. The shapes the code uses **right now** are in `docs/contracts.md` and `backend/app/models/`, agreed at the Sprint 1 kickoff. When they disagree, `docs/contracts.md` wins; fields from 9.1 are added sprint by sprint as stories need them.

### 9.1 Entities

| Entity | Key fields |
|---|---|
| Trip | id, destination, start_date, end_date, status, current_version, created_at |
| Requirements (versioned) | trip_id, version, budget, mode, pace, interests[], avoid[], tourist_local_ratio, max_travel_min, daily_start, daily_end, dietary, accessibility, free_text, provenance{} |
| Place | id, sources[], provider_ids{}, name, categories[], experience_types[], lat, lng, address, price_level, est_cost_low, est_cost_high, cost_basis (known\|price_level\|free\|unknown), hours, rating, review_count, popularity, local_signal (tourist\|local\|hidden\|unknown), field_provenance{}, retrieved_at |
| Event (P1) | id, provider, name, venue_place_id, starts_at, ends_at, price, url, retrieved_at |
| ItineraryVersion | trip_id, version, created_by (plan\|replan), parent_version, score |
| Activity | id, trip_id, version, day, place_id, start, end, est_cost, priority, purpose_tags[], status (planned\|done\|locked\|cancelled) |
| Backup | activity_id, place_id, rank, purpose_similarity, cost_delta, travel_delta_min, validated_at |
| ValidationResult | id, trip_id, version, rule, passed, severity, message, activity_ids[] |
| ChangeEvent | id, trip_id, source (user\|environment\|simulated), type, payload, raw_text, status |
| ReplanEvent | id, trip_id, from_version, to_version, trigger_id, diff{changed, moved, preserved, added, removed}, reasons{}, iterations |
| ExecutionEvent | id, trip_id, run_id, node, type (node\|tool\|llm\|validation\|loop), iteration, status, duration_ms, metadata, ts |

### 9.2 REST API

All routes are mounted under the `/api` prefix (for example `POST /api/trips`). Code lives in `backend/app/api/`.

| Method | Endpoint | Purpose |
|---|---|---|
| POST | /trips | Create trip from form + free text; returns trip and any clarification questions. |
| POST | /trips/{id}/answers | Answer clarification questions (L1). |
| POST | /trips/{id}/plan | Run initial planning (L2 + L3). Returns run_id. |
| GET | /runs/{run_id} | Run status and progress (polling; SSE optional in P1). |
| GET | /trips/{id}/itinerary?version= | Current or historical itinerary with backups and validation. |
| POST | /trips/{id}/changes | Submit a change in text or typed form (L4). |
| POST | /trips/{id}/activities/{aid}/swap | User picks a backup manually; revalidates. |
| POST | /trips/{id}/versions/{v}/restore | Undo to an earlier version. |
| POST | /trips/{id}/simulate | Demo disruptions (venue closed, delay, rain). |
| GET | /trips/{id}/trace | Execution events for the trace panel. |
| GET | /health | Liveness and dependency status for deployment. |

### 9.3 Sprint 1 request and response examples

Examples use the MVP shapes from `docs/contracts.md`. They are illustrative; the contracts file is authoritative.

```
POST /api/trips
{
  "destination": "Seattle",
  "start_date": "2026-10-12",
  "end_date": "2026-10-14",
  "budget": 500,
  "transport_mode": "transit",
  "free_text": "First time in Seattle. I love coffee, bookstores and parks, hate museums,
                and don't want to travel more than 30 minutes between stops."
}

201 Created
{
  "trip_id": "trp_8f2c1a",
  "trip": { ...same fields as the request... },
  "preferences": {
    "interests": ["coffee", "bookstores", "parks"],
    "avoid": ["museums"],
    "pace": "moderate",
    "max_travel_minutes": 30,
    "where_from": {
      "interests": "from your text",
      "avoid": "from your text",
      "pace": "assumed",
      "max_travel_minutes": "from your text"
    }
  },
  "created_at": "2026-10-05T19:30:00Z"
}

GET /api/trips/trp_8f2c1a          -> 200, same body as above
GET /api/health                    -> 200 {"status": "ok", "demo_mode": true}

422 Unprocessable Entity (validation error, e.g. end_date before start_date)
{ "detail": [ { "loc": ["body", "end_date"], "msg": "end_date must be on or after start_date" } ] }
```

## 10. Deployment Architecture

```
Browser (Svelte + Vite, Mapbox GL JS with a URL-restricted public token)
        |
        v  HTTPS
Static hosting / CDN  (frontend build)
        |
        v  HTTPS  /api/*
FastAPI container (1 service: API + LangGraph + tools)  --->  Gemini API
        |                                               --->  Map / POI / events providers
        v
Managed Postgres (SQLite in local dev)          Structured JSON logs -> host log viewer
```

- Secrets (LLM key, server-side provider keys) live only in the backend host's environment settings. The browser map token is a separate, URL-restricted public token.
- A walking-skeleton deployment is done in Sprint 1 and redeployed on every merge to main, so deployment is never a last-week surprise.
- Database migrations with Alembic; SQLite locally and Postgres in production through the same SQLAlchemy models (keeps NFR-11).
- Rate limits per IP on /plan and /changes protect the LLM budget. A monthly spend cap is set in the provider dashboards.
- `DEMO_MODE=true` switches every tool to recorded fixtures so the final demo cannot be broken by an outage.

## 11. Architecture Decision Records

### ADR-001: Orchestrate with an explicit LangGraph state graph

**Status:** Proposed | **Deciders:** Tech Lead, Agent Graph Eng.

**Context:** The system needs loops with caps, conditional branches, persistence between steps and human pauses. The team is beginner-to-intermediate and needs debuggable control flow.

| Dimension | A: LangGraph graph | B: Plain Python loop | C: Autonomous single agent |
|---|---|---|---|
| Complexity | Medium | Low at first, grows quickly | Low code, high unpredictability |
| Loop control | Explicit edges, checkpoints | Hand-written | Model decides; hard to cap |
| Testability | Node and edge tests | Good | Poor |
| Human-in-the-loop | Built-in interrupts | Hand-written | Awkward |
| Team learning value | High | Medium | Low |

**Decision:** A. Routing stays deterministic; LLMs live inside nodes. **Consequences:** easier tracing and resume; the team must learn LangGraph state reducers early (Sprint 1 practice loop). Revisit if the graph becomes too large to read.

### ADR-002: Deterministic validators; LLM never judges hard constraints

**Status:** Accepted. **Decision:** all hard constraints are pure Python functions with unit tests. The LLM may explain validator output but never overrides it. **Consequence:** some "creative" plans get rejected; that is intended.

### ADR-003: Place and POI data provider

**Status:** Accepted, pending Sprint 1 fill-rate spike (S0-05) | **Date:** October 5, 2026 | **Deciders:** Tech Lead, Tools Eng., Preferences Eng.

**Context:** Budget validation, opening-hours validation and the tourist/local balance need price level, hours, ratings, review counts and popularity for each place. Mapbox is strong for maps, routing and travel-time matrices but thinner on these venue attributes.

| Dimension | A: Mapbox only | B: Mapbox + Foursquare Places | C: All-Google (Places + Routes + Maps) | D: Curated seed data |
|---|---|---|---|---|
| Hours, price level, ratings | Limited | Yes (Premium fields) | Yes (higher-tier fields) | Exact for demo cities |
| Local signal inputs | None | Popularity, tips, 1,500+ categories | Ratings and review counts | Hand-labelled |
| Fits current Mapbox map | Yes | Yes (attribution required) | No: licence terms likely require a Google map and limit storage (verify) | Yes |
| Caching / fixtures / DB storage | OK per Mapbox terms | Check licence; expected workable | Restricted (verify) | Unrestricted |
| Cost at demo scale | Low | Low: 500 free Pro calls/month, Premium ~$18.75 per 1,000 (June 2026 rates) | Low to medium; billed per field tier | Free |
| Change to architecture | None | One new adapter + merge step | Replace map, routing and matrix stack | None |

**Decision:** Option B, with D kept permanently as the test and demo fallback. Mapbox stays the source for geometry, routing, matrices and map rendering. Foursquare enriches places with hours, price level, rating, review count, popularity and tips. Both sit behind the existing `search_places` adapter interface so neither provider leaks into agent code.

#### Merge rules

- Discovery searches Foursquare for venues (richer categories) and uses Mapbox coordinates only for routing inputs.
- When the same venue appears from both providers (name similarity >= 0.85 and distance < 50 m), keep one Place with `sources: [mapbox, foursquare]` and per-field provenance.
- Premium fields are requested only for candidates that survive filtering and ranking (roughly top 40 per trip), not for every search hit. This keeps the Premium call count low.
- Every Place stores `source`, `retrieved_at` and per-field provenance; the UI shows "Powered by Foursquare" wherever its data appears.

#### Derived signals (heuristics, not facts)

| Signal | Rule (v1, tune in Sprint 2) | Shown to user as |
|---|---|---|
| Tourist | Landmark/attraction category, OR review count in the top 10% for the city and category, OR high popularity with tourist-area location | "Popular sight" |
| Local favourite | Rating >= 4.2 (or provider equivalent), review count between the 25th and 80th percentile for its category, not a landmark category, not a chain | "Local pick" |
| Hidden gem | Rating >= 4.4 and review count below the 25th percentile, with at least 20 reviews | "Hidden gem" |
| Unknown | Missing rating or review data | No badge |

Percentiles are computed per city and per category from the candidate pool, so a busy downtown cafe is compared with other cafes, not with museums. Thresholds live in `backend/app/config.py` (signal settings).

#### Estimated cost model

Price level is a scale ($ to $$$$), not a dollar amount, and attraction ticket prices are usually missing. Cost is therefore always an estimate with a label:

| Source of cost | Rule | Label |
|---|---|---|
| Known price (seed data or explicit ticket price) | Use as is | "$25" |
| Price level | Per-category range table (for example food $ = $8-15 per person, $$ = $15-35); plan against the upper bound | "About $15-35" |
| Free category (park, viewpoint, free museum day) | $0 | "Free" |
| Nothing known | Excluded from the total; counted separately | "Cost unknown" |

The budget validator checks the sum of upper-bound estimates against the budget and reports how many activities have unknown cost. The user can mark budget as strict (upper bounds must fit) or flexible (midpoints must fit).

#### Spike (Sprint 1, S0-05) exit criteria

- Pull 30 real candidate places per demo city through both providers and record fill rates for hours, price level, rating, review count and popularity.
- Target: hours >= 70% for food and cafes, price level >= 60% for food, rating/review count >= 80% overall.
- Estimate calls and cost for one planning run and one replan.
- Confirm licence terms for caching, storing Place rows and recorded fixtures, and the attribution requirement.
- If targets are missed, keep B for what it provides and lean on D for the demo cities; document the gap in the UI with "Cost unknown" and "Hours not listed".

**Consequences:** richer, more honest planning without changing the map stack; one more API key, adapter and merge step; the local-favourite feature is openly a heuristic; ongoing cost is small if Premium calls are limited to ranked candidates and cached. Revisit if coverage in a new city is poor or pricing changes again.

### ADR-004: Pre-compute backups at planning time

**Status:** Proposed. **Context:** Repair must be fast and must not always depend on live search. **Decision:** the Backup Agent stores two validated backups for each high and medium priority activity. **Consequences:** more tool calls up front (mitigated by reusing the candidate pool); faster, more reliable replans; backups must be revalidated at use time because constraints may have changed.

### ADR-005: Relational database with versioned itineraries

**Status:** Accepted. **Decision:** SQLite locally, managed Postgres in production, through SQLAlchemy + Alembic. Every accepted replan creates a new ItineraryVersion instead of overwriting. **Consequences:** undo and before/after diffs become trivial; storage grows slowly (acceptable at demo scale).

### ADR-006: Polling for run progress in MVP

**Status:** Accepted. **Decision:** the UI polls `/runs/{id}` every second while a run is active. Server-sent events are a P1 upgrade. **Consequence:** simpler hosting; slightly less live feel in the trace panel.

### ADR-007: LLM provider is Google Gemini (free tier)

**Status:** Accepted | **Date:** October 5, 2026 | **Deciders:** Tech Lead

**Context:** The team has no budget for paid LLM APIs. The agents need structured output (Pydantic-shaped JSON) and LangGraph integration.

| Dimension | A: OpenAI API | B: Gemini API free tier | C: Local models (Ollama) |
|---|---|---|---|
| Cost | Paid per token | Free, no card; rate-limited | Free |
| Structured output | Yes | Yes (Pydantic schemas in google-genai) | Weaker on small models |
| LangGraph integration | Yes | Yes (langchain-google-genai) | Yes |
| Works in the deployed demo | Yes | Yes | No (runs on a laptop) |
| Limits | Spend | Roughly 10-15 requests/min per project on Flash models | Laptop hardware |

**Decision:** B, using Flash models. **Consequences:** each engineer creates their own key in their own Google AI Studio project (limits are per project); DEMO_MODE and cached LLM responses are used for routine development and CI; L6 retry with exponential backoff handles 429 responses; free-tier inputs may be used by Google to improve its products, so only made-up trip data is used. Model names live in `backend/app/config.py` so the model can be changed in one place. Ollama is the offline fallback for experiments.

### ADR-008: Frontend framework is Svelte

**Status:** Accepted | **Date:** October 5, 2026 | **Deciders:** Product Owner, Frontend & Maps Eng.

**Context:** The original plan used React. The Frontend & Maps Eng. had already started the UI in Svelte, and `main` only had a React hello-world, so switching cost almost nothing.

**Decision:** Svelte + Vite + TypeScript. The backend contract (REST under `/api`) is unchanged. Mapbox GL JS is used directly (it does not depend on a framework). Component tests use Vitest + Svelte Testing Library; type checks use `svelte-check`; lint uses ESLint with `eslint-plugin-svelte`.

**Consequences:** fewer ready-made React components and map wrappers, so some UI pieces are written by hand; the component specs in the Design System doc still apply (props become Svelte component props). Revisit only if the frontend owner changes.

## 12. Reliability, Observability and Security

| Concern | Design |
|---|---|
| LLM output invalid | Gemini structured output + Pydantic validation; 2 retries with the error message; then a typed failure. |
| LLM rate limits (free tier) | Exponential backoff on 429; per-run call caps; DEMO_MODE and cached responses during development. |
| Runaway cost | Per-run caps: 8 discovery calls, 3 repair iterations, token budget per run; per-IP rate limits. |
| Provider outage | L6 retry/fallback; cache; DEMO_MODE fixtures. |
| Prompt injection via tool data | Place names, descriptions and event text are inserted as quoted data, never as instructions; outputs are schema-validated. |
| Traceability | ExecutionEvent per node, tool call, LLM call and loop iteration with run_id; trace panel in UI; optional LangSmith. |
| Privacy | No accounts in MVP; free text stored with the trip only; logs redact free text and keys. |
| Secrets | .env ignored by Git; secret scanning enabled on the repository; server-only keys never shipped to the browser. |

## 13. What to Revisit as the System Grows

- Move long runs to a background worker if planning exceeds ~30 s on the host.
- Replace heuristic ordering with a small constraint solver (for example OR-Tools) if days exceed ~8 activities.
- Add user accounts and saved trips when sharing becomes a goal.
- Add an embedding-based purpose similarity if tag-based similarity proves too coarse.
