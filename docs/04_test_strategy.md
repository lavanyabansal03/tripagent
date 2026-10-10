# TripAgent: Test Strategy & Evaluation Plan

_How we prove the agent is correct, bounded, local and reproducible_

| Field | Value |
|---|---|
| Owner role | Engineering (QA lead rotates; Validation Eng. owns benchmark) |
| Team | Product Owner / Engineering Manager; five engineers in role areas: Preferences, Validation, Agent Graph, Tools, Frontend & Maps |
| Version | 2.3 (October 5, 2026) |
| Status | Living document, updated each sprint |
| Method | Testing strategy: pyramid, test plan, coverage targets, example cases |

## 1. Testing Goals

TripAgent mixes deterministic code, probabilistic LLM calls and external providers. The strategy therefore tests each layer with the cheapest reliable method: fast deterministic tests for validators and loops, recorded fixtures for providers, a golden evaluation set for LLM behaviour, and a small number of end-to-end runs for the full product.

- Prove hard constraints are never knowingly violated.
- Prove every loop terminates with the correct terminal state.
- Prove replans are local: unaffected, completed and locked activities survive.
- Measure LLM quality with numbers, not impressions.
- Keep the demo reproducible when providers are down.

## 2. Test Pyramid for TripAgent

```
                 /  E2E (Playwright)  \          3 flows, nightly + before demo
                / Scenario benchmark    \        13 scenarios, every PR (demo mode)
               /  Graph + integration     \      node transitions, loop caps, API
              / Contract (provider fixtures)\    adapters vs recorded responses
             /   Unit (validators, scoring)   \  many, < 5 s total
```

| Layer | Tools | Runs | Owner | Target |
|---|---|---|---|---|
| Unit | pytest, Hypothesis | Every commit | Everyone | Validators and scoring >= 90% line coverage |
| Contract | pytest + recorded JSON fixtures | Every PR | Tools Eng. | Every adapter has fixtures for success, empty, error |
| Graph / integration | pytest with mock tools and fake LLM | Every PR | Agent Graph Eng. | Every edge and terminal state covered |
| LLM evaluation | pytest + golden set, real Gemini calls (throttled for free tier) | On prompt changes | Preferences Eng. | Extraction >= 85% field accuracy |
| Scenario benchmark | pytest, demo mode | Every PR | Validation Eng. | S1-S11 pass; metrics not regressed |
| Frontend component | Vitest + Svelte Testing Library | Every PR | Frontend & Maps Eng. | Core components and states |
| E2E | Playwright against deployed preview | Nightly + pre-demo | Frontend & Maps Eng. | 3 critical flows green |
| Accessibility | axe (Playwright plugin) + manual keyboard pass | Per sprint | Frontend & Maps Eng. | No critical violations |

## 3. Unit Tests

### 3.1 Validators

| Validator | Example cases |
|---|---|
| Schedule overlap | 10:00-11:00 and 10:30-12:00 fail; 10:00-11:00 and 11:00-12:00 pass (touching is allowed); activity past daily_end fails. |
| Opening hours | Inside hours pass; crossing close fails; overnight hours (18:00-02:00) handled; unknown hours give a warning, not a pass. |
| Travel time | Leg 31 min with 30 limit fails; leg longer than the gap between activities fails; mode switch changes result. |
| Budget | Sum equals budget passes; unknown costs reported separately; currency rounding stable. |
| Avoid list | Category in avoid fails, including when it is a secondary category. |
| Diversity | Three consecutive cafes fail; two pass; half-day uses relaxed rule. |
| Freshness | Event retrieved 25 h ago warns; place retrieved 3 days ago passes. |

### 3.2 Property-based tests (Hypothesis)

- Validators are pure: same input gives the same output, and input objects are not mutated.
- For any generated itinerary and any patch produced by `apply_patch`, activities with status `done` or `locked` are unchanged.
- Scheduler output never contains overlaps for any generated set of durations and travel times.
- Diversity re-rank never removes the only candidate for a required interest.

