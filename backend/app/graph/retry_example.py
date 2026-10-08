"""A tiny bounded LangGraph loop for learning how conditional edges work."""

from typing import TypedDict

from langgraph.graph import END, START, StateGraph


class RetryState(TypedDict, total=False):
    attempt: int
    max_attempts: int
    succeed_on_try: int
    succeeded: bool
    explanation: str
    logs: list[str]


def _try_once(state: RetryState) -> dict:
    attempt = state.get("attempt", 0) + 1
    succeeded = attempt >= state.get("succeed_on_try", 2)
    result = "succeeded" if succeeded else "not ready"
    return {
        "attempt": attempt,
        "succeeded": succeeded,
        "logs": [*state.get("logs", []), f"try {attempt}: {result}"],
    }


def _route(state: RetryState) -> str:
    if state.get("succeeded"):
        return "done"
    if state.get("attempt", 0) >= state.get("max_attempts", 3):
        return "exhausted"
    return "retry"


def _explain_failure(state: RetryState) -> dict:
    return {
        "explanation": f"Stopped after {state.get('attempt', 0)} tries.",
        "logs": [*state.get("logs", []), "retry limit reached"],
    }


def build_retry_example():
    """Build the small graph; the caller chooses the retry limit and outcome."""
    graph = StateGraph(RetryState)
    graph.add_node("try_once", _try_once)
    graph.add_node("explain_failure", _explain_failure)
    graph.add_edge(START, "try_once")
    graph.add_conditional_edges(
        "try_once",
        _route,
        {"done": END, "retry": "try_once", "exhausted": "explain_failure"},
    )
    graph.add_edge("explain_failure", END)
    return graph.compile()


def run_retry_example(succeed_on_try: int = 2, max_attempts: int = 3) -> RetryState:
    """Run the example, succeeding on the requested attempt or stopping at the cap."""
    if max_attempts < 1:
        raise ValueError("max_attempts must be at least 1")
    return build_retry_example().invoke(
        {
            "attempt": 0,
            "max_attempts": max_attempts,
            "succeed_on_try": succeed_on_try,
            "logs": [],
        }
    )