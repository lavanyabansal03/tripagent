# TripAgent: Software Requirements Specification v2

_Personalization, diversity, current information, backups, maps and deployment_

| Field | Value |
|---|---|
| Owner role | Product Owner + Tech Lead |
| Team | Product Owner / Engineering Manager; five engineers in role areas: Preferences, Validation, Agent Graph, Tools, Frontend & Maps |
| Version | 2.3 (October 5, 2026) |
| Status | Living document, updated each sprint |
| Method | Requirements specification (supersedes TripAgent_SRS_and_TechStack_UPDATED.docx) |

## 1. Document Purpose and Change Log

This specification defines scope, user stories, functional and non-functional requirements, constraints, replanning behaviour, scenarios, data contracts and acceptance criteria for TripAgent. It serves a 5-person student team building toward a final presentation on Monday, November 2, 2026. Under this timeline, P1 requirements are stretch goals. Architecture detail lives in the Architecture & Agent Design document; priorities and rationale live in the Product Vision & PRD.

| Version | Change |
|---|---|
| 1.0 | Initial SRS and tech stack. |
| 1.1 (UPDATED) | Added adaptive replanning stories US-13 to US-16 and FR-25 to FR-32. |
| 2.4 (Oct 5) | Frontend framework changed from React to Svelte (ADR-008). |
| 2.3 | LLM changed from OpenAI to Google Gemini free tier (ADR-007); NFR-03 relaxed for free-tier rate limits; timeline moved to four one-week sprints from October 5; code layout and /api prefix recorded; source-of-truth order added in Section 9. |
| 2.1 | ADR-003 decided: Mapbox + Foursquare with seed-data fallback. Added FR-56 to FR-58; clarified FR-10 (estimated cost model) and FR-36 (local signal heuristic); added Estimate constraint type. |
| 2.0 | Added personalization (free text, tourist/local), diversity, current events and freshness, purpose-preserving backups, map-driven planning, versioning, deployment and demo mode (US-17 to US-29, FR-33 to FR-55, NFR-13 to NFR-15). Consolidated the duplicated replanning section from 1.1 into one ordered procedure. Added priority to every requirement. |

## 2. Product Definition

TripAgent is an agentic travel planning and adaptive itinerary system that creates personalized, geographically efficient trips using real-world places and current information, and adapts the itinerary when the user's time, budget, preferences, transportation or activity availability changes.

```
OBSERVE -> DECIDE -> ACT THROUGH TOOLS -> UPDATE STATE -> VALIDATE -> REPAIR IF NEEDED -> OBSERVE AGAIN
```

## 3. Scope

### 3.1 In scope (MVP)

- Trip setup with form and free text; clarification questions.
- Place discovery across experience types; ranking with diversity and tourist/local balance.
- Multi-day itinerary with map-verified travel times, clustering and route order.
- Deterministic validation; backups; purpose-preserving repair.
- Adaptive replanning for budget, time, preference, transport and closure changes.
- Change summary, route diff, agent trace.
- Deployed public demo with demo mode.

### 3.2 Out of scope

- Bookings, tickets, payments or financial accounts.
- Native mobile apps; real-time GPS tracking.
- User accounts and social features.
- Model fine-tuning; large training datasets.
- Microservices, Kubernetes, message queues or vector databases.

## 4. User Stories

