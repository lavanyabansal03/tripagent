# Implementation Report — L4 adaptive replanning: A5 Change Interpreter + A7 Explainer

**Plan**: `.claude/plans/l4-adaptive-replanning-a5-a7.md`   **Branch**: `feature/L4-change-a5-a7` (base `fix/small-things`)   **Status**: COMPLETE

## Summary
Travellers can now change a trip while it is running: "I'm 90 minutes late", "my budget is now $300",
"Starbucks is closed today", Swap to a backup, Undo, Switch to walking, Skip something. A5 (LLM) turns words into a
checked change or asks one question; code applies it to a copy; the existing A6 repair fixes only what broke; A7
(LLM) explains each changed stop from the real diff; every change is saved as a new version. Adjust trip, Swap and
Undo work in live mode.

## Tasks completed
- Config caps `MAX_DELAY_MINUTES`, `MAX_REASON_CHARS` → `backend/app/config.py` (UPDATE)
- Tables `replan_events`, `trip_places`; `append_trace`, `save_replan`, `list_replans`, `save_places`, `get_places`; planning run lookup ignores change runs → `backend/app/storage.py` (UPDATE)
- Planning saves its places; `GET itinerary` returns the current version → `backend/app/api/trips.py` (UPDATE)
- `repair_until_valid` extracted (new plans unchanged); `day_end` and `closure` checks (only when failing) → `backend/app/agents/planner.py` (UPDATE)
- Repair: closed-today and past-day-end fixes → `backend/app/agents/repair.py` (UPDATE)
- A5 → `backend/app/agents/change_interpreter.py` (CREATE)
- Apply a change → `backend/app/agents/apply_change.py` (CREATE)
- A7 → `backend/app/agents/explainer.py` (CREATE)
- Pipeline → `backend/app/agents/replan.py` (CREATE)
- Endpoints `/changes`, `/swap`, `/restore`, `/simulate`; `/replans` → `backend/app/api/changes.py` (CREATE), `main.py`, `trips.py` (UPDATE)
- UX copy "We need one detail: {question}" → `docs/06_design_system_ux_copy.md`, `frontend/src/copy/en.json` (UPDATE)
- Frontend: `CHANGES_AVAILABLE = true`, send the day, A5 question in the Adjust dialog, previous version from the API, panel removals from the diff → `client.ts`, `store.svelte.ts`, `ItineraryPage.svelte`, `AdjustTripDialog.svelte`, `ChangeSummaryPanel.svelte` (UPDATE)

## Tests added
- `test_change_interpreter.py` (25): every type from text and quick buttons, word-rule fallback, invalid LLM answers, two-museum question, locked stop, not-supported "on the way", named stop beats a wrong LLM id.
- `test_apply_change.py` (10): day-only delay, locked untouched, budget/mode/avoid, closure flag, swap only to a stored backup, same-chain swap text, originals unchanged.
- `test_explainer.py` (7): code fallback for every change, LLM reasons only for changed ids, drops sentences naming other places, length cap, code's trigger kept, prompt forbids describing places.
- `test_replan.py` (9): closure replaced in the same slot, unaffected stops identical, delay moves/removes, empty day → INFEASIBLE, locked never changes, swap, version max+1, diff.
- `test_changes_api.py` (15): all endpoints and errors (409 lock, 404s, 422 weather, plan-before-change).
- Frontend: `AdjustTripDialog.test.ts` (3), `ChangeSummaryPanel.test.ts` (1, fails on the old panel), `client.test.ts` (+1).

## Validation results
- Backend: ruff clean; **398 passed**.
- Frontend: lint ok; type check 0 errors; **65 passed**; build ok.
- Live browser run (local, live mode, NVIDIA + Geoapify + Mapbox): plan → late (v2) → budget (v3) → closure (v4) → swap (v5) → undo (v5→v4) → walking (v6) → skip (v7) → unclear text shows A5's question; trace shows interpret and explain; no console errors.
- Postgres (temporary Neon branch, then deleted): the same flow through the API; new tables created; versions 1-7, 6 replans, 39 trace events.

## Deviations from the plan
- Endpoints live in a new `backend/app/api/changes.py` (not inside `trips.py`) to keep files small; paths and shapes are exactly as planned.
- A5 builds the trigger text from the checked change instead of using the LLM's wording ("Because running 90 minutes late" read badly); A7 writes only the per-activity reasons. Grounded and grammatical.
- A5: when the words name exactly one stop, code's match overrides the LLM's id (seen live).
- Change summary "Removed" now comes from the backend diff (replaced stops were listed twice).

## Issues encountered
- The disk was nearly full (~2 GB free); one write failed and was retried. Large caches (npm 3.1 GB, uv 1.7 GB) could be cleared by the user.
- Four unrelated uncommitted edits (NVIDIA default first, `gemini-3.5-flash`) were found in the working tree and committed separately, unchanged.
