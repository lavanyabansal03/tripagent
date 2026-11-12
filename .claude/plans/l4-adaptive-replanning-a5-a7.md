# Feature: L4 adaptive replanning — A5 Change Interpreter + A7 Explainer

The following plan should be complete, but validate documentation, codebase patterns and task sanity before implementing.
Pay special attention to the names of existing utils, types and models. Import from the right files.

## Feature Description

When something changes during a trip ("I'm 90 minutes late", "my budget is now $300", "the museum is closed today",
the traveller picks a backup, or wants to undo), TripAgent updates **only the affected part** of the current plan,
saves it as a **new version**, and explains **what changed and why**. Two LLM agents do the language work, code
decides everything else:

- **A5 Change Interpreter**: free text -> a typed `ChangeEvent`; asks one question when unsure (NEEDS_USER).
- **A7 Explainer**: writes the change summary (trigger line + one reason per changed activity) **only from the
  structured diff**; plain-code fallback text when no LLM answers.

Code applies the change, runs the existing L3 repair (A6) on the current itinerary, validates, and stores version N+1.

## User Story

As a traveller using TripAgent during my trip
I want to tell the app what changed in my own words, or tap Swap / Undo
So that only the affected stops change, the rest of my plan stays the same, and I can see why.

## Problem Statement

Live mode has no change handling: the Adjust trip, Swap, Undo and "Mix it up" actions call 4 endpoints that do not
exist (`/changes`, `/activities/{aid}/swap`, `/versions/{v}/restore`, `/simulate`), so they are hidden
(`CHANGES_AVAILABLE = DEMO_MODE`, `frontend/src/api/client.ts:30`). A5 and A7 (docs/03 §3) are not built. This is the
L4 loop, the centre of the project (docs/03 §5.4, SRS §7).

## Solution Statement

Add a synchronous replan pipeline in the backend (same style as `plan_trip`): interpret (A5) -> validate -> apply
(code) -> L3 repair on the current itinerary (existing A6 code, refactored to work on an existing itinerary) ->
diff -> explain (A7) -> persist version N+1, the ReplanEvent, the run and trace events. Add the 4 endpoints with the
shapes the frontend already uses, a "current version" pointer for Undo, two new storage tables, and turn the
actions back on in live mode.

## Out of Scope / Non-Goals

- Not included: weather / rain (needs a weather provider; P2).
- Not included: "Coffee on the way" quick chip (adding new stops along a route). It gets a polite
  needs-clarification answer: "Adding new stops on the way isn't supported yet."
