# Deployment

TripAgent deploys as two independent services:

| Piece | What it is | Where |
|-------|------------|-------|
| `frontend/` | Svelte 5 + Vite static SPA | any static host (Render, Vercel, Netlify, GitHub Pages) |
| `backend/` | FastAPI service | any Python host (Render web service) |

The frontend is a pure static build (`npm run build` → `dist/`), so it can be
hosted anywhere. The app runs in **demo mode** (`VITE_DEMO_MODE=true`) on
recorded fixtures, so the public demo works even before the trip endpoints are
implemented (FR-55). It still probes the backend `GET /api/health` when
`VITE_API_BASE` is set and shows *Backend connected* in the header.

## Render (Blueprint — recommended)

The repo ships a [`render.yaml`](../render.yaml) Blueprint that creates both
services.

1. Sign in at <https://render.com> and connect the GitHub account that has this
   repo.
2. **New +** → **Blueprint** → pick the `tripagent` repo → **Apply**.
3. Render provisions:
   - `tripagent-web` — static site (build `npm ci && npm run build`, publish `dist`)
   - `tripagent-api` — web service (`uvicorn app.main:app --host 0.0.0.0 --port $PORT`)
4. When prompted, paste any secrets (all optional while `DEMO_MODE=true`). The
   Mapbox public token is optional — without it the app uses the schematic map
   fallback.
5. Open the `tripagent-web` URL, e.g. `https://tripagent-web.onrender.com`.

Every push to `main` redeploys automatically (`autoDeploy: true`).

### Environment variables

Backend (`tripagent-api`):

| Key | Value |
|-----|-------|
| `DEMO_MODE` | `true` until live providers are wired |
| `CORS_ORIGINS` | `*` (no cookies/auth). Tighten to the frontend URL later |
| `GOOGLE_API_KEY`, `MAPBOX_SECRET_TOKEN`, `FOURSQUARE_API_KEY` | optional; set to leave demo mode |
| `DATABASE_URL` | `sqlite:///./tripagent.db` (swap for Postgres when needed) |

Frontend (`tripagent-web`):

| Key | Value |
|-----|-------|
| `VITE_DEMO_MODE` | `true` (set `false` once trip endpoints exist) |
| `VITE_API_BASE` | `https://tripagent-api.onrender.com` |
| `VITE_MAPBOX_PUBLIC_TOKEN` | optional, URL-restricted **public** token only |

> Never put a secret Mapbox/server key in a `VITE_` variable — those are baked
> into the browser bundle (SRS §11).

## Other static hosts

The frontend config files are already in `frontend/`.

- **Vercel**: import the repo, set **Root Directory** to `frontend`. `vercel.json`
  sets the build and SPA rewrite. Add `VITE_API_BASE` / `VITE_MAPBOX_PUBLIC_TOKEN`
  in Project → Settings → Environment Variables.
- **Netlify**: **Add new site** → import the repo. `netlify.toml` sets the build
  command and publish directory. Add the same env vars under Site configuration.
- **Manual / any host**: `cd frontend && npm ci && npm run build`, then upload
  `dist/`.

## Local production check

```bash
cd frontend
npm ci && npm run build
npm run preview          # serves dist/ on http://localhost:4173
```

## Docker

`frontend/Dockerfile` builds the SPA and serves it with nginx (`frontend/nginx.conf`),
with a `/healthz` endpoint, security headers and an optional `/api/` proxy:

```bash
cd frontend
docker build -t tripagent-web .
docker run --rm -p 8080:80 tripagent-web
```

## Deploy checklist (sprint R-06)

- [ ] Blueprint applied; both services healthy (`/api/health` returns `ok`).
- [ ] `tripagent-web` loads and shows *Demo mode*.
- [ ] `VITE_API_BASE` points at the live API and the header shows *Backend connected*.
- [ ] Mapbox token set (or schematic fallback accepted).
- [ ] Three clean rehearsals on the public URL in demo mode.
- [ ] No secrets committed; `git grep -i "sk-\|secret\|token"` is clean.
