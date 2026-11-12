"""First TripAgent workflow: read, clarify, find sample places, and save."""

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any, TypedDict
from uuid import uuid4

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from app.agents.backup import attach_backups
from app.agents.discovery import discover_places
from app.agents.discovery_plan import plan_with_llm
from app.agents.planner import build_plan_with_repairs
from app.agents.repair_choice import choose_with_llm
from app.config import MAX_CLARIFICATION_ATTEMPTS, MAX_FIND_ATTEMPTS
from app.tools.routes import add_route_legs


class TripState(TypedDict, total=False):
    trip: dict[str, Any]
    places: list[dict[str, str]]
    saved_trip: dict[str, Any]
    logs: list[dict[str, Any]]
    clarification_attempts: int
    find_attempts: int
    save_attempts: int
    question: dict[str, Any]
    status: str
    explanation: str
    find_error: str
    save_error: str
    run_id: str
    itinerary: dict[str, Any]
    validation: list[dict[str, Any]]
    terminal: str
    explanation: str
    repair_iterations: int


def _log(state: TripState, step: str, message: str, **details: Any) -> list[dict[str, Any]]:
    trip = state.get("trip", {})
    event_type = details.pop("event_type", "node")
    entry = {
        "id": str(uuid4()),
        "trip_id": trip.get("trip_id", trip.get("id", "")),
        "run_id": state.get("run_id", ""),
        "node": step,
        "type": event_type,
        "iteration": details.get("attempt", details.get("iteration", 1)),
        "status": "failed" if "error" in details or step == "stop" else "ok",
        "duration_ms": 0,
        "metadata": {"message": message, **details},
        "ts": datetime.now(UTC).isoformat(),
    }
    return [*state.get("logs", []), entry]


def _read_trip(state: TripState) -> dict[str, Any]:
    trip = dict(state.get("trip", {}))
    trip.setdefault("destination", "")
    trip.setdefault("interests", [])
    return {
        "trip": trip,
        "status": "running",
        "logs": _log(state, "read", "Trip details read"),
    }


def _missing_dates(state: TripState) -> list[str]:
    trip = state.get("trip", {})
    return [field for field in ("start_date", "end_date") if not trip.get(field)]


def _date_error(state: TripState) -> str | None:
    trip = state.get("trip", {})
    raw_start, raw_end = trip.get("start_date"), trip.get("end_date")
    try:
        start = datetime.fromisoformat(str(raw_start)).date() if raw_start else None
        end = datetime.fromisoformat(str(raw_end)).date() if raw_end else None
    except ValueError:
        return "Trip dates must use YYYY-MM-DD format. Please correct the trip dates."
    if start is not None and end is not None and end < start:
        return "End date cannot be before start date. Please correct the trip dates."
    return None


def _after_read(state: TripState) -> str:
    if _missing_dates(state) or _date_error(state):
        return "ask_question"
    return "find_places"


def _ask_question(state: TripState) -> dict[str, Any]:
    attempt = state.get("clarification_attempts", 0) + 1
    missing = _missing_dates(state)
    date_error = _date_error(state)
    question = {
        "kind": "trip_dates",
        "fields": missing or ["start_date", "end_date"],
        "prompt": date_error
        or "What are your trip dates? Please provide the missing start and end dates.",
        "attempt": attempt,
        "max_attempts": MAX_CLARIFICATION_ATTEMPTS,
    }
    return {
        "clarification_attempts": attempt,
        "question": question,
        "status": "awaiting_input",
        "logs": _log(state, "ask_question", "Asked for missing trip dates", attempt=attempt),
    }


def _wait_for_answer(state: TripState) -> dict[str, Any]:
    answer = interrupt(state.get("question", {}))
    trip = {**state.get("trip", {}), **{key: value for key, value in answer.items() if value}}
    return {
        "trip": trip,
        "status": "running",
        "logs": _log(state, "answer", "Trip dates received"),
    }


def _after_answer(state: TripState) -> str:
    if not _missing_dates(state) and not _date_error(state):
        return "find_places"
    if state.get("clarification_attempts", 0) >= MAX_CLARIFICATION_ATTEMPTS:
        return "explain_failure"
    return "ask_question"


