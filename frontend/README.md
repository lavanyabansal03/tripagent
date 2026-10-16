# TripAgent Frontend

Svelte 5 + Vite + TypeScript single-page app for TripAgent, owned by the
**Frontend & Maps Eng.** role. It implements the screens, components and copy in
the *Design System & UX Copy Guide (doc 06)* and the UI-facing requirements in
the SRS v2.

The app runs standalone against an in-memory demo engine (`DEMO_MODE`), so the
whole flow — describe a trip, plan, view the map, adjust, read the change
summary, undo — works with no backend and no API keys (FR-55).

## Quick start

```bash
cd frontend
npm install
cp .env.example .env.local     # optional; DEMO_MODE is on by default
npm run dev                    # http://localhost:5173
```

## Backend integration

This frontend is the `frontend/` package of the TripAgent repo. It talks to the
FastAPI backend under `/api` and, in development, Vite proxies `/api` to the
backend (default `http://localhost:8000`, override with `VITE_API_PROXY`).

On load the header probes the existing contract **`GET /api/health`** and shows
*Backend connected* or *Backend offline*, matching the original skeleton's
behaviour. Because the trip endpoints are still being built, the app runs on
recorded fixtures by default (`VITE_DEMO_MODE=true`, FR-55) so the whole flow is
usable with or without the backend. Set `VITE_DEMO_MODE=false` to route calls to
the live API as those endpoints land.

Run both together:

```bash
# terminal 1 — backend
cd backend && source .venv/bin/activate && uvicorn app.main:app --reload

# terminal 2 — frontend
cd frontend && npm run dev
```

| Script | What it does |
|--------|--------------|
| `npm run dev` | Vite dev server with API proxy to `VITE_API_PROXY` |
| `npm run build` | Production build to `dist/` |
| `npm run preview` | Serve the production build |
| `npm run check` | `svelte-check` type/a11y diagnostics |
| `npm run test` | Vitest unit + component tests |
| `npm run test:coverage` | Vitest with coverage |
| `npm run e2e` | Playwright end-to-end flows |

## Configuration

| Variable | Purpose |
|----------|---------|
| `VITE_DEMO_MODE` | `true` (default) uses recorded fixtures; `false` calls the FastAPI backend at `/api` |
| `VITE_MAPBOX_PUBLIC_TOKEN` | URL-restricted **public** map token. Blank falls back to the built-in schematic map. Only this token reaches the browser (SRS §11) |
| `VITE_API_PROXY` | Dev-server proxy target for the FastAPI service |

Never commit a Mapbox secret token or provider keys. The frontend only ever
receives the public map token.

## Architecture

```
src/
├── main.ts                 # mount App
├── App.svelte              # shell, header, theme, route switch
├── pages/                  # Setup, Understood (clarify + review), Itinerary
├── components/             # design-system components (see inventory below)
├── state/store.svelte.ts   # runes singleton: trip, itinerary, run, trace, versions
├── api/
│   ├── client.ts           # typed client; swaps mock <-> live by DEMO_MODE
│   └── mock/               # fixtures + engine simulating the agent graph
├── copy/                   # en.json (all strings) + i18n helpers
├── styles/                 # tokens.css, tokens.ts (map mirror), global.css
├── types/                  # domain types mirroring Architecture §9.1
└── utils/                  # visuals (colour+icon+word), map projection
```

### Design system

All colours, spacing, type, shape, elevation and motion live in
`src/styles/tokens.css` and are mirrored for map layers in
`src/styles/tokens.ts`. Components never hard-code these values. Every status and
change type pairs colour with an **icon and a word** (NFR-14), and the eight
experience categories use a colour-blind-safe palette with distinct icons.

### Demo engine

`src/api/mock/engine.ts` stands in for FastAPI + LangGraph. It follows the real
contracts (`POST /trips`, `POST /trips/{id}/plan`, `GET /runs/{id}` polling per
ADR-006, `POST /changes`, swap, restore, trace). Planning runs advance from
elapsed time (no timers) so tests can drive them deterministically. It
implements intake extraction with provenance, L2-style discovery, deterministic
clustering + a bounded L3 repair pass that removes hard travel/opening-hours
violations, purpose-preserving backups, change interpretation, minimal-change
diffs, versioning and `ExecutionEvent`s.

## Component inventory (Design Guide §4.1)

`TripForm`, `TellUsMoreField`, `PreferenceChips`, `TouristLocalSlider`,
`ClarifyCard`, `RunProgress`, `DayTabs`, `ActivityCard`, `LegRow`,
`BackupDrawer`, `FreshnessLabel`, `ValidationBadge`, `ValidationSummary`,
`AdjustTripDialog`, `ChangeSummaryPanel`, `MapView`, `AgentTrace`,
`InfeasibleNotice`, plus layout (`App`).

## Accessibility

- Keyboard: Tab to controls, `Enter` expands backups, `L` locks an activity.
- Change states are announced in a polite live region after replans.
- Focus-visible outlines, skip link, 4.5:1+ text contrast in both themes.
- `prefers-reduced-motion` disables route animation and map fly-to.
- `svelte-check` runs a11y diagnostics; `npm run check` must stay clean.

## Deployment (FR-54, D-01)

`Dockerfile` builds the SPA and serves it with nginx (`nginx.conf`), with a
`/healthz` endpoint, security headers, API proxy and SPA fallback. CI
(`.github/workflows/frontend.yml`) runs type-check, unit tests, build, secret
scan on every PR, and Playwright E2E on `main`.
