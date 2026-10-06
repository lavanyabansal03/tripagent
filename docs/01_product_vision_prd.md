# TripAgent: Product Vision & PRD

_Problem exploration, personas, assumptions, and prioritized requirements_

| Field | Value |
|---|---|
| Owner role | Product Owner |
| Team | Product Owner / Engineering Manager; five engineers in role areas: Preferences, Validation, Agent Graph, Tools, Frontend & Maps |
| Version | 2.3 (October 5, 2026) |
| Status | Living document, updated each sprint |
| Method | Product brainstorming (problem exploration, ideation, assumption testing) + PRD |

## 1. Product Vision

> **TripAgent is an agentic travel planning and adaptive itinerary system.** It builds personalized, geographically efficient trips from real places and current information, and keeps the plan working when the traveler's time, budget, preferences, transportation or activity availability changes.

**Elevator pitch:** Other planners write you an itinerary once. TripAgent keeps a Plan B for everything that matters, checks every leg against a real map, and when something changes it fixes only the part that broke and tells you why.

| Product pillar | What it means for the user | Differentiator vs a chatbot itinerary |
|---|---|---|
| Personal | Understands "Tell us more about your trip" text, not just checkboxes. Balances tourist sights with places locals enjoy. | Structured, editable preferences with "we assumed" labels. |
| Varied | Days mix food, nature, culture, coffee and downtime instead of four museums in a row. | Diversity is a measured planning rule. |
| Grounded | Real places, real travel times, current events with a "retrieved" date. | Tool-verified data with provenance. |
| Resilient | Every key activity has backups that keep the same purpose. | Pre-validated Plan B, not "ask again". |
| Adaptive | Late, cheaper, rainy, walking instead of transit: the plan adjusts locally. | Minimal-change repair with an explained diff. |

## 2. Problem Exploration (Brainstorm Output)

### 2.1 Who has the problem and what do they do today?

Travelers planning 2 to 5 day city trips spend hours cross-referencing blogs, map apps, review sites and event listings. The result is usually either a tourist checklist or an unrealistic plan that zig-zags across the city. When something changes on the day (a closure, a delay, a cost surprise), they re-plan on their phone with no context about the rest of the day.

| Symptom the user describes | Root cause | TripAgent response |
|---|---|---|
| "Every list has the same ten sights." | Sources rank by popularity; no model of the user's taste or of "local" places. | Free-text extraction + experience-type tagging + tourist/local ratio. |
| "I spent half the day on the bus." | Plans are built from lists, not from travel times. | Travel matrix, clustering, route order, max-travel constraint. |
| "The place was closed and the day fell apart." | No alternatives prepared; re-planning starts from zero. | Pre-validated, purpose-preserving backups and local repair. |
| "The AI suggested an event from last year." | Static model knowledge. | Event tools with retrieved_at and stale-data labels. |
| "I changed one thing and it rewrote my whole trip." | One-shot generation. | Versioned itinerary and targeted patches. |

### 2.2 Personas

| Persona | Context | Needs most | Primary stories |
|---|---|---|---|
| Maya, the explorer | First visit to Seattle, 3 days, $500, transit, loves coffee, photography, bookstores; wants "places locals actually enjoy". | Personalization, local balance, diversity | US-17, US-18, US-19 |
| Dev, the budget traveler | Student, 2 days in NYC, tight budget that may drop mid-trip. | Budget validation, cheaper purpose-preserving swaps | US-06, US-13, US-22 |
| The Lee family | Parents + child, walking pace, accessibility needs, sensitive to rain and long transfers. | Travel-time limits, indoor backups, pace | US-23, US-24, US-28 |
| Sam, the developer (internal) | Team member debugging the agent. | Trace, reproducible scenarios | US-12 |

### 2.3 Solution ideas considered

The team generated options along different dimensions before converging. Chosen ideas are marked.

| Idea | Scope | Verdict |
|---|---|---|
| Pre-computed backups for every key activity (Plan B) | Medium | **Chosen (P0).** Core resilience story, cheap to reuse candidate pool. |
| Purpose-preserving replacement (keep "why", not just "what") | Medium | **Chosen (P0).** Makes swaps feel intelligent. |
| Map as constraint validator (travel matrix + clustering) | Medium | **Chosen (P0).** Needed for realistic plans. |
| Diversity scoring | Small | **Chosen (P0)** as a soft rule. |
| Current events and trending spots | Medium, data-dependent | **P1.** Valuable, but depends on an events provider decision. |
| Weather-aware re-plan (rain -> indoor) | Medium | **Stretch (P2)** unless events and backups finish early. |
| Inversion: let the user build, agent only critiques | Small | Rejected as primary flow; kept as "swap manually" feature. |
| Removal: no LLM planning, pure solver | Large | Rejected: loses free-text understanding and explanations. |
| Booking and payments | Large, risky | Out of scope. |

### 2.4 Assumptions and how we test them

