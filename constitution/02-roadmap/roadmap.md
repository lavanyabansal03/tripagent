# Roadmap

_Sources: [05_sprint_plan_backlog.md](../../docs/05_sprint_plan_backlog.md), [backlog.csv](../../docs/backlog.csv), [01_product_vision_prd.md](../../docs/01_product_vision_prd.md) section 3.8_

**Hard deadline: final presentation Monday, November 2, 2026.** Four one-week sprints follow
the October 5 kickoff. Each sprint ends with something a user can see working from start to
finish. P0 items are committed. P1 items are stretch goals, started only after a sprint goal is met.

## At a glance

| Sprint | Dates (2026) | Goal: what the user can see | Points |
|---|---|---|---|
| 0 Inception | Before Oct 5 (done) | Project package, repo skeleton, scope agreed | 7 |
| 1 Foundation | Mon Oct 5 - Sun Oct 11 | Describe a trip in words, see it understood and stored, on a public URL | 29 |
| 2 Grounded itinerary | Mon Oct 12 - Sun Oct 18 | A map-checked itinerary that passes validation or honestly explains why it can't | 29 |
| 3 Adaptive agent | Mon Oct 19 - Sun Oct 25 | Report a change and get a local, purpose-preserving repair with an explained diff | 28 |
| 4 Hardening and demo | Mon Oct 26 - Sun Nov 1 | Reliable, tested product that can't break on demo day. **Feature freeze Fri Oct 30** | 13 |
| Presentation | Mon Nov 2 | Final demo on the public URL | — |

## Key dates

| Date | Milestone |
|---|---|
| Mon Oct 5 | Kickoff: roles assigned, data contracts agreed, Sprint 1 starts |
| Wed Oct 7 | Contracts merged as Pydantic models; everyone has a Gemini key; ADR-003 spike results |
| Thu Oct 8 | Hello-world backend and frontend deployed (walking skeleton) |
| Mon Oct 12 | Sprint 1 review + Sprint 2 planning |
| Mon Oct 19 | Sprint 2 review + Sprint 3 planning |
| Mon Oct 26 | Sprint 3 review + Sprint 4 planning |
| Fri Oct 30 | Feature freeze: bug fixes only after this |
| Sat Oct 31 - Sun Nov 1 | Three full rehearsals on the public URL in DEMO_MODE |
| Mon Nov 2 | Final presentation |

---

## Task tracker

The `Status` column is filled in by comparing each task against the code. See the
[constitution README](../README.md) for status values. Owners are role names; see
[team.md](../05-team/team.md) for who holds each role.

### Sprint 0: Inception (done before Oct 5)

| ID | Task | Pts | Owners | Refs | Status |
|---|---|---|---|---|---|
| S0-01 | Agree MVP scope, roles and demo city | 2 | Product Owner + all | PRD | Done (per backlog) |
| S0-02 | Walk through the agent graph and agree data contracts | 3 | All | ARCH 3-6 | Done (per backlog) |
| S0-08 | Repo skeleton, CI, PR template, CODEOWNERS, .env template | 2 | Tech Lead | TEST 10 | Done (per backlog) |

### Sprint 1: Foundation (Oct 5 - Oct 11)

> **Goal:** A user can describe a trip in their own words and see TripAgent understand, store
> and trace it, on a public URL.
>
> **Demo:** Enter the Maya description on the deployed site; see extracted preferences with
> "from your text" and "assumed" labels, stored and retrievable.

