# TripAgent: Sprint Plan & Product Backlog

_Roles, ceremonies, estimation, and Sprints 1-4 with story points and owners_

| Field | Value |
|---|---|
| Owner role | Engineering Manager + Product Owner; rotating Scrum Master |
| Team | Product Owner / Engineering Manager; five engineers in role areas: Preferences, Validation, Agent Graph, Tools, Frontend & Maps |
| Version | 2.3 (October 5, 2026) |
| Status | Living document, updated each sprint |
| Method | Sprint planning: goals, capacity, prioritized backlog, risks, Definition of Done |

## 1. How This Team Works

TripAgent is built with Scrum adapted for a part-time student team. Work is organized as **vertical slices**: every sprint ends with something a user can see working end-to-end, and every major story is shared by several people instead of being split into "frontend person" and "backend person".

### 1.1 Roles

| Role | Who | Accountable for |
|---|---|---|
| Product Owner | Project lead | Vision, backlog order, acceptance of stories, answering product questions within 24 h. |
| Engineering Manager / Tech Lead | Project lead (same person as PO in this program) | Architecture decisions (ADRs), code-review standards, unblocking, coaching. |
| Scrum Master (rotating) | A different engineer each sprint; nobody repeats before everyone has served | Runs ceremonies, keeps the board honest, tracks blockers and velocity. |
| Feature lead (per story) | Named in each story | Coordinates the slice across layers, owns the demo of that story. |
| Engineers | Five engineers, each with a home area (see 1.2) | Build, test, review, document. Each keeps a home area but works across layers. |

### 1.2 Home areas (not silos)

Owners in this plan are written as role names, not people. At the Sprint 1 kickoff the team mapped each role to a person (see the Person column); points in owner cells show how a story is split, for example "Preferences Eng. 3, Validation Eng. 2".

| Role | Person | Home area | Also works on |
|---|---|---|---|
| Preferences Eng. | Kaleb | Intake, change interpretation, preferences, ranking, diversity, golden sets | Backup purpose tags, Explainer wording, UX copy |
| Validation Eng. | Harshita | Models, validators, Backup Agent, impact analysis, scenario benchmark | CI, property tests, docs |
| Agent Graph Eng. | Sathwika | LangGraph workflow, loops, planner/scheduler, repair | Performance, approval loop |
| Tools Eng. | Nitin | FastAPI, tool adapters, Discovery Agent, maps/routing, events, fallback | Deployment, backup search |
| Frontend & Maps Eng. | Yahya | Frontend, map UI, trace UI, Explainer Agent, deployment, E2E | Design system, accessibility |

**AI agent leads.** Every engineer leads at least one LLM agent (agreed Oct 8, 2026). "Lead" means they build it, test it and answer questions about it; others help.

| Agent (see ARCH section 3) | Lead | Sprint |
|---|---|---|
| A1 Intake | Preferences Eng. (Kaleb) | 1 |
| A2 Discovery | Tools Eng. (Nitin) | 2 |
| A3 Itinerary Planner | Agent Graph Eng. (Sathwika) | 2 |
| A4 Backup | Validation Eng. (Harshita) | 3 |
| A5 Change Interpreter | Preferences Eng. (Kaleb) | 3 |
| A6 Repair | Agent Graph Eng. (Sathwika) | 3 |
| A7 Explainer | Frontend & Maps Eng. (Yahya) | 3 |

### 1.3 RACI for key activities

| Activity | PO / Tech Lead | Scrum Master | Feature lead | Engineers |
|---|---|---|---|---|
| Backlog ordering | A/R | C | C | C |
| Story acceptance | A | I | R | C |
| Estimation | I | R | C | A (team estimate) |
| Architecture decision (ADR) | A | I | R | C |
| Shared model change | C | I | R | A (2 reviewers) |
| Deployment | I | I | C | R/A (Frontend & Maps Eng., Tools Eng.) |
| Demo | I | R | R | R |

R = responsible, A = accountable, C = consulted, I = informed.

### 1.4 Ceremonies

