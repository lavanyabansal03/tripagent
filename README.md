# TripAgent

## What this is
TripAgent is an AI trip-planning web app: you describe a trip and it builds a day-by-day plan. It uses a Python/FastAPI backend with Google Gemini agents and a React frontend.

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

## Run tests
```bash
# Backend (from backend/, with the venv active)
ruff check
pytest

# Frontend (from frontend/)
npm test
```

## Git rules
- Make a new branch for every task: `git checkout -b <your-name>/<short-task-name>`
- Open a Pull Request into `main`; it needs **1 review** and passing CI before merging.
- **Never commit `.env`** or any real API key.

## Folder owners
| Folder | Owner |
|---|---|
| `backend/app/api/` | Tools Eng. |
| `backend/app/agents/` | Preferences Eng. + Agent Graph Eng. |
| `backend/app/graph/` | Agent Graph Eng. |
| `backend/app/tools/` | Tools Eng. |
| `backend/app/validation/` | Validation Eng. |
| `backend/app/models/` | Validation Eng. (shared data models) |
| `frontend/` | Frontend & Maps Eng. |