def _sample_places(trip: dict[str, Any]) -> list[dict[str, str]]:
    destination = trip.get("destination") or "your destination"
    return [
        {"name": f"Old Town Walk in {destination}", "category": "culture"},
        {"name": f"Central Market in {destination}", "category": "food"},
        {"name": f"Riverside Park in {destination}", "category": "outdoors"},
    ]


def _search_places(trip: dict[str, Any]) -> list[dict[str, Any]]:
    """Find candidates with the Discovery agent (one search per interest, capped).

    It uses the shared place-search adapter, so DEMO_MODE stays on the Seattle fixtures.
    """
    return _discover(trip)[0]


def _discover(trip: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, list[str]]]:
    """Like _search_places, plus the LLM's search words for the Agent trace (A2)."""
    result = discover_places(trip, plan=plan_with_llm)
    if result.status == "ERROR":
        raise RuntimeError(result.reason)  # find_places retries, then explains the failure
    return [place.model_dump(mode="json") for place in result.places], result.search_words


def _find_places(
    state: TripState, search: Callable[[dict[str, Any]], list[dict[str, Any]]]
) -> dict[str, Any]:
    attempt = state.get("find_attempts", 0) + 1
    try:
        found = search(state.get("trip", {}))
        # A search may also return the LLM's search words: (places, {interest: words}).
        places, search_words = found if isinstance(found, tuple) else (found, {})
        logs = state.get("logs", [])
        if search_words:
            logs = _log(
                state,
                "search_plan",
                f"LLM chose search words for {len(search_words)} interest(s)",
                event_type="llm",
                search_words=search_words,
            )
        return {
            "places": places,
            "find_attempts": attempt,
            "find_error": "",
            "logs": _log(
                {**state, "logs": logs}, "find", f"Found {len(places)} places", attempt=attempt
            ),
        }
    except Exception as error:  # Keep transient tool failures inside the bounded graph loop.
        return {
            "find_attempts": attempt,
            "find_error": str(error),
            "logs": _log(state, "find", "Place search failed", attempt=attempt, error=str(error)),
        }


def _after_find(state: TripState) -> str:
    if not state.get("find_error"):
        return "save_trip"
    if state.get("find_attempts", 0) >= MAX_FIND_ATTEMPTS:
        return "explain_failure"
    return "find_places"


def _explain_failure(state: TripState) -> dict[str, Any]:
    if _missing_dates(state):
        explanation = (
            "I couldn't continue because the trip dates are still missing after two questions."
        )
    else:
        failed_step = "place search" if state.get("find_error") else "saving the trip"
        attempts = state.get("find_attempts", 0) or state.get("save_attempts", 0)
        error = state.get("find_error") or state.get("save_error", "unknown error")
        explanation = f"{failed_step.capitalize()} failed after {attempts} tries: {error}"
    return {
        "status": "failed",
        "explanation": explanation,
        "logs": _log(state, "stop", explanation),
    }