| ID | Task | Pts | Owners | Refs | Status |
|---|---|---|---|---|---|
| US-01 | Trip form (with screen sketches) -> `POST /api/trips` -> stored trip | 5 | Frontend 2, Tools 2, Validation 1 | FR-01 | Not verified |
| US-17 | "Tell us more" free-text extraction with Gemini + provenance labels; 10-example answer key | 5 | Preferences 3, Frontend 1, Validation 1 | FR-02, FR-33 | Not verified |
| V-01 | Pydantic models from `docs/contracts.md` + validators v1: overlap, budget (with tests) | 5 | Validation 4, Agent Graph 1 | FR-07, FR-10 | Not verified |
| G-01 | Practice loop that stops after 3 tries, then graph v1: intake -> mock discovery -> persist, with ExecutionEvents | 3 | Agent Graph | FR-20, FR-21 | Not verified |
| T-01 | Tool interfaces + mock adapters + fixtures for the demo city | 3 | Tools | FR-55 | Not verified |
| S0-05 | Spike: Mapbox + Foursquare fill rates for 30 places, cost per run, licence check | 2 | Tools 1, Preferences 1 | ADR-003 | Not verified |
| D-01 | Hello-world deployment + `/api/health` + deploy on merge | 3 | Frontend 2, Tools 1 | FR-54 | Not verified |
| FR-34 | Clarification loop (L1, max 2 rounds) + questions UI. Moved from stretch: loop engineering is the focus | 3 | Agent Graph 2, Frontend 1 | FR-34 | Not verified |

### Sprint 2: Grounded itinerary (Oct 12 - Oct 18)

> **Goal:** Given a trip, TripAgent produces a varied, map-checked itinerary that passes
> validation or explains why it cannot.
>
> **Demo:** Plan 3 days in Seattle by transit with a 30-minute limit; show clustered days on
> the map with per-leg times; force an impossible budget and show the INFEASIBLE explanation.
>
> **If behind, cut in this order:** nearest-neighbour ordering -> local/tourist ratio -> diversity warning.

| ID | Task | Pts | Owners | Refs | Status |
|---|---|---|---|---|---|
| US-04 | Discovery Agent (L2): Foursquare + Mapbox adapters, merge/dedupe, Premium-call budget, coverage report | 5 | Tools 3, Preferences 2 | FR-03, FR-56-58 | Not verified |
| US-18 | Experience typing, local/tourist heuristic + ratio, cost-range table | 3 | Preferences 2, Validation 1 | FR-10, FR-35, FR-36 | Not verified |
| US-23/24 | Travel matrix per mode, day clustering, simple nearest-neighbour ordering | 5 | Tools 3, Agent Graph 2 | FR-45-47 | Not verified |
| US-03 | Planner Agent + deterministic scheduler | 5 | Agent Graph 4, Preferences 1 | FR-06 | Not verified |
| V-02 | Validators v2: opening hours, travel time, avoid list, diversity warning | 3 | Validation | FR-08, FR-09, FR-11, FR-37 | Not verified |
| L3-01 | Plan-Validate-Repair loop (L3) with cap, stall check, INFEASIBLE explanation | 3 | Agent Graph 2, Validation 1 | FR-16, FR-17 | Not verified |
| US-07 | Itinerary view + map markers, routes, per-leg times | 5 | Frontend 4, Tools 1 | FR-18 | Not verified |

### Sprint 3: Adaptive agent (Oct 19 - Oct 25), the centerpiece

> **Goal:** When the traveler's situation changes, TripAgent repairs only what broke, keeps
> the purpose of what it replaces, and explains the change.
>
> **Demo:** "I'm running 90 minutes late" -> "My budget is now $300" -> "switch to walking".
> Each shows the change summary, route diff and trace; scenarios S1-S6 pass.

| ID | Task | Pts | Owners | Refs | Status |
|---|---|---|---|---|---|
| US-21 | Backup Agent: purpose tags + 1 validated backup per priority activity | 3 | Validation 2, Tools 1 | FR-40, FR-41 | Not verified |
| US-13-15a | Change Interpreter + `POST /api/trips/{id}/changes` + ChangeEvent validation | 5 | Preferences 2, Tools 2, Frontend 1 | FR-25, FR-32 | Not verified |
| FR-25b | Impact Analyzer (affected set) for budget, time, mode and closure | 3 | Validation 2, Agent Graph 1 | FR-25 | Not verified |
| US-22 | Repair Agent with backup cascade (L5), nearby search, purpose-preserving choice | 8 | Agent Graph 3, Tools 2, Preferences 2, Validation 1 | FR-42-44, FR-48 | Not verified |
| US-16 | Versioning, ReplanEvent diff, Explainer Agent (template fallback first) | 3 | Frontend 2, Agent Graph 1 | FR-31, FR-52 | Not verified |
| FR-51 | Adjust-trip dialog, change summary list, changed legs highlighted on map | 3 | Frontend 3 | FR-31, FR-51 | Not verified |
| S-01 | Scenario benchmark: S1-S6 automated with metrics report | 3 | Validation 2, all 1 | TEST 6 | Not verified |