| Ceremony | When | Length | Output |
|---|---|---|---|
| Sprint planning | Monday, after the review | 45 min | Sprint goal, committed stories, tasks, owners |
| Async stand-up | Mon / Wed / Fri in team chat | 5 min each | Yesterday, today, blockers |
| Mid-sprint check-in | Thursday | 20-30 min | Mini demo, blockers, decisions |
| Backlog refinement | Thursday, after check-in | 15 min | Next sprint stories meet Definition of Ready |
| Sprint review / demo | Monday | 30 min | Working increment shown on deployed URL |
| Retrospective | Monday, after review | 15 min | One process change to try next sprint |

Weekly demo format for each person: what I built, what user problem it solves, which contract it uses, what I tested, what is blocked, what I need from a teammate.

### 1.5 Board and workflow

```
BACKLOG -> READY -> IN PROGRESS -> CODE REVIEW -> TESTING -> DONE
```

- Use GitHub Projects. Import `backlog.csv` from this package to create the initial cards.
- Work-in-progress limit: 2 cards per person in IN PROGRESS.
- Branches: `feature/<story-id>-short-name`; PRs need 1 review (2 for shared models, graph edges or prompts).
- Every PR links its story id and states which tests were added.

### 1.6 Estimation and capacity

Stories use Fibonacci points (1, 2, 3, 5, 8, 13). Points measure complexity, uncertainty and effort together, not hours. Any story estimated at 13 is split before it enters a sprint.

**Capacity assumption (to recalibrate after Sprint 1):** five part-time engineers, roughly 8 to 10 focused hours each per week. Planning targets are set at about 75% of estimated capacity to leave room for learning and integration: about 25 points for each one-week sprint, with Sprint 4 deliberately lighter (about 13 points) to leave room for bug fixes and rehearsals. After Sprint 1, the team replaces this assumption with measured velocity.

### 1.7 Definition of Ready

- User story with persona and benefit.
- Acceptance criteria in Given/When/Then form.
- Contracts it touches are identified (models, endpoints, tools).
- Estimated by the team; <= 8 points.
- Dependencies listed and either done or mockable.

### 1.8 Definition of Done

- Acceptance criteria met on the deployed preview (from Sprint 1 onward).
- Unit/contract/graph tests added; CI green; benchmark not regressed.
- Follows shared contracts; no secrets exposed.
- ExecutionEvents emitted for new nodes, tools or loops.
- UI text follows the UX copy guide; states covered (loading, empty, error).
- Docs updated (README section, API doc or ADR).
- Reviewed and merged; demoed or demo-ready.

### 1.9 Story template

```
[US-22] Purpose-preserving replacement            Points: 8   Priority: P0
As a budget traveler, I want a replacement to keep the purpose of what I planned
so that swaps still feel worthwhile.

Acceptance criteria
  Given an itinerary with a $40 cooking class tagged {food, culture}
  And the budget is reduced so the class no longer fits
  When TripAgent repairs the plan
  Then the replacement shares at least one purpose tag with the class
  And it costs less than the class
  And all other activities on unaffected days are unchanged
  And the change summary states the reason

Tasks: purpose similarity fn (Preferences Eng.) | cascade in repair node (Agent Graph Eng.) |
       nearby search call (Tools Eng.) | cost check test (Validation Eng.) | reason text in UI (Frontend & Maps Eng.)
```

## 2. Release Roadmap

> **Final presentation: Monday, November 2, 2026.** Sprint 1 starts at the kickoff on Monday, October 5, which leaves four one-week sprints. Scope was reduced to fit: all P1 items are stretch goals, started only when a sprint goal is met. Every Monday is sprint review + planning for the next sprint.

| Sprint | Dates (2026) | Increment the user can see |
|---|---|---|
| 0 Inception | Done before Oct 5 | Project package, repo skeleton, scope agreed. |
| 1 Foundation | Mon Oct 5 - Sun Oct 11 | Describe a trip in words -> see it understood and stored, on a public URL. |
| 2 Grounded itinerary | Mon Oct 12 - Sun Oct 18 | A map-verified itinerary that is validated or honestly infeasible. |
| 3 Adaptive agent | Mon Oct 19 - Sun Oct 25 | Report a change -> local, purpose-preserving repair with explained diff. |
| 4 Hardening and demo | Mon Oct 26 - Sun Nov 1 | Reliable, tested, demo-proof product. Feature freeze Fri Oct 30. |
| Presentation | Mon Nov 2 | Final demo on the public URL. |

### Key dates