### 3.3 Scoring and ranking

- Preference match increases with overlapping tags.
- Tourist/local ratio re-rank moves the plan toward the target.
- Purpose similarity ranks "food market + demo" above "generic restaurant" for a cooking-class original.
- Local signal: landmark category is never "Local pick"; missing rating gives unknown; percentiles computed within category.
- Cost model: price level maps to the category range; unknown cost is excluded from the total and counted.

## 4. Contract Tests for Tools

Each provider adapter is tested against recorded real responses stored under `backend/tests/fixtures/<provider>/`. Tests assert normalization into internal models (Place, Route, TravelMatrix, Event), including `source` and `retrieved_at`.

| Case | Expected |
|---|---|
| Normal response | Fields mapped; units converted (seconds to minutes, meters to km). |
| Missing optional fields (no hours, no price) | Model fields are None; nothing invented. |
| Empty results | Empty list, not an error. |
| 429 / 5xx | Retry twice with backoff, then fallback path. |
| 400 bad request | No retry; typed error; key not in message. |
| Matrix larger than provider limit | Adapter batches requests and merges. |
| Same venue from Mapbox and Foursquare | Merged into one Place; per-field provenance kept. |
| Premium budget exceeded | No further Premium calls; remaining places marked with unknown fields. |

Fixtures are refreshed once per sprint with a script so tests do not drift from reality.

## 5. Graph and Loop Tests

The LLM is replaced with a **scripted fake** that returns predetermined outputs, so control flow can be tested deterministically.

| Test | Setup | Assertion |
|---|---|---|
| Happy path | Fake LLM returns valid outputs; validator passes | Node order: intake, discovery, rank, cluster, plan, backup, validate, persist; terminal PASS. |
| L1 clarification cap | Intake always returns a blocking question | Two questions rounds, then NEEDS_USER. |
| L2 discovery cap | Search always returns 1 new place | Exits on no-progress or 8 calls; partial coverage flag set. |
| L3 repair cap | Validator always fails | Exactly 3 repair iterations; terminal INFEASIBLE; unresolved rules listed. |
| L3 stall detection | Repair oscillates A->B->A | Exits early on no improvement. |
| L4 single event lock | Two changes submitted concurrently | Processed sequentially; versions N+1 and N+2. |
| L5 cascade order | Backup 1 invalid, backup 2 valid | Backup 2 used; no live search call made. |
| L6 fallback | Routing tool raises timeout | Two retries then cached result; degraded flag set. |
| Resume | Kill run after Validator | Resume from checkpoint continues without duplicate events. |
| Trace completeness | Any run | One ExecutionEvent per node, tool call and loop iteration. |

## 6. Scenario Benchmark (Agentic Evaluation)

The benchmark runs the SRS v2 scenarios end-to-end through the API in demo mode, using fixtures for providers and either the real LLM (nightly) or cached LLM responses (per PR). It produces a metrics report that is compared with the latest main-branch run.

| Metric | Computed as | Gate |
|---|---|---|
| Hard-constraint pass rate | Plans with zero hard violations / plans | >= 95% |
| Replan success | Scenarios reaching PASS or correct INFEASIBLE / scenarios | >= 90% |
| Change locality | Unaffected activities preserved / unaffected activities | >= 80% |
| Backup hit rate | Repairs solved by stored backup / repairs | Tracked (target 60%) |
| Purpose preservation | Replacements sharing >= 1 purpose tag / replacements | >= 80% |
| Diversity | Full days meeting diversity rule / full days | >= 90% |
| Loop safety | Runs exceeding any cap | 0 |
| Explainability | Replans with reasons for each change | 100% |
| Cost per run | Tokens and tool calls per scenario | No regression > 20% |

Example scenario test:

