# TripAgent: Getting Started: How We Begin

_Who does what, the tools we use, and how to set up your laptop. Final presentation: Monday, November 2, 2026._

> **You do not need to read all the other documents.** This page is enough to get started. When a task needs more detail, it will point you to the right page.

## What we are building

TripAgent is a web app that plans a trip for you. You tell it where you are going and what you like. It finds real places, puts them into a day-by-day plan on a map, and checks that the plan actually works (opening hours, travel time, budget). If something changes, like "I'm running late" or "my budget is lower", it fixes only the part that broke and tells you why.

**Final presentation: Monday, November 2.** We build it in small pieces, and every piece should work from start to finish before we add the next one.

## Our timeline

| When | What we finish |
|---|---|
| Oct 5 - Oct 11 | A user types their trip, and the app understands and saves it. It is online. |
| Oct 12 - Oct 18 | The app makes a real day-by-day plan with a map and checks it. |
| Oct 19 - Oct 25 | The app fixes the plan when something changes. |
| Oct 26 - Nov 1 | Fix bugs, practice the demo. No new features after Oct 30. |

## Who does what

Each person owns one area but helps the others. Roles: **Preferences - Kaleb**, **Validation - Harshita**, **Agent Graph - Sathwika**, **Tools - Nitin**, **Frontend & Maps - Yahya**.

| Role | In simple words, you build... | Your first task (this week) |
|---|---|---|
| Preferences | The part that reads what the user typed and turns it into clear settings (likes, dislikes, budget, pace). | Write 10 example trip descriptions and what the app should understand from each. |
| Validation | The rules that check the plan: no overlaps, open when we visit, under budget, not too far apart. | Turn the data shapes we agreed into Pydantic models (Trip, Preferences, Place, Activity) by Wednesday. |
| Agent Graph | The "brain" that runs the steps in order and repeats a step when the plan fails a check. | Build a tiny LangGraph example with a loop that stops after 3 tries. |
| Tools | The backend API and the connections to Mapbox (maps, travel time) and Foursquare (place details). | Build POST /api/trips to save a trip, and test Mapbox and Foursquare for 30 places. |
| Frontend & Maps | Everything the user sees: the trip form, the plan, and the map. | Sketch the 3 main screens, then build the trip form with the big "Tell us more" box. |

## Tech stack

| Part | Tool | What it does for us |
|---|---|---|
| Editor | VS Code | Where we write all the code |
| Code sharing | Git + GitHub | Saves our code history and lets us review each other's work |
| Backend | Python 3.12 + FastAPI | The server that the website talks to |
| AI steps | LangGraph + Gemini API (free) | Runs the agent steps and understands text |
| Data checks | Pydantic | Makes sure data has the right shape |
| Database | SQLite (on laptop), Postgres (online) | Saves trips and plans |
| Maps and places | Mapbox + Foursquare | Real places, travel times, the map |
| Frontend | Svelte + Vite + TypeScript | The website |
| Tests | pytest (backend), Vitest (frontend) | Checks our code still works |

## Step-by-step setup (everyone)

### 1. Install these

- **VS Code**, **Git**, **Python 3.12**, **Node.js (LTS version)**, and a **GitHub account**.
- VS Code extensions: Python, Pylance, Ruff, ESLint, Prettier, Svelte for VS Code, GitLens, GitHub Pull Requests. Check: `git --version`, `python --version`, `node --version`.

### 2. Get the project

The project lead creates a GitHub repo called `tripagent`, adds everyone, turns on "require a review before merging", and pushes a small starter version (a hello-world backend and frontend). Then each of you runs:

```
git clone https://github.com/<our-org>/tripagent.git && cd tripagent && code .
# Backend (terminal 1)
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt    # FastAPI, LangGraph, Gemini, Pydantic, pytest
uvicorn app.main:app --reload      # open http://localhost:8000/docs
# Frontend (terminal 2)
cd frontend
npm install
npm run dev                        # open http://localhost:5173
```

### 3. Project folders

```
backend/app/   api, agents, graph, tools, validation, models      backend/tests/
frontend/src/  components, pages, styles                         docs/  our documents
```

### 4. Settings and keys

Copy `.env.example` to `.env`. Start with `DEMO_MODE=true`, which uses saved sample data, so you do not need any API keys on day one. Get your own free Gemini key in Google AI Studio (your own project). Mapbox and Foursquare keys are shared privately by the lead. **Never put keys in GitHub.** The `.env` file is already in `.gitignore`.

## How we work with Git

1. Never work directly on `main`. For each task, make a branch: `git checkout -b feature/US-01-trip-form`.
2. Save small steps often: `git add .` then `git commit -m "Add trip form fields"`.
3. Push and open a Pull Request on GitHub. One teammate reviews it before it is merged.
4. Pull `main` every morning so you have everyone's latest work: `git pull origin main`.

## Sprint 1, day by day

| Day | What happens |
|---|---|
| Mon Oct 5 | Kickoff meeting: roles, data shapes agreed, Sprint 1 tasks. Start your first task. |
| Tue Oct 6 - Wed Oct 7 | Everyone runs the project and has a Gemini key. Data shapes merged as Pydantic models. |
| Thu Oct 8 | Check-in: 3-minute show-and-tell each. Hello-world app online. |
| Fri Oct 9 - Sun Oct 11 | Finish your tasks and connect the pieces: form -> save -> understand -> show. |
| Mon Oct 12 | Sprint 1 demo, then plan Sprint 2. |

### Team rules

- **Stuck for more than 30 minutes? Ask in the team chat.** Asking early is a skill, not a weakness.
- Quick update in the chat on Monday, Wednesday and Friday: what I did, what I will do, what is blocking me.