| ID | Feature | Story | Priority |
|---|---|---|---|
| US-01 | Trip setup | As a traveler, I want to enter destination, dates, budget, interests and transportation so the system understands my trip. | P0 |
| US-02 | Preference capture | As a traveler, I want to specify activities I like and avoid so the itinerary reflects my preferences. | P0 |
| US-03 | Initial plan | As a traveler, I want a day-by-day itinerary so I know what to do and when. | P0 |
| US-04 | Real places | As a traveler, I want suggestions to be real locations with useful location information. | P0 |
| US-05 | Schedule feasibility | As a traveler, I want no overlapping activities or impossible travel times. | P0 |
| US-06 | Budget awareness | As a traveler, I want the itinerary to respect my budget when cost data exists. | P0 |
| US-07 | Map view | As a traveler, I want to see activities and routes on a map. | P0 |
| US-08 | Disruption handling | As a traveler, I want to report a closure or delay and have the affected part adapt. | P0 |
| US-09 | Minimal change | As a traveler, I want unaffected activities preserved. | P0 |
| US-10 | Explainability | As a traveler, I want to know why an activity was replaced or moved. | P0 |
| US-11 | Feasibility | As a traveler, I want to be told when requirements are impossible. | P0 |
| US-12 | Traceability | As a developer, I want to see which planning, tool, validation and replanning steps ran. | P0 |
| US-13 | Budget change | As a traveler, I want to change my budget after planning and get a revised plan within it when feasible. | P0 |
| US-14 | Time change | As a traveler, I want to report reduced time and get the remaining plan adjusted. | P0 |
| US-15 | Preference change | As a traveler, I want to change interests, avoidances, pace or transport and have the plan adapt. | P0 |
| US-16 | Replan transparency | As a traveler, I want to see what changed, what was preserved, and why. | P0 |
| US-17 | Free-text details | As a traveler, I want to describe my trip in my own words and have it understood. | P0 |
| US-18 | Tourist/local balance | As a traveler, I want to set how much of my trip is tourist sights vs local favourites. | P0 |
| US-19 | Diversity | As a traveler, I want varied days, not repetitive ones. | P0 |
| US-20 | Current events | As a traveler, I want to see what is happening during my dates, with a retrieved date. | P1 |
| US-21 | Backups | As a traveler, I want ready alternatives for each important activity. | P0 |
| US-22 | Purpose-preserving swap | As a traveler, I want replacements to keep the purpose of the original. | P0 |
| US-23 | Travel limit | As a traveler, I want to cap travel time between activities. | P0 |
| US-24 | Compact days | As a traveler, I want each day grouped by area and ordered sensibly. | P0 |
| US-25 | Along-route search | As a traveler, I want to find a place along my current route. | P1 |
| US-26 | Transport switch | As a traveler, I want to switch modes and see if the plan still works. | P0 |
| US-27 | Public demo | As a stakeholder, I want a public demo URL. | P0 |
| US-28 | Weather | As a traveler, I want rain to swap outdoor plans for indoor ones. | P2 |
| US-29 | Undo | As a traveler, I want to restore the previous itinerary version. | P1 |

## 5. Functional Requirements

Priority follows the PRD: P0 must ship for the MVP demo, P1 should ship, P2 is designed for but not built.