| Date | Milestone |
|---|---|
| Mon Oct 5 | Kickoff: roles assigned, data contracts agreed, Sprint 1 starts |
| Wed Oct 7 | Contracts merged as Pydantic models; everyone has a free Gemini key; ADR-003 spike results |
| Thu Oct 8 | Hello-world backend and frontend deployed (walking skeleton) |
| Mon Oct 12 | Sprint 1 review (trip understood, stored, deployed) + Sprint 2 planning |
| Mon Oct 19 | Sprint 2 review (validated itinerary with map) + Sprint 3 planning |
| Mon Oct 26 | Sprint 3 review (adaptive replanning demo) + Sprint 4 planning |
| Fri Oct 30 | Feature freeze; only bug fixes after this |
| Sat Oct 31 - Sun Nov 1 | Three full rehearsals on the public URL in DEMO_MODE |
| Mon Nov 2 | Final presentation |

## 3. Sprint Plans

### Done before Sprint 1

Sprint 0 (inception) was completed through the project package, the repository skeleton and the kickoff meeting. Its remaining items were folded into Sprint 1 stories: shared models into V-01, the API stub into US-01, the LangGraph practice loop into G-01, wireframes into US-01, and the golden set into US-17.

| Pri | ID | Item | Pts | Owners (points split) |
|---|---|---|---|---|
| P0 | S0-01 | Agree MVP scope, roles and demo city (project package + kickoff) | 2 | Product Owner + all |
| P0 | S0-02 | Walk through the agent graph and agree data contracts at kickoff | 3 | All |
| P0 | S0-08 | Repo skeleton, CI, PR template, CODEOWNERS, .env template | 2 | Tech Lead |

### Sprint 1: Foundation

**Dates:** Monday, October 5 to Sunday, October 11. Review Monday, October 12.

> **Sprint goal:** A user can describe a trip in their own words and see TripAgent understand, store and trace it, on a public URL.

| Pri | ID | Item | Pts | Owners (points split) |
|---|---|---|---|---|
| P0 | US-01 | Trip form (with screen sketches) -> POST /api/trips -> stored trip (vertical slice) | 5 | Frontend & Maps Eng. 2 UI, Tools Eng. 2 API, Validation Eng. 1 model |
| P0 | US-17 | Free-text "Tell us more" extraction with Gemini + provenance labels; 10-example answer key | 5 | Preferences Eng. 3 agent, Frontend & Maps Eng. 1 UI, Validation Eng. 1 tests |
| P0 | V-01 | Pydantic models from docs/contracts.md + validators v1: overlap, budget (with tests) | 5 | Validation Eng. 4, Agent Graph Eng. 1 |
| P0 | G-01 | Practice loop that stops after 3 tries, then graph v1: intake -> mock discovery -> persist, with ExecutionEvents | 3 | Agent Graph Eng. |
| P0 | T-01 | Tool interfaces + mock adapters + fixtures for the demo city | 3 | Tools Eng. |
| P0 | S0-05 | Spike: Mapbox + Foursquare fill rates for 30 places, cost per run, licence check (ADR-003) | 2 | Tools Eng. 1, Preferences Eng. 1 |
| P0 | D-01 | Hello-world deployment + /api/health + deploy on merge | 3 | Frontend & Maps Eng. 2, Tools Eng. 1 |
| P0 | FR-34 | Clarification loop L1 (max 2 rounds) + questions UI | 3 | Agent Graph Eng. 2, Frontend & Maps Eng. 1 |

**Committed (P0):** 29 points | **Stretch (P1/P2):** 0 points

FR-34 moved from the stretch list into Sprint 1 (P0) because loop engineering is the focus of the project; it matches the SRS, where FR-34 is P0.

**Sprint review demo:** Enter the Maya persona description on the deployed site and see the extracted preferences with "from your text" and "assumed" labels, stored and retrievable.

| Risk | Impact | Mitigation |
|---|---|---|
| Deployment surprises | Blocks Sprint 2 reviews on preview | Deploy hello-world by Thu Oct 8 |
| Contracts late | Everyone blocked | Validation Eng. merges models by Wed Oct 7; others build against docs/contracts.md meanwhile |
| Gemini free-tier rate limits | Slow testing | Each engineer uses their own AI Studio project; DEMO_MODE for routine work |
| Extraction accuracy low | Poor downstream plans | Golden set in CI; iterate prompt with examples |