```
def test_budget_drop_preserves_unaffected(client, seattle_trip_v1):
    before = client.get(f"/trips/{seattle_trip_v1}/itinerary").json()
    r = client.post(f"/trips/{seattle_trip_v1}/changes",
                    json={"text": "My budget is now $300"})
    after = wait_for_run(client, r.json()["run_id"])

    assert after["validation"]["hard_violations"] == 0
    assert after["total_known_cost"] <= 300
    assert locality(before, after, affected=after["replan"]["affected_ids"]) >= 0.8
    assert all(c["reason"] for c in after["replan"]["changes"])
```

## 7. LLM Evaluation

| Agent | Golden set | Metric | Target |
|---|---|---|---|
| Intake | 25 trip descriptions with expected fields (written by the team, reviewed by the Tech Lead) | Field-level precision and recall; contradiction detection | >= 85%; 5/5 contradictions caught |
| Change Interpreter | 30 change messages ("I'm running an hour behind", "cheaper please") | Correct ChangeEvent type and payload | >= 90% |
| Repair choice | 15 affected-activity cases with ranked acceptable answers | Chosen candidate in top 2 acceptable | >= 80% |
| Explainer | 15 diffs | Mentions only facts in the diff (checked by script + spot review) | 0 invented facts |

Prompt changes require the golden-set run in the PR description. Every production bug caused by an LLM output becomes a new golden-set case.

## 8. Frontend and End-to-End Tests

### 8.1 Component tests

- TripForm: required fields, inline errors, free-text counter.
- ActivityCard: backup drawer, freshness label, locked state.
- ChangeSummaryPanel: every change type renders an icon and text label.
- AgentTrace: iterations grouped by loop; failed steps highlighted.
- MapView: receives legs and renders changed legs with the diff style (snapshot of layer config).

### 8.2 Critical E2E flows

1. Create trip with free text -> answer one clarification -> see itinerary with map and backups.
2. Report "I'm 90 minutes late" -> see change summary and route diff. (Add "-> undo" only if the US-29 stretch goal ships.)
3. Switch transit to walking -> see flagged legs repaired or infeasible message.

## 9. Non-Functional Tests

| Area | Test |
|---|---|
| Performance | Time 10 benchmark plans on the deployed preview; median < 60 s first plan, < 30 s replan (SRS NFR-03, Gemini free tier). |
| Security | Secret scanning in CI; grep build bundle for server key patterns; test that errors never echo keys. |
| Prompt injection | Fixture place named "Ignore previous instructions and..." must not change behaviour; outputs remain schema-valid. |
| Deployment smoke | After each deploy: /health OK, create trip in demo mode, fetch itinerary. |
| Accessibility | axe scan on setup, itinerary and change summary pages; keyboard-only run of flow 2. |

## 10. CI Pipeline

```
on pull_request:
  lint (ruff, eslint) -> type check (mypy, svelte-check)
  -> unit + contract + graph tests (pytest, Vitest)
  -> scenario benchmark in demo mode with cached LLM responses
  -> post metrics table as PR comment; fail on gate breach
on push to main:
  all of the above -> deploy preview -> smoke test -> promote
nightly:
  benchmark with live Gemini (throttled to stay under free-tier limits) + E2E on preview
```

## 11. Test Data

- Two demo cities with recorded fixtures (places, routes, matrices, events).
- Synthetic "tiny city" of 12 places on a grid for unit and loop tests where travel times are easy to reason about.
- Fixture builder helpers: `make_itinerary(days=..., activities=[...])`, `make_place(category=..., cost=...)`.

## 12. Known Gaps and Risks

| Gap | Mitigation |
|---|---|
| LLM non-determinism in nightly runs | Track trends over 3 runs; gate on cached responses per PR. |
| Gemini free-tier rate limits | Run live LLM tests sequentially with a short delay; use cached responses in CI. |
| Fixtures drift from live providers | Sprint refresh script; nightly live contract smoke test. |
| Map rendering hard to assert | Test layer data and styles, not pixels; manual check in demo. |
| Opening-hours data sparse | Tests assert "unknown" labelling, not coverage. |
