# CLAUDE.md — TripAgent

TripAgent is an AI trip-planning web app built by a five-person student team.
A user describes a trip in their own words; the app finds real places, builds a
day-by-day plan on a map, checks that it actually works, and when something changes
("I'm 90 minutes late", "my budget is now $300") it repairs only the part that broke
and explains why. Final presentation: **Monday, November 2, 2026**.

## Before you write code
0. For the big picture (mission, roadmap with task status, tech stack, team, open
   questions) read `constitution/README.md`. It summarizes `docs/`; the docs still win.
1. Check which sprint we are in and what is in scope: `docs/05_sprint_plan_backlog.md`.
   Do not build stories from later sprints or the stretch list unless asked.
2. Use the data shapes in `docs/contracts.md` and `backend/app/models/`.
3. If a task touches requirements or design, read the relevant section of the docs
   below. Do not read every document for every task.

## Source-of-truth order (when documents disagree)
| Question | Wins |
|---|---|
| What data shape does code use right now? | `docs/contracts.md` + `backend/app/models/` |
| What are we building this sprint, by when? | `docs/05_sprint_plan_backlog.md` |
| What must the system do? (US-xx, FR-xx, NFR-xx) | `docs/02_srs.md` |
| Why / what is in or out of scope? | `docs/01_product_vision_prd.md` |
| Long-term design: agents, loops, state, ADRs | `docs/03_architecture_agent_design.md` |
| How to test it | `docs/04_test_strategy.md` |
| UI tokens, components, exact UI text | `docs/06_design_system_ux_copy.md` |
| Beginner setup and roles | `docs/00_getting_started.md` |

`docs/03` section 9.1 is the **target** data model. `docs/contracts.md` is the **current**
one. Grow toward 9.1 only when a story needs it.

## Stack
- Backend: Python 3.12, FastAPI, Pydantic v2, LangGraph, SQLAlchemy (SQLite locally)
- LLM: **Google Gemini API, free tier, Flash models** via `google-genai` /
  `langchain-google-genai`. **Never use OpenAI.** Model names live in `backend/app/config.py`.
- Places and maps: Foursquare (venue details) + Mapbox (routing, travel times, map)
- Frontend: Svelte + Vite + TypeScript (ADR-008; replaced React)
- Tests: pytest, Vitest; lint with ruff

## Layout
```
backend/app/
  api/         FastAPI routes, all under /api          (Tools Eng.)
  agents/      LLM-backed steps (intake, planner, ...)  (Preferences + Agent Graph Eng.)
  graph/       LangGraph workflow, state, routing       (Agent Graph Eng.)
  tools/       Foursquare/Mapbox adapters + mocks       (Tools Eng.)
  validation/  pure-function validators                (Validation Eng.)
  models/      shared Pydantic models                   (Validation Eng.)
  config.py    settings from env (keys, DEMO_MODE, limits)
backend/tests/ pytest; provider fixtures in backend/tests/fixtures/<provider>/
frontend/src/  Svelte app                               (Frontend & Maps Eng.)
docs/          project documents
```

## Commands
```bash
# backend (from backend/)
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload        # http://localhost:8000/docs
ruff check . && pytest

# frontend (from frontend/)
npm install && npm run dev           # http://localhost:5173
npm test && npm run build
```

## Rules that always apply
- **The LLM proposes; deterministic code decides.** Time math, budget sums, overlap,
  opening hours and travel-time checks are plain Python functions with tests, never LLM calls.
- **Every loop has an exit**: a counter in state, a hard cap from config, and a named
  end state (PASS, INFEASIBLE, NEEDS_USER, ERROR).
- **Never invent data.** Missing price, hours or ratings stay empty/"unknown".
  Every Place keeps `source` and `retrieved_at`.
- **Repair, do not regenerate.** Changes patch the current itinerary; completed and
  locked activities are never modified.
- **DEMO_MODE=true** must work with no API keys (mocks + recorded fixtures).
- **Secrets** only in `.env` (git-ignored). Never in code, tests, logs or the frontend bundle.
- Gemini free tier is rate-limited (~10-15 requests/min per project): handle 429 with
  exponential backoff; use cached responses in tests and CI.
- Keep code simple and readable for beginners; small functions, short comments where useful.

## Working conventions
- One branch per task: `feature/<story-id>-short-name`. Open a PR; CI must pass.
- New code comes with tests. Run `ruff check` and `pytest` before finishing.
- Changing a shared model in `backend/app/models/` or `docs/contracts.md` affects everyone:
  say so clearly in the PR description.
- UI text must come from `docs/06_design_system_ux_copy.md` terminology
  (Trip, Plan, Activity, Backup, Adjust trip, Kept, Checked).