- Not included: approval mode (Apply / Keep my plan, P1), queued events (a second change while one runs gets 409).
- Not included: real Mapbox route legs (separate work).
- Not changing: initial planning (`POST /plan`) behaviour; contracts' `ChangeEvent` / `ReplanEvent` shapes.
- Not doing: merging any PR. Base branch `fix/small-things` (PR #46 on top of PR #45).

## Feature Metadata

**Feature Type**: New Capability
**Estimated Complexity**: High
**Primary Systems Affected**: backend agents (new A5, A7, apply/replan), planner + repair (small additions),
storage (2 tables), trips API (4 endpoints + current version), frontend client/store/ItineraryPage/AdjustTripDialog
**Dependencies**: none new (uses `llm.py`, Geoapify/NVIDIA/Gemini already configured)

## Related Work

**Implements**: docs/03 §5.4 (L4), SRS §7 Replanning Procedure, FR-13..17, FR-19, FR-42..44, US-09
**Back-references**: A6 Repair (`backend/app/agents/repair.py`, `repair_choice.py`), shared LLM helper
(`backend/app/agents/llm.py`), storage (`backend/app/storage.py`), PRs #45/#46 (base).
**Forward-references**: (none yet)

---

## DECISIONS (from the clarifying questions, all answered "yes")

1. "Switch to walking" (transport) and "Skip something" (avoid) **are supported** (A6 already repairs travel / avoid).
2. "Running late" shifts every not-done, not-locked activity on **the day open on screen** (frontend sends `day`) by
   the delay; anything pushed past `daily_end` (default 20:00) is **removed with a reason**.
3. Undo = **move the current-version pointer** back to the previous version; versions are never deleted; a new
   change after Undo creates the next version number (max + 1).
4. When A5 is unsure, the API returns A5's **question** and the Adjust dialog **shows it** (one new UX string).
5. Done = all tests (new ones fail on old code) + a real browser run with real keys for all 7 actions
   (late, budget, closure, swap, undo, walking, skip) + screenshots. **No merge.**

---

## CONTEXT REFERENCES

### Relevant Codebase Files — READ BEFORE IMPLEMENTING

- `CLAUDE.md` — rules: LLM proposes / code decides; every loop capped from config; never invent data; repair not regenerate; done/locked never modified; UI text from docs/06.
- `docs/03_architecture_agent_design.md` §5.4 L4 (event loop), §3 agent table (A5, A7) — the target flow.
- `docs/02_srs.md` §7 "Replanning Procedure" (12 steps), FR-13..17, FR-19, FR-42..44.
- `docs/06_design_system_ux_copy.md` "Adjust trip" + "Change summary" sections (~line 221) — exact UI text.
- `frontend/src/types/index.ts` — `ChangeEvent`, `ReplanDiff`, `ReplanEvent`, `ItineraryVersion` (the contract; section 11 of contracts.md points here).
- `frontend/src/api/mock/engine.ts` (lines ~1150-1270) — demo behaviour to mirror: `submitChange`, `interpretChange` regexes, `swapBackup`, `simulate` (`closure`, `delay`), `restoreVersion` (pointer), `getItinerary` (defaults to `current_version`).
- `frontend/src/state/store.svelte.ts` — `submitChange` / `submitTypedChange` (empty `run_id` = needs clarification, line ~214), `swap`, `simulate`, `undo` (line ~254, previous = versions[index-1]), `pollRun`, `reload` (line 190).
- `frontend/src/components/AdjustTripDialog.svelte` lines 18-26 — quick-chip typed payloads: `time {minutes}`, `budget {budget}`, `transport {mode}`, `preference {avoid}`, `preference {interests, along_route}`.
- `frontend/src/components/ChangeSummaryPanel.svelte` — reads `replan.trigger_text`, `replan.reasons[activity_id]`, `previous` itinerary.
- `frontend/src/pages/ItineraryPage.svelte` lines 31-37 — BUG: `previousItinerary` comes from `mockEngine` even in live mode.
- `backend/app/agents/llm.py:61` `ask_json(prompt, Shape)` — the only way agents call an LLM.
- `backend/app/agents/repair_choice.py` (whole file) — the A6 LLM pattern to MIRROR for A5 and A7 (prompt builder + Pydantic shape + code validation + None fallback).
- `backend/app/agents/planner.py:166` `check_itinerary`, `:402` `build_plan_with_repairs` (repair loop to extract), `:373` `_attach_day_warnings`, `:386` `_limited`.
- `backend/app/agents/repair.py` — `PROTECTED_STATUSES` (:30), `repair_itinerary` (:49), `fix_closed_places` (:86), `_replace_or_remove` (:153), `_hours_check` (:250).
- `backend/app/agents/backup.py` `attach_backups(itinerary, trip, search=None, only_ids=None)`.
- `backend/app/storage.py` — table + function pattern (`trace_events` :67, `save_itinerary` :149, `get_itinerary` :162, `list_versions` :173, `save_run` :186). New tables are created by `metadata.create_all` (safe on the existing Neon DB; never add columns to existing tables).
- `backend/app/api/trips.py` — `RunStatus` (:155), `_load`/`_save` (:171/:186), `plan_trip` (:387, the run/trace/storage pattern to mirror), `get_itinerary` (:462), `get_versions` (:474), `get_replans` (:480).
- `backend/app/graph/trip_planner.py` — `_log` (event shape incl. `duration_ms`), `_ms_since`, how `plan_node` passes `choose` and `add_backups`.
- `backend/tests/conftest.py` — tests never call real LLMs / Geoapify; in-memory DB per test.
- `backend/tests/test_llm_repair_choice.py` — fake-LLM test pattern (monkeypatch `ask_json`).

### New Files to Create

- `backend/app/agents/change_interpreter.py` — A5: prompt, `ChangeShape`, code validation, rule-based fallback, typed-input path.
- `backend/app/agents/apply_change.py` — code: apply a validated change to requirements + itinerary copy.
- `backend/app/agents/explainer.py` — A7: prompt, `ExplanationShape`, validation, deterministic fallback.
- `backend/app/agents/replan.py` — the L4 pipeline for one change (apply -> repair -> diff -> explain).
- `backend/tests/test_change_interpreter.py`, `test_apply_change.py`, `test_explainer.py`, `test_replan.py`, `test_changes_api.py`.
- `frontend/src/test/AdjustTripDialog.test.ts` (question shown), store/client test additions.

### Patterns to Follow

**LLM agent (mirror `repair_choice.py`)**: `build_prompt(...)` with facts only + "do not invent"; Pydantic shape with
`Field(description=...)`; `answer = ask_json(prompt, Shape)`; `None` -> fallback; code validates every field (ids must
exist, numbers in range, enums) and drops/ignores bad parts.

**Caps from config** (`backend/app/config.py`): add `MAX_DELAY_MINUTES = 600`, `MAX_REASON_CHARS = 200`; reuse
`MAX_REPAIR_ITERATIONS`, `MAX_REPAIR_LLM_CALLS`.

**Storage**: SQLAlchemy Core `Table` + JSON column + small functions; `with engine().begin()` for writes.

**API**: Pydantic request models with `ConfigDict(extra="forbid")`; `HTTPException(404|409|422)`; synchronous run
that writes `RunStatus` + trace via storage (like `plan_trip`).

**Trace events**: same dict shape as `graph/trip_planner._log` (`node`, `type` in node/tool/llm/validation/loop,
`iteration`, `status`, `duration_ms`, `metadata.message`).

---

## IMPLEMENTATION PLAN

### Phase 1: Foundation (storage, config, current-version pointer)
### Phase 2: Core (A5, apply, repair additions, replan pipeline, A7)
**Depends on:** Phase 1
### Phase 3: Integration (endpoints, frontend)
**Depends on:** Phase 2
### Phase 4: Testing & live validation
**Depends on:** Phase 3

---

## STEP-BY-STEP TASKS

### 1. UPDATE `backend/app/config.py`
- **ADD**: `MAX_DELAY_MINUTES = 600` (A5 rejects bigger delays), `MAX_REASON_CHARS = 200` (A7 reason length).
- **VALIDATE**: `cd backend && ruff check .`
- **SATISFIES**: AC 6 (caps from config)

### 2. UPDATE `backend/app/storage.py`
- **ADD** tables `replan_events (id PK, trip_id idx, event JSON)` and `trip_places (trip_id PK, places JSON)`.
- **ADD** `save_replan(event)`, `list_replans(trip_id)` (oldest first), `save_places(trip_id, places)` (insert or replace), `get_places(trip_id) -> list`.
- **ADD** `append_trace(trip_id, run_id, events)` (insert only; `save_trace` replaces a run's events).
- **GOTCHA**: never alter existing tables (Neon already has them); new tables only.
- **VALIDATE**: `pytest tests/test_storage.py -q`
- **SATISFIES**: AC 3, AC 4

### 3. UPDATE `backend/app/api/trips.py` — current version + places
- **UPDATE** `plan_trip`: also `storage.save_places(trip_id, result.get("places", []))`.
- **UPDATE** `get_itinerary`: with no `version`, return `trip.current_version` (not the newest).
- **VALIDATE**: `pytest tests/test_trips_api.py tests/test_storage.py -q`
- **SATISFIES**: AC 4 (undo), AC 3

### 4. UPDATE `backend/app/agents/planner.py`
- **REFACTOR**: extract the repair loop of `build_plan_with_repairs` into
  `repair_until_valid(trip, itinerary, places, *, version, choose=None, add_backups=None, first_checks=None)
  -> (checks, iterations, terminal, explanation)`; `build_plan_with_repairs` calls it (behaviour unchanged).
- **ADD** to `check_itinerary`: a hard `day_end` result for activities ending after `daily_end`, and a hard `closure`
  result for activities with `unavailable: true` (ids in `activity_ids`).
- **GOTCHA**: existing planner/repair tests must pass unchanged.
- **VALIDATE**: `pytest tests/test_planner.py tests/test_repair.py tests/test_llm_repair_choice.py -q`
- **SATISFIES**: AC 2 (repair, not regenerate)

### 5. UPDATE `backend/app/agents/repair.py`
- **ADD** `fix_unavailable_places` (runs first): activities with `unavailable: true` -> `_replace_or_remove(..., "closure", "It is closed today.")`; the closed place id is added to `rejected_place_ids`.
- **ADD** `fix_day_end`: not-protected activities ending after `daily_end` -> remove, reason "It no longer fits in the day."
- **GOTCHA**: never touch `PROTECTED_STATUSES`; replacement keeps the slot; clear `unavailable` on a replaced activity.
- **VALIDATE**: `pytest tests/test_repair.py -q`
- **SATISFIES**: AC 2, AC 5

### 6. CREATE `backend/app/agents/change_interpreter.py` (A5)
- **IMPLEMENT** `ChangeShape` (Pydantic): `type: Literal["time","budget","closure","transport","preference","unknown"]`,
  `minutes: int | None`, `budget: float | None`, `activity_id: str | None`, `mode: Literal[walking,transit,driving,cycling] | None`,
  `avoid: list[str]`, `question: str | None`, `trigger: str` (short, traveller's words).
- **IMPLEMENT** `build_prompt(text, itinerary, requirements, day)` — lists the day's activities (id, name, time, purpose) and current budget/mode; tells the LLM to use only these ids and to ask a question when unsure.
- **IMPLEMENT** `validate(shape, itinerary, requirements, day) -> Interpretation` (`status: ok | needs_clarification`, `change: dict`, `question`): minutes 1..MAX_DELAY_MINUTES; budget >= 0; closure id must exist and not be protected; mode in enum; avoid non-empty; `preference` with `interests` / along-route -> needs_clarification "Adding new stops on the way isn't supported yet."
- **IMPLEMENT** `rule_based(text, itinerary)` fallback (mirror `engine.ts interpretChange`): late/delay + minutes/hours; budget + number; walk/transit/drive; skip/avoid + word; closed + an activity name word that matches exactly one activity on the day (else ask "Which place is closed: A or B?").
- **IMPLEMENT** `interpret(text=None, typed=None, *, itinerary, requirements, day)`: typed -> validate directly (no LLM); text -> `ask_json` -> validate; LLM None/invalid -> `rule_based` -> validate; still nothing -> needs_clarification with the docs/06 generic text.
- **PATTERN**: `repair_choice.py` (prompt + shape + None fallback).
- **VALIDATE**: `pytest tests/test_change_interpreter.py -q`
- **SATISFIES**: AC 1

### 7. CREATE `backend/app/agents/apply_change.py`
- **IMPLEMENT** `apply_change(change, requirements, itinerary, *, day) -> (requirements, itinerary, moved_ids)` on deep copies:
  `time` shifts start/end of not-protected activities on `day` by minutes (records `change_type="moved"`, reason "You're running N minutes late.");
  `budget` sets `requirements.budget`; `closure` sets `unavailable=True` on the activity;
  `transport` sets `requirements.mode`; `preference` adds to `requirements.avoid` (case-insensitive, no duplicates);
  `swap` sets the activity's place to the chosen backup's place (must be one of its stored backups).
- **GOTCHA**: never modify done/locked/cancelled; keep ISO offsets when shifting.
- **VALIDATE**: `pytest tests/test_apply_change.py -q`
- **SATISFIES**: AC 2, AC 5

### 8. CREATE `backend/app/agents/explainer.py` (A7)
- **IMPLEMENT** `ExplanationShape`: `trigger: str`, `reasons: list[{activity_id, reason}]`.
- **IMPLEMENT** `fallback(change, diff, before, after, repairs) -> (trigger_text, reasons)` from the change type and the repair records (e.g. "It is closed today.", "You're running 90 minutes late.", "It no longer fits in the day.").
- **IMPLEMENT** `explain(...)`: prompt with ONLY the change and the per-activity facts (old/new place names, old/new times, rule); LLM answer kept only for activity ids in the diff (changed/moved/removed); each reason <= MAX_REASON_CHARS; a reason naming a place not in before/after is dropped; missing reasons filled from `fallback`.
- **VALIDATE**: `pytest tests/test_explainer.py -q`
- **SATISFIES**: AC 1 (A7), AC 6

### 9. CREATE `backend/app/agents/replan.py`
- **IMPLEMENT** `replan(change, *, trip, requirements, itinerary, places, versions, day, choose, add_backups, explain_fn) -> ReplanResult`:
  1. new version = max(versions) + 1; deep copy; set each activity's `version`; clear old `change_type`/`reason`;
  2. `apply_change`; 3. `repair_until_valid` (choose = LLM chooser, capped); 4. refresh backups for changed ids;
  5. diff by activity id vs old: `changed` (place changed), `moved` (time changed), `removed`, `added`, `preserved`;
  6. A7 `explain`; 7. return itinerary, requirements, ReplanEvent dict, terminal, explanation, timings.
- **GOTCHA**: the old version object is never modified (deep copy); terminal PASS / INFEASIBLE / ERROR.
- **VALIDATE**: `pytest tests/test_replan.py -q`
- **SATISFIES**: AC 2, AC 3

### 10. UPDATE `backend/app/api/trips.py` — 4 endpoints + replans
- **ADD** `ChangeRequest {text?: str, typed?: dict, day?: int}`; `POST /{id}/changes` -> `{run_id, change}`; needs clarification -> `run_id: ""`, `change.status = "needs-clarification"`, `change.payload.question`.
- **ADD** `POST /{id}/activities/{aid}/swap {backup_id}` -> `{run_id}` (404 unknown activity / backup).
- **ADD** `POST /{id}/versions/{v}/restore` -> `{version}` (404 unknown version); sets `trip.current_version`.
- **ADD** `POST /{id}/simulate {type: closure|delay, activity_id?}` -> `{run_id}`; closure without id picks the first not-protected activity of day 1.
- **UPDATE** `GET /{id}/replans` -> `storage.list_replans`.
- **ADD** a per-trip `threading.Lock`; a second change while one runs -> 409.
- **IMPLEMENT** run + trace: `RunStatus(phase="adapt")`; trace events `interpret` (llm), `apply` (node), `repair` (loop, per iteration), `repair_choice` (llm, if any), `explain` (llm), `save` (node), appended with `append_trace`.
- **VALIDATE**: `pytest tests/test_changes_api.py tests/test_trips_api.py -q`
- **SATISFIES**: AC 1-5

### 11. UPDATE `docs/06_design_system_ux_copy.md` + `frontend/src/copy/en.json`
- **ADD** UX copy: "A5 question shown in the Adjust dialog" -> `We need one detail: {question}` (`adjust.question`).
- **VALIDATE**: `cd frontend && npm test -- --run src/copy`
- **SATISFIES**: AC 7 (UI text from docs/06)

### 12. UPDATE frontend
- `src/api/client.ts`: `CHANGES_AVAILABLE = true`; `submitChange` input adds `day?: number` (sent to the API).
- `src/state/store.svelte.ts`: pass `state.activeDay` as `day`; on needs clarification store `clarifyQuestion` (from `change.payload.question`); `reload` also loads `previousItinerary` = `api.getItinerary(id, previousVersion)` when there is one.
- `src/pages/ItineraryPage.svelte`: use `store.previousItinerary` (remove `mockEngine` use).
- `src/components/AdjustTripDialog.svelte`: show `t('adjust.question', {question})` when the store has one.
- **VALIDATE**: `cd frontend && npm run lint && npm run check && npm test && npm run build`
- **SATISFIES**: AC 1, AC 4, AC 7

### 13. Tests + live validation
- Run every validation command; run the browser script for the 7 actions with real keys (local DB); screenshots.
- **SATISFIES**: AC 8

---

## TESTING STRATEGY

### Unit Tests (fake LLMs via monkeypatching `ask_json`)
- A5: each type from text; typed path skips the LLM; LLM None -> rule-based; invalid id/minutes/mode -> needs_clarification; two museums -> question; along-route -> not supported.
- apply_change: shifts only the chosen day and skips done/locked; budget/mode/avoid; closure flag; swap only to a stored backup; old itinerary unchanged.
- repair additions: unavailable replaced from backups first; day_end removal; protected untouched.
- A7: LLM reasons kept only for diff ids; long reasons cut; reasons naming unknown places dropped; fallback covers every changed id.
- replan: version N+1; unaffected activities identical (id, place, start, end); diff correct; INFEASIBLE path explained.

### Integration Tests (API, in-memory DB, demo data)
- `/changes` text + typed for late, budget, closure, walking, skip; needs-clarification response shape; `/swap`; `/restore` + `GET itinerary` follows `current_version`; `/simulate` closure + delay; `/replans` list; 409 lock; 404s.

### Edge Cases
- Delay pushing everything past day end; closure of a locked activity (rejected: ask); swap with a backup id that is not stored (404); restore to unknown version (404); change after undo creates max+1; no LLM keys (rule-based path works); a day with no activities.

---

## VALIDATION COMMANDS

### Level 1: Syntax & Style
- `cd backend && ruff check .`
- `cd frontend && npm run lint && npm run check`

### Level 2: Unit Tests
- `cd backend && GOOGLE_API_KEY= NVIDIA_API_KEY= pytest -q --ignore=tests/test_preferences_live.py`

### Level 3: Integration Tests
- `cd backend && pytest tests/test_changes_api.py -q`
- `cd frontend && npm test && npm run build`

### Level 4: Manual Validation (live, local)
- Backend: `DEMO_MODE=false LLM_PRIMARY=nvidia DATABASE_URL=sqlite:///./tripagent.db uvicorn app.main:app --port 8000`
- Frontend: `VITE_DEMO_MODE=false VITE_MAPBOX_PUBLIC_TOKEN=<pk token from .env> npm run dev -- --port 5190 --host 127.0.0.1`
- Browser (Playwright script): plan Seattle -> Adjust "I'm 90 minutes late" -> "my budget is now $300" -> "the <stop> is closed today" -> Swap a backup -> Undo -> quick "Switch to walking" -> quick "Skip something"; screenshot each; check change summary text, version chip, trace (interpret/explain llm steps), no console errors.

---

## ACCEPTANCE CRITERIA

- [ ] AC 1: A5 turns text and quick chips into a validated change; asks one question when unsure; A7 writes a summary grounded only in the diff, with a code fallback.
- [ ] AC 2: Only affected activities change (unaffected keep id, place, start, end); done/locked never change; A6 repair runs on the current itinerary.
- [ ] AC 3: Each change saves version N+1 and a ReplanEvent; `/replans`, `/versions`, `/itinerary?version=` return them.
- [ ] AC 4: Undo moves the current version back; nothing deleted; a later change creates max+1.
- [ ] AC 5: Late, budget, closure, swap, undo, walking, skip all work end to end (API tests + live browser run).
- [ ] AC 6: Every loop/limit from config; named end states; no invented data.
- [ ] AC 7: Adjust trip / Swap / Undo visible and working in live mode; new UI text in docs/06.
- [ ] AC 8: ruff, pytest, lint, type check, vitest, build all pass; key new tests fail on the old code; nothing merged.

## COMPLETION CHECKLIST

- [ ] All tasks done in order, each validated
- [ ] Full test suites pass
- [ ] Live browser run with screenshots
- [ ] PR opened (base `fix/small-things`), not merged

## OPEN QUESTIONS / ASSUMPTIONS

- Assumed: replanning runs synchronously like `POST /plan` (the frontend polls `/runs/{id}` and gets "done" at once).
- Assumed: the L4 pipeline is a plain module (`replan.py`) rather than a second LangGraph graph; trace events keep the same shape. Can move into LangGraph later without API changes.
- Assumed: "Mix it up" (simulate `diversity`) answers 422 "not supported yet" in live mode until a diversity repair exists; the button stays hidden in live mode.

## NOTES (open canvas)

- Why a current-version pointer and not a copied version on Undo: matches the demo engine (`restoreVersion`), keeps `versions` honest, and `ChangeSummaryPanel`/`undo()` already compute "previous" from the list.
- Why persist candidate places (`trip_places`): SRS §7 step 4 cascade "stored backups, then nearby search"; the initial search pool is the cheapest "nearby" pool and avoids new provider calls during a change. A widened live search can be added later.
- Risk: LLM latency on free tiers. A5 + A7 add ~2 calls per change (plus up to 5 A6 choices). Fallbacks keep it working if both LLMs are down.
- Risk: refactoring `build_plan_with_repairs` — guarded by the existing planner/repair tests (they must pass unchanged).

## AMENDMENTS

- 2026-11-12 — Must also work on the deployed version (Render web service + Neon Postgres), verified as far as
  possible without merging:
  - New tables are created by `metadata.create_all` on start (works on the existing Neon DB; existing tables are
    never altered). JSON columns, ordering by id and the version pointer must behave the same on Postgres.
  - Per-trip lock is in-process: correct for Render's single uvicorn process (free plan); note it in code.
  - No new secrets or env vars needed on Render; `CHANGES_AVAILABLE` is true in the live build.
  - **Validation (new Level 4b):** create a temporary Neon branch (`neon branches create`), point the local backend
    at that branch's `DATABASE_URL` (never printed), run the API change flow (plan -> late -> budget -> closure ->
    swap -> undo -> walking -> skip) against Postgres, then delete the branch. Production data is never touched.
  - After the user merges (their decision), run the same 7 actions against
    `https://tripagent-api-lavanyabansal03.onrender.com` and the live website.
  - **AC 9:** the full change flow passes against Neon Postgres (temporary branch).
