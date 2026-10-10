# Tech Stack

_Sources: [CLAUDE.md](../../CLAUDE.md), [02_srs.md](../../docs/02_srs.md) section 13, [03_architecture_agent_design.md](../../docs/03_architecture_agent_design.md) sections 10-11, [00_getting_started.md](../../docs/00_getting_started.md), plus `backend/requirements.txt`, `frontend/package.json` and `.github/workflows/ci.yml` on `main` as of Oct 5, 2026._

The **Status** column compares the planned stack with what is installed on `main` today:
**Installed** means it is in the dependency files, **Planned** means the docs call for it but
it is not installed yet.

## Backend

| Layer | Technology | Purpose | Status |
|---|---|---|---|
| Language | Python 3.12 | Backend, agents, validators, tools | Installed |
| API | FastAPI + Uvicorn | REST API; all routes under `/api` | Installed |
| Data shapes | Pydantic v2 + pydantic-settings | Typed contracts, settings from env | Installed |
| Orchestration | LangGraph | State graph, conditional edges, checkpoints, interrupts (ADR-001) | Installed |
| LLM | Google Gemini API, free tier, **Flash models**, via `google-genai` and `langchain-google-genai` | Extraction, ordering proposals, repair choice, explanations (ADR-007) | Installed |
| HTTP client | httpx | Calls to Mapbox and Foursquare | Installed |
| Persistence | SQLAlchemy | ORM for trips, versions, events | Installed |
| Migrations | Alembic | Schema migrations | Planned |
| Database | SQLite (local) / managed Postgres (production) | Trips, itinerary versions, events (ADR-005) | SQLite default in config; Postgres planned |
| Config | `.env` at repo root -> `backend/app/config.py` | Keys, `DEMO_MODE`, database URL | Installed |

**Never use OpenAI.** Model names and loop limits belong in `backend/app/config.py`.

## External providers

| Provider | Used for | Key | Status |
|---|---|---|---|
| Google Gemini (AI Studio) | All LLM steps | `GOOGLE_API_KEY`, one per engineer | Key slot in config |
| Mapbox | Search, Directions, Matrix (travel times), GL JS map | `MAPBOX_SECRET_TOKEN` (server); URL-restricted public token (browser) | Key slot in config |
| Foursquare Places | Hours, price level, ratings, review counts, popularity (ADR-003) | `FOURSQUARE_API_KEY` | Key slot in config |
| Curated seed data | Permanent test and demo fallback (ADR-003 option D) | none | Planned |
| Events provider (P1) | Current events | TBD | Undecided |

**Free-tier limit:** Gemini allows about 10-15 requests per minute per project. Handle 429 with
exponential backoff, and use cached responses in tests and CI.

## Frontend

| Layer | Technology | Purpose | Status |
|---|---|---|---|
| Framework | Svelte + TypeScript (ADR-008, replaced React) | UI | Decided; `main` still has the React hello-world, Yahya's Svelte code to be merged |
| Build | Vite | Dev server and build | Installed |
| Map | Mapbox GL JS | Pins, routes, diff layer | Planned |
| Styling | CSS custom properties in `frontend/src/styles/tokens.css` | Design tokens from the design system | Planned |
| Copy | `frontend/src/copy/en.json` | All UI strings, no inline text | Planned |
| Lint | ESLint + `eslint-plugin-svelte` (+ Prettier) | Frontend lint and formatting | Decided; repo still uses oxlint, switch pending |

## Testing and quality

| Tool | Purpose | Status |
|---|---|---|
| pytest | Backend unit, contract, graph and scenario tests | Installed |
| ruff | Python lint | Installed |
| Vitest | Frontend unit tests | Installed |
| Svelte Testing Library | Frontend component tests | Planned |
| Hypothesis | Property-based tests for validators | Planned |
| Playwright (+ axe) | E2E and accessibility tests | Planned |
| mypy / svelte-check | Type checks | Both planned (`tsc` runs in the current React build) |

## Delivery and operations

| Area | Technology | Status |
|---|---|---|
| Source control | Git + GitHub; one branch per task; PR needs 1 review (2 for shared models, graph edges, prompts) | Active |
| CI | GitHub Actions: backend `ruff check` + `pytest`; frontend `npm ci`, `npm test`, `npm run build` | Installed |
| CD | Deploy on merge to `main`, smoke test `/api/health` | Planned (D-01) |
| Hosting | Static/CDN for frontend; one FastAPI container for backend | Host not chosen |
| Observability | Structured JSON logs; ExecutionEvents per node; optional LangSmith | Planned |
| Secrets | `.env` (git-ignored) locally; host environment settings in production; secret scanning on | `.env` ignored; scanning not verified |

## Architecture in one picture

```
Browser (Svelte + Vite, Mapbox GL JS with a URL-restricted public token)
        |  HTTPS
Static hosting / CDN (frontend build)
        |  HTTPS /api/*
FastAPI container (API + LangGraph + tools)  --->  Gemini API
        |                                    --->  Mapbox / Foursquare / events
Postgres in production (SQLite locally)          Structured JSON logs
```

## Code layout and owners

```
backend/app/
  api/         FastAPI routes, all under /api           Tools Eng.
  agents/      LLM-backed steps (intake, planner, ...)   Preferences + Agent Graph Eng.
  graph/       LangGraph workflow, state, routing        Agent Graph Eng.
  tools/       Foursquare/Mapbox adapters + mocks        Tools Eng.
  validation/  pure-function validators                  Validation Eng.
  models/      shared Pydantic models                    Validation Eng.
  config.py    settings from env
backend/tests/ pytest; fixtures in backend/tests/fixtures/<provider>/
frontend/src/  Svelte app                                Frontend & Maps Eng.
docs/          project documents
constitution/  this summary
```

## Performance targets

Set for the Gemini free tier (SRS NFR-03): first itinerary for a 3-day demo trip < 60 s
median with live APIs; replan < 30 s; DEMO_MODE run < 10 s.

## Deliberately excluded

Microservices, Kubernetes, message queues, vector databases, OpenAI, model fine-tuning.
