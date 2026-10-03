"""First TripAgent workflow: read, clarify, find sample places, and save."""

from collections.abc import Callable
from typing import Any, TypedDict

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

MAX_CLARIFICATION_ATTEMPTS = 2
MAX_FIND_ATTEMPTS = 3


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


def _log(state: TripState, step: str, message: str, **details: Any) -> list[dict[str, Any]]:
    entry = {"step": step, "message": message, **details}
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


def _after_read(state: TripState) -> str:
    return "ask_question" if _missing_dates(state) else "find_places"


def _ask_question(state: TripState) -> dict[str, Any]:
    attempt = state.get("clarification_attempts", 0) + 1
    missing = _missing_dates(state)
    question = {
        "kind": "trip_dates",
        "fields": missing,
        "prompt": "What are your trip dates? Please provide the missing start and end dates.",
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
    if not _missing_dates(state):
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


def _find_places(
    state: TripState, search: Callable[[dict[str, Any]], list[dict[str, str]]]
) -> dict[str, Any]:
    attempt = state.get("find_attempts", 0) + 1
    try:
        places = search(state.get("trip", {}))
        return {
            "places": places,
            "find_attempts": attempt,
            "find_error": "",
            "logs": _log(state, "find", f"Found {len(places)} sample places", attempt=attempt),
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
    search: Callable[[dict[str, Any]], list[dict[str, str]]] = _sample_places,
    save: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
):
    """Build a resumable graph. External search/save functions are injectable for tests."""
    def find_node(state: TripState) -> dict[str, Any]:
        return _find_places(state, search)

    def save_node(state: TripState) -> dict[str, Any]:
        record = {"trip": state.get("trip", {}), "places": state.get("places", [])}
        attempt = state.get("save_attempts", 0) + 1
        try:
            saved_trip = (save or (lambda value: value))(record)
            return {
                "saved_trip": saved_trip,
                "save_attempts": attempt,
                "save_error": "",
                "status": "completed",
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
            "save_trip": "save_trip",
            "explain_failure": "explain_failure",
        },
    )
    graph.add_conditional_edges(
        "save_trip",
        after_save,
        {"done": END, "save_trip": "save_trip", "explain_failure": "explain_failure"},
    )
    graph.add_edge("explain_failure", END)
    return graph.compile(checkpointer=checkpointer or InMemorySaver())