def build_trip_graph(
    checkpointer: Any | None = None,
    search: Callable[[dict[str, Any]], Any] = _discover,
    save: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
):
    """Build a resumable graph. External search/save functions are injectable for tests."""
    def find_node(state: TripState) -> dict[str, Any]:
        return _find_places(state, search)

    def plan_node(state: TripState) -> dict[str, Any]:
        trip = state.get("trip", {})
        backup_counts: list[int] = []
        backup_errors: list[str] = []

        def add_backups(itinerary: dict[str, Any], only_ids: set[str] | None) -> int:
            # A4 runs before Repair so Repair can try stored backups first (docs/03 5.3).
            # A failure only means no backups; the plan itself is still good.
            try:
                count = attach_backups(itinerary, trip, only_ids=only_ids)
            except Exception as error:
                backup_errors.append(str(error))
                return 0
            backup_counts.append(count)
            return count

        itinerary, validation, repair_iterations, terminal, explanation = build_plan_with_repairs(
            trip, state.get("places", []), add_backups=add_backups, choose=choose_with_llm
        )
        logs = _log(state, "planner", "Built a day-by-day itinerary")
        if backup_errors:
            logs = _log(
                {**state, "logs": logs},
                "backup",
                "Backup search failed; the plan has no backups",
                event_type="tool",
                error=backup_errors[-1],
            )
        else:
            logs = _log(
                {**state, "logs": logs},
                "backup",
                f"Found {backup_counts[-1] if backup_counts else 0} backups",
                event_type="tool",
            )
        for iteration in range(1, repair_iterations + 1):
            logs = _log(
                {**state, "logs": logs},
                "repair",
                "Replaced or rearranged activities and reran validation",
                iteration=iteration,
                event_type="loop",
            )
        choices = [c for c in itinerary.get("repairs", []) if c.get("options", 0) > 1]
        if choices:
            by_llm = [c for c in choices if c.get("chosen_by") == "llm"]
            logs = _log(
                {**state, "logs": logs},
                "repair_choice",
                f"LLM chose {len(by_llm)} of {len(choices)} replacements"
                + ("" if len(by_llm) == len(choices) else "; code chose the rest"),
                event_type="llm",
                choices=[
                    {
                        "old": c["old_place"],
                        "new": c["new_place"],
                        "by": c["chosen_by"],
                        "why": c["why"],
                    }
                    for c in choices
                ],
            )
        # Travel time and route for every stop-to-stop leg, now that the plan is final.
        # A failure only means no route lines; the plan itself is still good.
        try:
            leg_count = add_route_legs(itinerary, trip.get("mode", "walking"))
            sources = sorted({leg["source"] for d in itinerary["days"] for leg in d["legs"]})
            logs = _log(
                {**state, "logs": logs},
                "routes",
                f"Added travel times for {leg_count} legs",
                event_type="tool",
                sources=sources,
            )
        except Exception as error:
            logs = _log(
                {**state, "logs": logs},
                "routes",
                "Travel times between stops failed; the plan has no route lines",
                event_type="tool",
                error=str(error),
            )
        validation_logs = _log(
            {**state, "logs": logs},
            "validator",
            f"Ran {len(validation)} itinerary checks",
            event_type="validation",
            terminal=terminal,
        )
        return {
            "itinerary": itinerary,
            "validation": validation,
            "repair_iterations": repair_iterations,
            "terminal": terminal,
            "explanation": explanation or "",
            "logs": validation_logs,
        }

    def save_node(state: TripState) -> dict[str, Any]:
        record = {
            "trip": state.get("trip", {}),
            "places": state.get("places", []),
            "itinerary": state.get("itinerary", {}),
            "validation": state.get("validation", []),
        }
        attempt = state.get("save_attempts", 0) + 1
        try:
            saved_trip = (save or (lambda value: value))(record)
            return {
                "saved_trip": saved_trip,
                "save_attempts": attempt,
                "save_error": "",
                "status": (
                    "infeasible" if state.get("terminal") == "INFEASIBLE" else "completed"
                ),
                "logs": _log(state, "save", "Trip plan saved", attempt=attempt),
            }
        except Exception as error:  # Keep storage failures inside the bounded graph loop.
            return {
                "save_attempts": attempt,
                "save_error": str(error),
                "logs": _log(
                    state, "save", "Saving trip failed", attempt=attempt, error=str(error)
                ),
            }

    def after_save(state: TripState) -> str:
        if not state.get("save_error"):
            return "done"
        if state.get("save_attempts", 0) >= MAX_FIND_ATTEMPTS:
            return "explain_failure"
        return "save_trip"

    graph = StateGraph(TripState)
    graph.add_node("read_trip", _read_trip)
    graph.add_node("ask_question", _ask_question)
    graph.add_node("wait_for_answer", _wait_for_answer)
    graph.add_node("find_places", find_node)
    graph.add_node("planner", plan_node)
    graph.add_node("save_trip", save_node)
    graph.add_node("explain_failure", _explain_failure)
    graph.add_edge(START, "read_trip")
    graph.add_conditional_edges(
        "read_trip", _after_read, {"ask_question": "ask_question", "find_places": "find_places"}
    )
    graph.add_edge("ask_question", "wait_for_answer")
    graph.add_conditional_edges(
        "wait_for_answer",
        _after_answer,
        {
            "ask_question": "ask_question",
            "find_places": "find_places",
            "explain_failure": "explain_failure",
        },
    )
    graph.add_conditional_edges(
        "find_places",
        _after_find,
        {
            "find_places": "find_places",
            "save_trip": "planner",
            "explain_failure": "explain_failure",
        },
    )
    graph.add_edge("planner", "save_trip")
    graph.add_conditional_edges(
        "save_trip",
        after_save,
        {"done": END, "save_trip": "save_trip", "explain_failure": "explain_failure"},
    )
    graph.add_edge("explain_failure", END)
    return graph.compile(checkpointer=checkpointer or InMemorySaver())
