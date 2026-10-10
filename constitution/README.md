# TripAgent Constitution

The short, stable core of the project: **why** we are building TripAgent, **what** we ship
and **when**, and **what we build it with**. It is condensed from the documents in `docs/`
(v2.3, October 5, 2026), `CLAUDE.md` and `README.md`.

The constitution summarizes the docs; it does not replace them. Each section links to the
source document it came from. If the constitution and a source document disagree, follow the
source-of-truth order in [CLAUDE.md](../CLAUDE.md) and update the constitution.

## Contents

| Folder | File | Answers |
|---|---|---|
| [01-mission/](01-mission/) | [mission.md](01-mission/mission.md) | Why TripAgent exists, who it serves, the non-negotiable principles, and what is out of scope |
| [02-roadmap/](02-roadmap/) | [roadmap.md](02-roadmap/roadmap.md) | Sprints, dates, milestones, and every backlog task with a status column |
| [03-tech-stack/](03-tech-stack/) | [tech-stack.md](03-tech-stack/tech-stack.md) | Languages, frameworks, providers, tooling, and what is planned vs. installed today |
| [04-open-questions/](04-open-questions/) | [open-questions.md](04-open-questions/open-questions.md) | Inconsistencies found across the docs, how each was resolved, and decisions still open |
| [05-team/](05-team/) | [team.md](05-team/team.md) | Who holds each role, folder ownership, working branches |

## How to use it

- **New to the project?** Read the mission, then the roadmap row for the current sprint.
- **Picking up a task?** Find its ID in the roadmap, then open the source doc it points to.
- **Tracking progress?** Update the `Status` column in the roadmap task tables.

## Status values used in the roadmap

| Status | Meaning |
|---|---|
| Not started | No code found for it |
| In progress | Partial code exists, acceptance criteria not yet met |
| Done | Acceptance criteria met and merged to `main` |
| Not verified | Not yet checked against the code |