| ID | Area | Requirement (the system shall...) | Priority |
|---|---|---|---|
| FR-01 | Trip creation | Accept destination, dates, budget, interests, transportation mode and optional preferences. | P0 |
| FR-02 | Requirement normalization | Convert natural-language requirements into a validated structured representation. | P0 |
| FR-03 | Candidate discovery | Retrieve candidate places from an external search/location provider. | P0 |
| FR-04 | Candidate filtering | Filter candidates by explicit hard constraints where data exists. | P0 |
| FR-05 | Candidate ranking | Rank candidates by declared factors: preference match, travel time, availability, cost, experience type. | P0 |
| FR-06 | Itinerary generation | Create a structured itinerary of days, activities, time windows and locations. | P0 |
| FR-07 | Schedule validation | Detect overlapping or impossible activity times. | P0 |
| FR-08 | Opening-hours validation | Where hours exist, check activities fall within them; unknown hours produce a warning. | P0 |
| FR-09 | Travel-time validation | Calculate travel time between consecutive activities for the chosen mode and flag violations. | P0 |
| FR-10 | Budget validation | Total estimated costs using the cost model in ADR-003 (known price, price-level range, free, unknown); check upper bounds when budget is strict and midpoints when flexible; report unknown-cost count; detect violations. | P0 |
| FR-11 | Preference validation | Evaluate whether required or preferred categories are satisfied. | P0 |
| FR-12 | Violation classification | Classify problems by type and severity (hard, soft, data-gap). | P0 |
| FR-13 | Replanning | Generate candidate fixes for a detected violation. | P0 |
| FR-14 | Minimal change | Preserve unaffected items when feasible. | P0 |
| FR-15 | Revalidation | Validate any modified itinerary before marking it feasible. | P0 |
| FR-16 | Replan limit | Stop repair after a configured maximum iterations (default 3) or when progress stalls. | P0 |
| FR-17 | Infeasibility handling | Explain unresolved constraints and suggest relaxations when no feasible plan exists. | P0 |
| FR-18 | Map visualization | Display activity markers, route lines and per-leg travel time. | P0 |
| FR-19 | Disruption simulation | Provide demo/test scenarios (closure, delay, budget drop, mode change, rain). | P0 |
| FR-20 | Agent trace | Record workflow steps, tool calls, LLM calls, loop iterations, validation outcomes and replans. | P0 |
| FR-21 | Persistence | Persist trip state and itinerary versions to continue or inspect a workflow. | P0 |
| FR-22 | API failure handling | Handle tool failures with retry, fallback and degraded states without exposing secrets. | P0 |
| FR-23 | Provenance | Retain provider/source metadata and retrieved_at on place, route and event data. | P0 |
| FR-24 | Human control | Perform no bookings or financial transactions. | P0 |
| FR-25 | Change detection | Accept post-planning changes (budget, time, preferences, transport, availability) and identify affected constraints and activities. | P0 |
| FR-26 | Adaptive budget replanning | Recalculate costs and replace, remove or reorder activities to meet a new budget, preserving higher-priority items. | P0 |
| FR-27 | Adaptive time replanning | Recalculate times and travel for the remaining plan after a time change. | P0 |
| FR-28 | Adaptive preference replanning | Adapt affected activities to changed interests, avoidances, pace or transport. | P0 |
| FR-29 | Targeted modification | Modify the smallest affected portion instead of regenerating the trip. | P0 |
| FR-30 | Preservation | Preserve unaffected, completed and user-locked activities. | P0 |
| FR-31 | Change summary | Present changed, preserved, added, removed and moved items with the trigger and reasons. | P0 |
| FR-32 | Change validation | Validate user changes and report missing, contradictory or infeasible inputs. | P0 |
| FR-33 | Free-text extraction | Extract interests, avoidances, food needs, budget priorities, pace, tourist/local preference, accessibility and travel limits from free text, labelling each field explicit, inferred or default. | P0 |
| FR-34 | Clarification | Ask at most 3 questions per round, max 2 rounds, when blocking information is missing or contradictory. | P0 |
| FR-35 | Experience typing | Tag each candidate with experience types: tourist, local, hidden, food, cafe, nature, culture, shopping, nightlife, event, free. | P0 |
| FR-36 | Tourist/local balance | Derive tourist, local and hidden signals with the configurable heuristic in ADR-003 (category, rating, review-count percentile per city and category); honour the user ratio within +/-20% when candidates allow; otherwise explain. Signals are presented as labels, not facts. | P0 |
| FR-37 | Diversity objective | Apply a diversity re-rank and validate >= 3 categories per full day and <= 2 consecutive same-category activities (configurable). | P0 |
| FR-38 | Current events | Retrieve events and seasonal activities for the trip dates from an events provider. | P1 |
| FR-39 | Stale-data handling | Label events older than 24 h and places older than 7 days as possibly outdated and offer refresh. | P1 |
| FR-40 | Purpose tagging | Assign purpose tags to each activity (for example food, culture, relaxation, views). | P0 |
| FR-41 | Backup generation | Store >= 1 (target 2) validated backups for each high and medium priority activity. | P0 |
| FR-42 | Backup cascade | On invalidation: try backups in order, then nearby live search, then widened search, then removal with explanation. | P0 |
| FR-43 | Purpose-preserving selection | Rank replacements by purpose similarity, then travel impact, then cost. | P0 |
| FR-44 | Backup revalidation | Revalidate a backup against current constraints before use. | P0 |
| FR-45 | Travel matrix | Compute travel-time matrices per transport mode for each day cluster. | P0 |
| FR-46 | Geographic clustering | Group candidates into day clusters by travel time. | P0 |
| FR-47 | Route ordering | Order activities within a day to reduce travel, respecting fixed-time items. | P0 |
| FR-48 | Nearby search | Search replacements within N minutes of neighbouring activities. | P0 |
| FR-49 | Along-route search | Search places along an active leg with a maximum detour. | P1 |
| FR-50 | Mode re-evaluation | Recompute travel and revalidate when the transport mode changes. | P0 |
| FR-51 | Route diff | Visually distinguish changed legs and activities after a replan. | P0 |
| FR-52 | Versioning and undo | Store each accepted itinerary as a version; allow restoring the previous version. | P1 |
| FR-53 | Approval for major changes | Present major replans as proposals requiring user acceptance. | P1 |
| FR-54 | Deployment | Deploy frontend and backend to a public URL with environment-based secrets, production database, health check and logs. | P0 |
| FR-55 | Demo mode | Provide a mode that uses recorded fixtures for all external tools. | P0 |
| FR-56 | Multi-provider places | Combine a map/routing provider and a venue-enrichment provider behind one adapter; merge duplicates (name similarity >= 0.85, distance < 50 m) and keep per-field provenance. | P0 |
| FR-57 | Premium-call budgeting | Request paid enrichment fields only for filtered, ranked candidates (default max 40 per trip) and cache results. | P0 |
| FR-58 | Provider attribution | Display required provider attribution wherever that provider's data appears. | P0 |