### Sprint 2: Grounded itinerary

**Dates:** Monday, October 12 to Sunday, October 18. Review Monday, October 19.

> **Sprint goal:** Given a trip, TripAgent produces a varied, map-verified itinerary that passes validation or explains why it cannot.

| Pri | ID | Item | Pts | Owners (points split) |
|---|---|---|---|---|
| P0 | US-04 | Discovery Agent L2: Foursquare + Mapbox adapters, merge/dedupe, Premium-call budget, coverage report | 5 | Tools Eng. 3, Preferences Eng. 2 |
| P0 | US-18 | Experience typing, local/tourist heuristic + ratio, cost-range table | 3 | Preferences Eng. 2, Validation Eng. 1 |
| P0 | US-23/24 | Travel matrix per mode, day clustering, simple nearest-neighbour ordering | 5 | Tools Eng. 3, Agent Graph Eng. 2 |
| P0 | US-03 | Planner Agent + deterministic scheduler | 5 | Agent Graph Eng. 4, Preferences Eng. 1 |
| P0 | V-02 | Validators v2: opening hours, travel time, avoid list, diversity warning | 3 | Validation Eng. |
| P0 | L3-01 | Plan-Validate-Repair loop L3 with cap, stall check, INFEASIBLE explanation | 3 | Agent Graph Eng. 2, Validation Eng. 1 |
| P0 | US-07 | Itinerary view + map markers, routes, per-leg times | 5 | Frontend & Maps Eng. 4, Tools Eng. 1 |

**Committed (P0):** 29 points | **Stretch (P1/P2):** 0 points

**Load check:** 29 committed points. If Sprint 1 velocity comes in low, cut in this order: nearest-neighbour ordering (keep clustering), then the local/tourist ratio (keep experience typing), then the diversity warning.

**Sprint review demo:** Plan 3 days in Seattle with transit and a 30-minute limit; show clustered days on the map with per-leg times; then force an impossible budget and show the INFEASIBLE explanation.

| Risk | Impact | Mitigation |
|---|---|---|
| Matrix limits and cost | Slow or expensive planning | Per-cluster matrices; cache |
| Planner LLM ignores constraints | Many repair loops | LLM only orders; scheduler and validator enforce |

### Sprint 3: Adaptive agent (centerpiece)

**Dates:** Monday, October 19 to Sunday, October 25. Review Monday, October 26.

> **Sprint goal:** When the traveler's situation changes, TripAgent repairs only what broke, keeps the purpose of what it replaces, and explains the change.

| Pri | ID | Item | Pts | Owners (points split) |
|---|---|---|---|---|
| P0 | US-21 | Backup Agent: purpose tags + 1 validated backup per priority activity | 3 | Validation Eng. 2, Tools Eng. 1 |
| P0 | US-13-15a | Change Interpreter + POST /api/trips/{id}/changes + ChangeEvent validation | 5 | Preferences Eng. 2, Tools Eng. 2, Frontend & Maps Eng. 1 |
| P0 | FR-25b | Impact Analyzer (affected set) for budget, time, mode and closure | 3 | Validation Eng. 2, Agent Graph Eng. 1 |
| P0 | US-22 | Repair Agent with backup cascade L5, nearby search, purpose-preserving choice | 8 | Agent Graph Eng. 3, Tools Eng. 2, Preferences Eng. 2, Validation Eng. 1 |
| P0 | US-16 | Versioning, ReplanEvent diff, Explainer Agent (template fallback first) | 3 | Frontend & Maps Eng. 2, Agent Graph Eng. 1 |
| P0 | FR-51 | Adjust-trip dialog, change summary list, changed legs highlighted on map | 3 | Frontend & Maps Eng. 3 |
| P0 | S-01 | Scenario benchmark: S1-S6 automated with metrics report | 3 | Validation Eng. 2, all 1 |

**Committed (P0):** 28 points | **Stretch (P1/P2):** 0 points

**Vertical split example (US-22, 8 points):** Preferences Eng. writes purpose similarity (2), Agent Graph Eng. adds the cascade to the repair node (3), Tools Eng. adds nearby search with a travel-time radius (2), Validation Eng. writes the cost and locality tests (1). Frontend & Maps Eng. pairs with Preferences Eng. on the reason text in the change summary as part of FR-51.