### Sprint 4: Hardening and demo (Oct 26 - Nov 1)

> **Goal:** TripAgent is reliable, tested, documented and cannot be broken on demo day.
> **Feature freeze Friday, October 30.**

| ID | Task | Pts | Owners | Refs | Status |
|---|---|---|---|---|---|
| R-01 | Retry/fallback (L6) and caching; confirm DEMO_MODE covers every tool | 3 | Tools 2, Agent Graph 1 | FR-22, FR-55 | Not verified |
| R-02 | Scenarios S7-S10 + one E2E flow (Playwright) | 2 | Validation 1, Frontend 1 | TEST 6, 8 | Not verified |
| R-03 | Accessibility and UX copy pass | 2 | Frontend 2, Preferences 1 | DESIGN | Not verified |
| R-04 | Gemini rate-limit handling, token caps, quick performance check | 2 | Agent Graph 2 | NFR-03, NFR-13 | Not verified |
| R-05 | README, runbook, API docs, architecture diagram | 2 | All (Validation coordinates) | DOCS | Not verified |
| R-06 | Demo script + three clean rehearsals on the public URL | 2 | All (PO reviews) | PRD 3.6 | Not verified |

### Stretch goals (only after a sprint goal is met, in this order)

| Pri | ID | Task | Pts | Owners | Refs | Status |
|---|---|---|---|---|---|---|
| P1 | US-29 | Undo to previous version | 2 | Frontend 1, Agent Graph 1 | FR-52 | Not verified |
| P1 | FR-53 | Approval before major changes (L7) | 3 | Agent Graph 2, Frontend 1 | FR-53 | Not verified |
| P1 | T-02 | Trace panel (list of events for a run) | 2 | Frontend | FR-20 | Not verified |
| P1 | US-19 | Diversity re-rank during candidate ranking | 2 | Preferences | FR-37 | Not verified |
| P1 | US-20a | Spike: events provider and freshness labels | 2 | Tools | FR-38 | Not verified |
| P1 | US-20 | Current events with checked date + stale labels | 5 | Tools 3, Frontend 2 | FR-38, FR-39 | Not verified |
| P1 | US-25 | Along-route search ("coffee on the way") | 5 | Tools 3, Frontend 2 | FR-49 | Not verified |
| P2 | US-28 | Weather-triggered replanning | 5 | Unassigned | US-28 | Not verified |

---

## Epics

| Epic | Covers | Sprints |
|---|---|---|
| E0 Inception | Scope, architecture, contracts | 0 |
| E1 Trip setup and requirements | US-01, 02, 17; FR-01, 02, 33, 34 | 1 |
| E2 Discovery and ranking | US-04, 18, 19, 20; FR-03-05, 35-39 | 1-3 |
| E3 Itinerary generation | US-03; FR-06 | 2 |
| E4 Validation | US-05, 06; FR-07-12 | 1-2 |
| E5 Agent graph and replanning | US-08-16, 21, 22, 29; FR-13-17, 25-32, 40-44, 52, 53 | 1-4 |
| E6 Maps | US-07, 23-26; FR-18, 45-51 | 2-3 |
| E7 User interface | All UI stories | 0-4 |
| E8 Reliability and delivery | US-12, 27; FR-19-22, 54, 55; NFRs | 0-4 |

## Future (P2, design for but do not build)

- Weather-triggered replanning (keep `ChangeEvent.type` open for `weather`).
- Accounts, saved and shared trips (keep trip ids non-guessable).
- Calendar / ICS export.
- Multi-city trips and hotels as day anchors (optional `day_anchor` field).

## Working rules that shape the roadmap

- **Definition of Done:** acceptance criteria met on the deployed preview, tests added, CI
  green, contracts followed, ExecutionEvents emitted, UI copy from the guide, docs updated,
  reviewed and merged.
- **Work-in-progress limit:** 2 cards per person.
- **Story size:** anything estimated at 13 points is split before it enters a sprint.
- **Capacity:** about 25 points per sprint (Sprint 4 about 13), recalibrated after Sprint 1.