## 6. Constraint Model

| Type | Examples | System behaviour |
|---|---|---|
| Hard | Venue closed; overlap; max travel time; avoid list; accessibility | Reject or repair. |
| Hard/configurable | Budget ceiling; daily end time | Hard when marked strict by the user (default: strict). |
| Soft | Diversity; tourist/local ratio; preferred ordering; geographic efficiency | Trade off, score and explain. |
| Estimate | Cost from price level; local/tourist signal | Use with a visible label ("About $15-35", "Local pick"). |
| Data gap | Missing cost, hours or popularity | Never invent; label and count as unknown. |

## 7. Replanning Procedure

TripAgent supports two replanning modes that share one procedure: **disruption-driven** (external or simulated events) and **user-driven adaptive** (the traveler changes a requirement). The current itinerary is always the baseline.

1. Validate the change input (FR-32); ask for clarification when ambiguous.
2. Record the trigger as a ChangeEvent and create a new requirements version if requirements changed.
3. Identify affected activities, time windows and routes (impact analysis).
4. For each affected activity, run the backup cascade: stored backups, nearby search, widened search, removal.
5. Filter candidates by hard constraints first.
6. Choose among feasible candidates by purpose similarity, travel impact, cost and priority.
7. Apply the smallest reasonable change; never modify completed or locked activities.
8. Recalculate costs, travel times, hours, schedule and preference coverage for affected days.
9. Run full deterministic validation.
10. Repeat repair up to the configured limit; stop early if the violation score does not improve.
11. If infeasible, report the blocking constraint and suggested relaxations.
12. Record changed, moved, preserved, added and removed items with reasons; persist a new version.

Supported changes at minimum: budget up or down, delayed start or reduced time, venue unavailability, changed interests or avoidances, transport mode change, travel-time limit change, and (P2) weather.

## 8. Required Scenarios

| # | Scenario | Trigger | Expected behaviour |
|---|---|---|---|
| S1 | Normal plan | 3 days Seattle, $500, transit, coffee + nature + bookstores | Valid plan; diversity and travel rules pass; backups present. |
| S2 | Venue closed | Scheduled museum unavailable | Backup #1 used if valid; day revalidated; others preserved. |
| S3 | User delayed | 90 minutes late on day 2 | Remaining day re-timed; lowest-priority item moved or dropped; completed items untouched. |
| S4 | Budget reduced | $500 -> $300 | Costly items replaced by purpose-preserving cheaper ones; total <= $300 or infeasible report. |
| S5 | Travel conflict | Leg exceeds 30-minute limit | Reorder or nearby replacement; leg now within limit. |
| S6 | Preference change | No museums, more outdoors | Museums replaced with outdoor items; others preserved. |
| S7 | Mode change | Transit -> walking | Matrix recomputed; violating legs repaired. |
| S8 | Too expensive activity | $40 cooking class over budget | Replacement shares a purpose tag (food/culture) and is cheaper. |
| S9 | Tourist/local | User sets 20% tourist | Plan within +/-20% of ratio or explains candidate shortage. |
| S10 | No feasible alternative | All candidates violate a hard rule | Stops within limits; names the constraint; suggests relaxation. |
| S11 | Provider outage | Routing API returns errors | Retry, fallback to cache/fixtures, degraded label; no crash. |
| S12 | Stale event (P1) | Event retrieved 3 days ago | Labelled "may have changed" with refresh action. |
| S13 | Rain (P2) | Rain forecast afternoon day 1 | Outdoor items swapped for indoor purpose-matched items. |

## 9. Data Contracts

The **current, implemented** data shapes live in `docs/contracts.md` and the Pydantic models in `backend/app/models/`. The Architecture & Agent Design document, Section 9, describes the fuller **target** model the contracts grow toward. When they disagree, `docs/contracts.md` wins for code. Changes to shared models require a team-chat message and a PR reviewed by at least two engineers because every agent depends on them.

### Source-of-truth order

