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
   - `tripagent-web-lavanyabansal03` — static site (build `npm ci && npm run build`, publish `dist`)
   - `tripagent-api-lavanyabansal03` — web service (`uvicorn app.main:app --host 0.0.0.0 --port $PORT`)

   Names include the repo owner because `onrender.com` subdomains are global; if
   Render says a name is taken, change it in both services (the frontend's
   `VITE_API_BASE` in `render.yaml` holds the API's public address).
4. When prompted, paste any secrets (all optional while `DEMO_MODE=true`). The
   Mapbox public token is optional — without it the app uses the schematic map
   fallback.
5. Open the frontend URL Render shows, e.g. `https://tripagent-web-lavanyabansal03.onrender.com`.

Every push to `main` redeploys automatically (`autoDeploy: true`).

### Environment variables

Backend (`tripagent-api-lavanyabansal03`):

| Key | Value |
|-----|-------|
| `DEMO_MODE` | `true` until live providers are wired |
| `CORS_ORIGINS` | `*` (no cookies/auth). Tighten to the frontend URL later |
| `GOOGLE_API_KEY`, `NVIDIA_API_KEY`, `MAPBOX_SECRET_TOKEN`, `GEOAPIFY_API_KEY` | optional; set to leave demo mode |
| `LLM_PRIMARY` | optional: `nvidia` (default) or `gemini`, which LLM goes first |
| `DATABASE_URL` | **secret**: the Postgres connection string from Neon. Empty -> a SQLite file, which Render wipes on every restart |

Frontend (`tripagent-web-lavanyabansal03`):

| Key | Value |
|-----|-------|
| `VITE_DEMO_MODE` | `true` (set `false` once trip endpoints exist) |
| `VITE_API_BASE` | the API's public address, `https://tripagent-api-lavanyabansal03.onrender.com` (set in `render.yaml`; Render's `fromService` host is a private name browsers cannot reach) |
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
- [ ] The frontend loads; it shows *Demo mode* while `VITE_DEMO_MODE=true`.
- [ ] With `VITE_DEMO_MODE=false`, no "Demo mode" text is shown and the header shows *Backend connected*.
- [ ] `VITE_API_BASE` points at the live API and the header shows *Backend connected*.
- [ ] Mapbox token set (or schematic fallback accepted).
- [ ] Three clean rehearsals on the public URL in demo mode.
- [ ] No secrets committed; `git grep -i "sk-\|secret\|token"` is clean.
