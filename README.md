# TripAgent

## What this is
TripAgent is an AI trip-planning web app: you describe a trip and it builds a day-by-day plan. It uses a Python/FastAPI backend with Google Gemini agents and a Svelte frontend.

## Prerequisites
- [VS Code](https://code.visualstudio.com/) (accept the recommended extensions when prompted)
- [Git](https://git-scm.com/)
- [Python 3.12](https://www.python.org/downloads/)
- [Node.js LTS](https://nodejs.org/)

## Run the backend
From the repo root:

```bash
cd backend
python -m venv .venv
```

Activate the virtual environment:

| OS | Command |
|---|---|
| Windows (PowerShell) | `.venv\Scripts\Activate.ps1` |
| Windows (cmd) | `.venv\Scripts\activate.bat` |
| Mac / Linux | `source .venv/bin/activate` |

Then:

```bash
pip install -r requirements.txt
```

Copy `.env.example` (in the repo root) to `.env` in the repo root. API keys are optional for now — the app runs in demo mode without them.

```bash
# Windows
copy ..\.env.example ..\.env
# Mac / Linux
cp ../.env.example ../.env
```

Start the server (from `backend/`):

```bash
uvicorn app.main:app --reload
```

Open http://localhost:8000/docs to see the API.

## Run the frontend
In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. It should say **Backend: connected** while the backend is running.

## LangGraph learning demo

The frontend can start a trip with a destination and optional dates. If dates are missing, the graph
pauses and asks a question; submit the answer to continue. The run shows its step-by-step log and
sample places. The API is also available in `/docs`:

- `POST /api/trips/plan` starts a run.
- `POST /api/trips/{thread_id}/answer` resumes a run that is waiting for dates.

The date question is limited to two attempts. Place search and saving each retry up to three times,
then stop with an explanation. The separate teaching example is `app.graph.retry_example.run_retry_example()`.
Search results and graph checkpoints are demo-only/in-memory; no external place service or durable
database is connected yet.

## Run tests
```bash
# Backend (from backend/, with the venv active)
ruff check
pytest

# Frontend (from frontend/)
npm test
```

## Git rules
- Make a new branch for every task: `git checkout -b feature/<story-id>-short-name` (for example `feature/US-01-trip-form`)
- Open a Pull Request into `main`; it needs **1 review** and passing CI before merging. Changes to shared models, graph edges or prompts need **2 reviews**.
- **Never commit `.env`** or any real API key.

## Folder owners
| Folder | Owner |
|---|---|
| `backend/app/api/` | Tools Eng. (Nitin) |
| `backend/app/agents/` | Preferences Eng. (Kaleb) + Agent Graph Eng. (Sathwika) |
| `backend/app/graph/` | Agent Graph Eng. (Sathwika) |
| `backend/app/tools/` | Tools Eng. (Nitin) |
| `backend/app/validation/` | Validation Eng. (Harshita) |
| `backend/app/models/` | Validation Eng. (Harshita) (shared data models) |
| `frontend/` | Frontend & Maps Eng. (Yahya) |

Project mission, roadmap and tech stack: [constitution/](constitution/README.md).
