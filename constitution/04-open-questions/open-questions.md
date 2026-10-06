# Open Questions and Inconsistencies

Found while condensing `docs/`, `CLAUDE.md` and `README.md` into the constitution (Oct 5, 2026).
Rule agreed with the team: **when documents conflict, the `docs/` folder holds the right details**;
other files are brought in line with it.

## A. Decisions

| # | Question | Status | Answer |
|---|---|---|---|
| A1 | Demo city | Answered | As in the docs: Seattle by default, optional second city (PRD 3.7) |
| A2 | Hosting for frontend and backend | **Open** | |
| A3 | Foursquare fill rates and licence (ADR-003 spike) | **Open**, due Wed Oct 7 | |
| A4 | Events provider | Open (P1, not blocking) | |
| A5 | What counts as a "major change" for approval (L7)? | Open (P1, not blocking) | |
| A6 | Who holds each role | Answered | Kaleb (Preferences), Harshita (Validation), Sathwika (Agent Graph), Nitin (Tools), Yahya (Frontend & Maps). See [team.md](../05-team/team.md) |
| A7 | Data contracts (`docs/contracts.md`) | **Open** | Not written yet; likely JSON shapes, implemented as Pydantic models in `backend/app/models/` |
| A8 | Who is the Product Owner / Tech Lead? | **Open** | |
| A9 | Frontend framework | Answered | Svelte, replacing React (ADR-008). Yahya already has Svelte code |
| A10 | Plain Svelte + Vite, or SvelteKit? Which branch holds Yahya's Svelte code? | **Open** | |

## B. Conflicts and how they were resolved

| # | Topic | Resolution | Files changed |
|---|---|---|---|
| B1 | Branch naming | `feature/<story-id>-short-name` | README.md |
| B2 | Frontend linter | ESLint + `eslint-plugin-svelte` (+ Prettier). **Follow-up:** do it as part of merging Yahya's Svelte frontend (replace oxlint, add `eslint.config.js`, keep `npm test` and `npm run build` scripts so CI passes) | constitution/03-tech-stack |
| B3 | Performance targets | Gemini free-tier numbers (SRS NFR-03): first plan < 60 s, replan < 30 s | 01_product_vision_prd.md, 04_test_strategy.md |
| B4 | Clarification loop priority | **P0, moved into Sprint 1** (loop engineering is the focus). Sprint 1 now 29 points | 05_sprint_plan_backlog.md, backlog.csv, roadmap |
| B5 | Trace panel priority | **Open.** Recording ExecutionEvents is P0 (FR-20); the panel UI (T-02) is still stretch | — |
| B6 | Diversity priority | Not a real conflict: diversity warning is P0 (V-02), re-rank is P1 (US-19) | — |
| B7 | Undo | Stays stretch (P1); "undo" step removed from E2E flow 2 unless US-29 ships | 04_test_strategy.md |
| B8 | Story ID `US-53` | Renamed to `FR-53` | 05_sprint_plan_backlog.md, backlog.csv, roadmap |
| B9 | PR reviews | README now states the 2-review rule for shared models, graph edges and prompts | README.md |
| B10 | Config contents | Not a conflict yet: add model names and loop limits to `config.py` when the first agent/loop lands | — |
| B11 | Planned dependencies (Alembic, Hypothesis, RTL, Playwright, mypy) | Add each when its first story needs it | — |
| B12 | Production database | Managed Postgres (ADR-005); provider depends on A2 | — |