| Question | Document that wins |
|---|---|
| What data shape does code use right now? | docs/contracts.md (and backend/app/models/) |
| What are we building this sprint, and by when? | 05 Sprint Plan & Backlog |
| What must the system do? | 02 SRS (this document) |
| Why does the product exist, what is in or out of scope? | 01 Product Vision & PRD |
| How should it be designed long-term? | 03 Architecture & Agent Design |
| How do we test it? | 04 Test Strategy |
| What does the UI look like and say? | 06 Design System & UX Copy |

## 10. Non-Functional Requirements

| ID | Category | Requirement |
|---|---|---|
| NFR-01 | Correctness | Hard constraints checked deterministically where data exists. |
| NFR-02 | Reliability | Provider failures handled with retry, fallback and error states. |
| NFR-03 | Performance | First itinerary for a 3-day demo trip in < 60 s median with live APIs on the Gemini free tier; replans in < 30 s; DEMO_MODE runs in < 10 s. |
| NFR-04 | Maintainability | Agents, tools, validators, models and routes in separate modules. |
| NFR-05 | Testability | Validators and graph paths independently testable with mocks. |
| NFR-06 | Observability | Every node, tool call and loop iteration traceable by run_id. |
| NFR-07 | Security | No secrets in source control or the browser bundle; secret scanning enabled. |
| NFR-08 | Usability | A new user can create a trip and understand problems and changes without help (hallway test). |
| NFR-09 | Explainability | Every replan records a human-readable reason per change. |
| NFR-10 | Reproducibility | All scenarios runnable in demo mode with deterministic fixtures. |
| NFR-11 | Portability | SQLite locally and Postgres in production through the same models. |
| NFR-12 | Scope control | Prefer a small reliable architecture over extra infrastructure. |
| NFR-13 | Cost control | Per-run caps on tool calls, repair iterations and tokens; per-IP rate limits. |
| NFR-14 | Accessibility | WCAG 2.1 AA for core flows; change states never conveyed by colour alone. |
| NFR-15 | Freshness | Time-sensitive data always displays its retrieved date. |

## 11. Security and Privacy

- Keys in environment variables or host secret settings; never committed; secret scanning on.
- Browser receives only a URL-restricted public map token.
- User input and tool results are untrusted data; tool text is never executed as instructions.
- No sensitive personal data collected beyond what planning needs; logs redact free text.
- No booking or payment capability.

## 12. Acceptance Criteria (MVP)

- A user can create a trip with form fields and free text, and see the extracted preferences with provenance labels.
- TripAgent produces a multi-day itinerary of real or fixture places with map-verified legs.
- Validators detect schedule, hours, travel-time, budget, avoid-list and diversity issues.
- High and medium priority activities show backups.
- Scenarios S1 to S10 pass in the automated suite; S11 passes in demo mode.
- Replans preserve >= 80% of unaffected activities on the benchmark.
- The UI shows changed, moved, preserved and removed items with reasons, and the map highlights changed legs.
- No loop runs past its cap; infeasible cases are explained.
- The trace panel shows nodes, tool calls and loop iterations for a run.
- The app runs at a public URL; no secrets in the repo or bundle.

## 13. Technology Stack

| Layer | Technology | Purpose |
|---|---|---|
| Language | Python 3.12 | Backend, agents, validators, tools. |
| Orchestration | LangGraph | State graph, conditional edges, checkpoints, interrupts. |
| LLM | Google Gemini API, free tier (Flash models) via google-genai and langchain-google-genai; structured output with Pydantic | Extraction, ordering proposals, repair choice, explanations. See ADR-007. |
| API | FastAPI + Pydantic | REST API and typed contracts. |
| Persistence | SQLAlchemy + Alembic; SQLite (dev), Postgres (prod) | Trips, versions, events. |
| Code layout | backend/app/{api,agents,graph,tools,validation,models}, frontend/src | All API routes under the /api prefix. |
| Maps and routing | Mapbox (Search, Directions, Matrix, GL JS) | Geometry, travel times, matrices, map rendering. |
| POI enrichment | Foursquare Places API (ADR-003) | Hours, price level, ratings, review counts, popularity, tips. |
| Events (P1) | Decision in Sprint 2 spike | Current events. |
| Frontend | Svelte + Vite + TypeScript | UI. See ADR-008. |
| Testing | pytest, Vitest + Svelte Testing Library, Playwright | Unit to end-to-end. |
| CI/CD | GitHub Actions | Tests, lint, benchmark, deploy on merge. |
| Observability | Structured JSON logs; optional LangSmith | Trace and debugging. |
