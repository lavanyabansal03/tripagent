# Team

_Sources: [05_sprint_plan_backlog.md](../../docs/05_sprint_plan_backlog.md) section 1, [00_getting_started.md](../../docs/00_getting_started.md)_

| Role | Person | Home area | Leads AI agent(s) | Owns folder(s) | Working branch(es) |
|---|---|---|---|---|---|
| Preferences Eng. | Kaleb | Intake, change interpretation, preferences, ranking, diversity, golden sets | A1 Intake (S1), A5 Change Interpreter (S3) | `backend/app/agents/` (shared) | |
| Validation Eng. | Harshita | Models, validators, impact analysis, scenario benchmark | A4 Backup (S3) | `backend/app/validation/`, `backend/app/models/` | |
| Agent Graph Eng. | Sathwika | LangGraph workflow, loops, planner/scheduler, repair | A3 Planner (S2), A6 Repair (S3) | `backend/app/graph/`, `backend/app/agents/` (shared) | `sathwika21n--AgentGraph` |
| Tools Eng. | Nitin | FastAPI, tool adapters, maps/routing, events, fallback | A2 Discovery (S2) | `backend/app/api/`, `backend/app/tools/` | |
| Frontend & Maps Eng. | Yahya | Frontend, map UI, trace UI, deployment, E2E | A7 Explainer (S3) | `frontend/` | `yahya-azeem/frontend-svelte` (merged) |

Every engineer leads at least one AI agent (agreed Oct 8, 2026). See [05_sprint_plan_backlog.md](../../docs/05_sprint_plan_backlog.md) section 1.2.

Product Owner / Tech Lead: _to confirm_.

## How we work

- One branch per task: `feature/<story-id>-short-name`.
- PRs need 1 review; 2 for shared models, graph edges or prompts.
- Async stand-up Mon / Wed / Fri in team chat; check-in Thursday; review, retro and planning Monday.
- Stuck for more than 30 minutes? Ask in the team chat.