**Sprint review demo:** Live: "I'm running 90 minutes late" then "My budget is now $300" then "switch to walking". Each shows the change summary, route diff and trace; scenarios S1-S6 pass.

| Risk | Impact | Mitigation |
|---|---|---|
| Largest sprint; integration heavy | Goal missed | Integrate daily on main behind feature flags; no stretch items this sprint |
| Repair thrashing | Timeouts, weird diffs | Stall check + cascade order tests from Sprint 2 |

### Sprint 4: Hardening and demo

**Dates:** Monday, October 26 to Sunday, November 1. Feature freeze Friday, October 30. Presentation Monday, November 2.

> **Sprint goal:** TripAgent is reliable, tested, documented and cannot be broken on demo day.

| Pri | ID | Item | Pts | Owners (points split) |
|---|---|---|---|---|
| P0 | R-01 | Retry/fallback L6 and caching; confirm DEMO_MODE covers every tool | 3 | Tools Eng. 2, Agent Graph Eng. 1 |
| P0 | R-02 | Scenarios S7-S10 + one E2E flow (Playwright) | 2 | Validation Eng. 1, Frontend & Maps Eng. 1 |
| P0 | R-03 | Accessibility and UX copy pass | 2 | Frontend & Maps Eng. 2, Preferences Eng. 1 |
| P0 | R-04 | Gemini rate-limit handling, token caps, quick performance check | 2 | Agent Graph Eng. 2 |
| P0 | R-05 | README, runbook, API docs, architecture diagram | 2 | All (Validation Eng. coordinates) |
| P0 | R-06 | Demo script + three clean rehearsals on the public URL | 2 | All (Product Owner reviews) |

**Committed (P0):** 13 points | **Stretch (P1/P2):** 0 points

**Sprint review demo:** Final presentation: problem, architecture, three live scenarios on the public URL, benchmark metrics, retrospective.

| Risk | Impact | Mitigation |
|---|---|---|
| Provider outage on demo day | Demo fails | DEMO_MODE toggle rehearsed |
| Last-minute features | Regressions | Feature freeze Friday, October 30 |

### Stretch goals (only after a sprint goal is met)

These stay in the backlog but are not committed. Pick them up in this order only if a sprint goal is already met.

| Pri | ID | Item | Pts | Owners (points split) |
|---|---|---|---|---|
| P1 | US-29 | Undo to previous version | 2 | Frontend & Maps Eng. 1, Agent Graph Eng. 1 |
| P1 | FR-53 | Approval before major changes (L7) | 3 | Agent Graph Eng. 2, Frontend & Maps Eng. 1 |
| P1 | T-02 | Trace panel (list of events for a run) | 2 | Frontend & Maps Eng. |
| P1 | US-19 | Diversity re-rank during candidate ranking | 2 | Preferences Eng. |
| P1 | US-20a | Spike: events provider and freshness labels | 2 | Tools Eng. |
| P1 | US-20 | Current events with retrieved date + stale labels | 5 | Tools Eng. 3, Frontend & Maps Eng. 2 |
| P1 | US-25 | Along-route search ("coffee on the way") | 5 | Tools Eng. 3, Frontend & Maps Eng. 2 |
| P2 | US-28 | Weather-triggered replanning | 5 | Unassigned |

## 4. Epics and Traceability

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

## 5. Metrics the Team Tracks

| Metric | Why |
|---|---|
| Velocity (points done per sprint) | Calibrates future commitments. |
| Sprint goal met (yes/no) | Focus on outcomes over points. |
| PR cycle time (open to merge) | Detects review bottlenecks. |
| Benchmark metrics trend | Product quality (see Test Strategy). |
| Carryover points | Honest planning; discuss causes in retro. |

## 6. Kickoff Meeting Agenda (Monday, October 5)

1. Product Owner presents the vision and personas (15 min).
2. Tech lead draws the agent graph and the seven loops on the whiteboard (20 min).
3. Each engineer answers: "What does my part need from the previous step, and what does it return?" (20 min).
4. Agree the shared models: Trip, Requirements, Place, Activity, TripState, ValidationResult, ChangeEvent, ReplanEvent (20 min).
5. Walk through the Sprint 1 cards; pick the first Scrum Master (10 min).