| Assumption | Type | Confidence | Cheapest test (Sprint 1) |
|---|---|---|---|
| Foursquare (with Mapbox) returns enough hours, price level and rating data for demo cities. | Feasibility | **Medium - riskiest** (was Low before ADR-003) | Spike: 30 places per demo city through both providers; targets hours >= 70% for food, price level >= 60%, ratings >= 80%. Fallback: curated seed data. |
| A rule based on rating and review-count percentiles is a fair proxy for "local favourite". | Solution | Medium | Label 20 places per city by hand; rule should agree on >= 70%. Show as "Local pick", never as fact. |
| An LLM can reliably extract structured preferences from free text. | Feasibility | Medium | Golden set of 25 trip descriptions; measure field accuracy >= 85%. |
| Users value "local" places over top sights. | User | Medium | Make tourist/local ratio a slider rather than a fixed rule; 5 hallway tests. |
| Pre-computed backups stay valid long enough to be useful. | Solution | Medium | Always revalidate at swap time; track backup hit-rate metric. |
| Travel-time matrices are affordable at demo scale. | Feasibility | High | Cost estimate in spike; cache by cluster. |
| A 5-person student team can ship the P0 scope by November 2 (four one-week sprints). | Delivery | Medium | Walking skeleton deployed by Oct 8; recalibrate scope with Sprint 1 velocity; P1 items are stretch only. |

## 3. Product Requirements (PRD)

### 3.1 Problem statement

Travelers who want a personal, realistic city itinerary must stitch together scattered sources, and the result breaks as soon as conditions change. Existing AI planners generate a one-shot list that ignores travel time, repeats the same kind of activity, relies on stale knowledge and has no fallback. The cost is wasted trip time, missed experiences and a plan the user stops trusting.

### 3.2 Goals

| Goal | Type | Measure (demo benchmark) |
|---|---|---|
| G1 Plans are feasible | User outcome | >= 95% of benchmark itineraries pass all hard constraints on first delivery. |
| G2 Plans feel personal and varied | User outcome | >= 85% preference-extraction accuracy; >= 3 distinct categories per full day; stated interests each covered. |
| G3 Changes are handled locally | User outcome | >= 90% of disruption scenarios repaired; >= 80% of unaffected activities preserved. |
| G4 The system is trustworthy | User outcome | 100% of replans have a trigger and reason; 100% of events show a retrieved date. |
| G5 The team learns real engineering | Program outcome | Deployed public URL, CI green, every mentee demos an end-to-end feature they co-own. |

### 3.3 Non-goals

| Non-goal | Why out of scope |
|---|---|
| Booking flights, hotels or tickets; payments | Legal and financial risk; distracts from agent design. |
| Native mobile app, real-time GPS tracking | Responsive web covers the demo; GPS adds privacy scope. |
| User accounts and social sharing | Not needed to demonstrate agent behaviour; revisit post-MVP. |
| Training or fine-tuning models | Time and data cost; prompting + validation is enough. |
| Planning for every city in the world with equal quality | Two demo cities are tuned; others work "best effort". |

### 3.4 User stories by persona

Existing stories US-01 to US-16 remain (see SRS v2). New stories added in this version:

| ID | Persona | Story |
|---|---|---|
| US-17 | Maya | As a first-time visitor, I want to describe my trip in my own words so that TripAgent understands preferences that do not fit a form. |
| US-18 | Maya | As a traveler who dislikes crowds, I want to choose how much of my trip is tourist sights versus local favourites so that the plan matches my style. |
| US-19 | Maya | As a traveler, I want each day to include a variety of experiences so that my trip does not feel repetitive. |
| US-20 | Maya | As a traveler, I want to see events and seasonal activities happening during my dates, with when the info was checked, so that I do not miss or trust stale things. |
| US-21 | All | As a traveler, I want every important activity to have ready alternatives so that one problem does not ruin my day. |
| US-22 | Dev | As a budget traveler, I want a replacement to keep the purpose of what I planned (for example food + culture) so that swaps still feel worthwhile. |
| US-23 | Lee family | As a traveler with limited stamina, I want to cap travel time between activities so that we do not spend the day in transit. |
| US-24 | Lee family | As a traveler, I want each day grouped by area and ordered sensibly so that we do not zig-zag across the city. |
| US-25 | Maya | As a traveler, I want to find a coffee shop along my current route so that I do not detour. |
| US-26 | All | As a traveler, I want to switch between walking, transit and driving and see whether my plan still works. |
| US-27 | Stakeholders / reviewers | As a stakeholder, I want a public demo URL so that TripAgent can be evaluated without a local setup. |
| US-28 | Lee family | As a traveler, I want outdoor plans swapped for indoor ones if rain is forecast. (Stretch) |
| US-29 | All | As a traveler, I want to undo an adjustment I do not like so that I stay in control. |

#### Edge-case stories

- No feasible plan exists (budget too low for the city and dates): the user sees which constraint blocks the plan and suggested relaxations.
- The free text contradicts the form (form says driving, text says "no car"): TripAgent asks one clarification question.
- An event in the plan was retrieved more than 24 hours ago: it shows a "may have changed" label and a refresh action.
- No backups could be found for an activity: the activity shows "No backup found" rather than hiding the gap.

