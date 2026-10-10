# Mission

_Sources: [01_product_vision_prd.md](../../docs/01_product_vision_prd.md), [02_srs.md](../../docs/02_srs.md), [03_architecture_agent_design.md](../../docs/03_architecture_agent_design.md), [CLAUDE.md](../../CLAUDE.md)_

## Mission statement

> **TripAgent builds personal, realistic city trips from real places and keeps them working
> when plans change.** When something goes wrong, it fixes only the part that broke and
> explains why.

TripAgent is an agentic travel-planning web app. A traveler describes a trip in their own
words. The app finds real places, builds a day-by-day plan on a map, and checks that the plan
works: opening hours, travel time and budget. When something changes ("I'm 90 minutes late",
"my budget is now $300", "switch to walking") it repairs only the affected part of the plan and
explains each change.

**Elevator pitch:** Other planners write you an itinerary once. TripAgent keeps a Plan B for
everything that matters, checks every leg against a real map, and when something changes it
fixes only the part that broke and tells you why.

## The problem we solve

Travelers planning 2-5 day city trips piece plans together from blogs, map apps and review
sites. They end up with either a tourist checklist or a plan that zig-zags across the city.
When something changes on the day, they re-plan from scratch on their phone.

| What the traveler says | What TripAgent does about it |
|---|---|
| "Every list has the same ten sights." | Reads free text, tags experience types, balances tourist vs. local places |
| "I spent half the day on the bus." | Plans from real travel times, clusters days by area, caps travel per leg |
| "The place was closed and the day fell apart." | Keeps checked backups ready and repairs only that part of the day |
| "The AI suggested an event from last year." | Uses live tools and shows when the information was checked |
| "I changed one thing and it rewrote my whole trip." | Saves each plan as a version and patches it instead of regenerating |

## Who we serve

| Persona | Needs most |
|---|---|
| **Maya, the explorer**: first visit to Seattle, 3 days, $500, transit, loves coffee and bookstores | Personalization, local favourites, variety |
| **Dev, the budget traveler**: student, 2 days in NYC, budget may drop mid-trip | Budget checks, cheaper swaps that keep the same purpose |
| **The Lee family**: parents and a child, walking pace, accessibility needs | Travel-time limits, indoor backups, a gentle pace |
| **Sam, the developer** (internal) | An agent trace and reproducible scenarios for debugging |

## Product pillars

1. **Personal**: understands free text, not just checkboxes.
2. **Varied**: days mix food, nature, culture, coffee and downtime.
3. **Grounded**: real places, real travel times, dates on time-sensitive data.
4. **Resilient**: important activities have backups that serve the same purpose.
5. **Adaptive**: changes are repaired locally, with an explained diff.

## Goals (measured on the demo benchmark)

| Goal | Target |
|---|---|
| G1 Plans are feasible | >= 95% of benchmark plans pass all hard constraints first time |
| G2 Plans feel personal and varied | >= 85% preference-extraction accuracy; >= 3 categories per full day |
| G3 Changes are handled locally | >= 90% of disruption scenarios repaired; >= 80% of unaffected activities kept |
| G4 The system is trustworthy | 100% of replans give a reason; 100% of events show a checked date |
| G5 The team learns real engineering | Public URL, CI green, every engineer demos an end-to-end feature they co-own |

## Principles (non-negotiable)

These apply to every line of code, every sprint.

1. **The LLM proposes; deterministic code decides.** Time math, budget sums, overlap, opening
   hours and travel-time checks are plain Python functions with tests, never LLM calls.
2. **Every loop has an exit.** A counter in state, a hard cap from config, a progress check,
   and a named end state: `PASS`, `INFEASIBLE`, `NEEDS_USER` or `ERROR`.
3. **Never invent data.** Missing price, hours or ratings stay "unknown". Every place keeps
   `source` and `retrieved_at`.
4. **Repair, do not regenerate.** Changes patch the current itinerary. Completed and locked
   activities are never modified.
5. **Demo mode always works.** `DEMO_MODE=true` runs the full app with no API keys, using mocks
   and recorded fixtures.
6. **Secrets stay secret.** Keys live only in `.env` or host settings, never in code, tests,
   logs or the frontend bundle.
7. **Everything leaves a trace.** Every node run, tool call, validation and replan writes an
   ExecutionEvent.
8. **Simple infrastructure.** One FastAPI service, one LangGraph workflow, one relational
   database. No queues, microservices or vector stores.
9. **Never hide uncertainty from the user.** Assumptions, unknown costs, missing hours and
   stale data are always labelled.
10. **Keep code beginner-readable.** Small functions, short comments where useful.

## Out of scope

- Booking flights, hotels or tickets; payments of any kind.
- Native mobile apps; real-time GPS tracking.
- User accounts and social sharing.
- Training or fine-tuning models.
- Equal quality for every city: two demo cities are tuned, the rest are best effort.
- Microservices, Kubernetes, message queues, vector databases.

## Definition of success on November 2, 2026

On the public URL, in demo mode, the team shows:

1. The Maya persona's description turned into a varied, map-checked 3-day Seattle plan.
2. Three live changes ("90 minutes late", "budget is now $300", "switch to walking"), each
   repaired locally with a change summary, route diff and trace.
3. Benchmark metrics meeting the goals above.
