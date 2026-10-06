# Team

_Sources: [05_sprint_plan_backlog.md](../../docs/05_sprint_plan_backlog.md) section 1, [00_getting_started.md](../../docs/00_getting_started.md)_

| Role | Person | Home area | Owns folder(s) | Working branch(es) |
|---|---|---|---|---|
| Preferences Eng. | Kaleb | Intake, preferences, ranking, diversity, Explainer, golden sets | `backend/app/agents/` (shared) | |
| Validation Eng. | Harshita | Models, validators, impact analysis, scenario benchmark | `backend/app/validation/`, `backend/app/models/` | |
| Agent Graph Eng. | Sathwika | LangGraph workflow, loops, planner/scheduler, repair | `backend/app/graph/`, `backend/app/agents/` (shared) | `sathwika21n--AgentGraph` (name as given; confirm exact spelling with git) |
| Tools Eng. | Nitin | FastAPI, tool adapters, maps/routing, events, fallback | `backend/app/api/`, `backend/app/tools/` | |
| Frontend & Maps Eng. | Yahya | Frontend, map UI, trace UI, deployment, E2E | `frontend/` | |

Product Owner / Tech Lead: _to confirm_.

## How we work

- One branch per task: `feature/<story-id>-short-name`.
- PRs need 1 review; 2 for shared models, graph edges or prompts.
- Async stand-up Mon / Wed / Fri in team chat; check-in Thursday; review, retro and planning Monday.
- Stuck for more than 30 minutes? Ask in the team chat.