### 3.5 Requirements by priority

#### P0: Must have for the MVP demo

| Requirement | Acceptance criteria |
|---|---|
| Trip setup with form + "Tell us more" free text | Given a description with interests, avoidances and a travel limit, when the trip is created, then the structured preferences show each field with an "from your text" or "assumed" label. |
| Experience-type tagging and tourist/local ratio | Every candidate has >= 1 experience type; local/tourist labels come from the ADR-003 heuristic; a ratio of 30% tourist yields a plan within +/-20% of the target when enough candidates exist. |
| Estimated costs with labels | Every activity shows a known price, an "About $x-y" range, "Free" or "Cost unknown"; the budget check uses upper bounds when strict. |
| Diversity rule | Full days contain >= 3 categories and no more than 2 consecutive activities of the same category, unless the user asks otherwise; violations appear as soft warnings. |
| Map-verified travel times per mode | Every leg shows a provider travel time; any leg above the user limit is flagged as a hard violation. |
| Geographic clustering and route order | Benchmark days have total travel <= 25% of active time, or show a warning. |
| Backups for priority activities | High and medium priority activities have >= 1 (target 2) validated backups shown in the activity card. |
| Purpose-preserving repair | In the "too expensive" scenario, the replacement shares >= 1 purpose tag with the original and costs less. |
| Adaptive replanning (budget, time, preference, mode, closure) | Each scenario in SRS v2 Section 11 produces a validated plan or an infeasibility explanation within 3 repair iterations. |
| Change summary + route diff | After a replan, the UI lists changed, moved, preserved, removed items with reasons, and the map highlights changed legs. |
| Agent trace | Every node, tool call and loop iteration appears in the trace panel for the run. |
| Public deployment | A public URL runs the full flow; secrets are not in the repo or the browser bundle; /health returns OK. |

#### P1: Should have (stretch goals under the November 2 timeline)

| Requirement | Acceptance criteria |
|---|---|
| Current events with freshness labels | Events for trip dates appear with "Checked <date>"; items older than 24 h are labelled. |
| Along-route search | "Coffee on the way" returns places with detour <= 10 min on the active leg. |
| Approval before major changes | Replans that change > 2 activities or raise cost show a before/after proposal first. |
| Undo / version history | User can restore the previous version in one click. |
| Manual backup swap | User can pick any listed backup; the day is revalidated. |

#### P2: Future considerations (design for, do not build)

- Weather-triggered replanning (keep the ChangeEvent type open for `weather`).
- Accounts, saved and shared trips (keep trip ids non-guessable).
- Calendar/ICS export.
- Multi-city trips and hotels as day anchors (keep a `day_anchor` field optional in the model).

### 3.6 Success metrics

| Metric | Leading or lagging | Target |
|---|---|---|
| Hard-constraint pass rate on benchmark | Leading (every PR) | >= 95% |
| Replan success rate | Leading | >= 90% of scenarios |
| Change locality (unaffected preserved) | Leading | >= 80% |
| Backup hit rate (repair solved by a stored backup) | Leading | >= 60% |
| Preference extraction accuracy (golden set) | Leading | >= 85% field-level |
| Median time to first itinerary (demo city, live APIs, Gemini free tier) | Leading | < 60 s (replan < 30 s), per SRS NFR-03 |
| Hallway test: "this plan feels like me" (1-5) | Lagging | Average >= 4 across 5 testers |
| Demo reliability in DEMO_MODE | Lagging | 3 consecutive clean runs before final demo |

### 3.7 Open questions

| Question | Owner | Blocking? |
|---|---|---|
| Do Foursquare fill rates meet spike targets for our demo cities, and do licence terms allow our caching and fixtures? (ADR-003) | Engineering (Tools Eng., Preferences Eng.) | Yes, by Wed Oct 7 |
| Which events provider, and is its free tier enough?  | Engineering (Tools Eng.) | No (P1) |
| Tune local/hidden thresholds after hand-labelling 20 places per city | Product Owner + Preferences Eng. | No, Sprint 2 |
| What counts as a "major change" for approval? | Product + Design | No |
| Which demo city (Seattle by default) and an optional second city? | Product Owner | Yes, Sprint 1 |
| Hosting choice for frontend and backend within budget | Engineering (Frontend & Maps Eng.) | Yes, Sprint 1 |

### 3.8 Timeline considerations

**Hard deadline: final presentation on Monday, November 2, 2026.** Four one-week sprints follow the kickoff on Monday, October 5: Sprint 1 walking skeleton deployed (Oct 5 - Oct 11); Sprint 2 grounded, validated itinerary with map (Oct 12 - Oct 18); Sprint 3 backups and adaptive replanning (Oct 19 - Oct 25); Sprint 4 hardening and rehearsals (Oct 26 - Nov 1), with feature freeze on Friday, October 30.

Because the timeline is about four weeks, **all P1 requirements are stretch goals**: they are built only after the sprint goal is met. The P0 list is the committed MVP. Details and points are in the Sprint Plan & Backlog document.
