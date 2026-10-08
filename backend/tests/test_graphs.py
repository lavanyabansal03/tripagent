from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from app.graph.retry_example import run_retry_example
from app.graph.trip_planner import MAX_FIND_ATTEMPTS, build_trip_graph


def test_learning_loop_succeeds_before_three_tries():
    result = run_retry_example(succeed_on_try=2)

    assert result["attempt"] == 2
    assert result["succeeded"] is True
    assert len(result["logs"]) == 2


def test_learning_loop_stops_after_three_tries():
    result = run_retry_example(succeed_on_try=4)

    assert result["attempt"] == 3
    assert result["succeeded"] is False
    assert result["explanation"] == "Stopped after 3 tries."


def test_trip_graph_asks_for_dates_then_runs_in_order():
    checkpointer = InMemorySaver()
    graph = build_trip_graph(checkpointer=checkpointer)
    config = {"configurable": {"thread_id": "test-trip"}}
    graph.invoke({"trip": {"destination": "Lisbon"}, "logs": []}, config)

    waiting = graph.get_state(config).values
    assert waiting["status"] == "awaiting_input"
    assert waiting["question"]["fields"] == ["start_date", "end_date"]
    assert waiting["logs"][0]["step"] == "read"
    assert waiting["logs"][1]["step"] == "ask_question"

    result = graph.invoke(
        Command(resume={"start_date": "2026-11-01", "end_date": "2026-11-05"}), config
    )

    assert result["status"] == "completed"
    assert [entry["step"] for entry in result["logs"]] == [
        "read",
        "ask_question",
        "answer",
        "find",
        "save",
    ]
    assert len(result["places"]) == 3


def test_trip_graph_stops_after_two_unanswered_clarifications():
    graph = build_trip_graph(checkpointer=InMemorySaver())
    config = {"configurable": {"thread_id": "missing-dates"}}
    graph.invoke({"trip": {"destination": "Oslo"}, "logs": []}, config)
    graph.invoke(Command(resume={"start_date": None, "end_date": None}), config)
    waiting_again = graph.get_state(config).values
    assert waiting_again["status"] == "awaiting_input"
    assert waiting_again["question"]["attempt"] == 2

    result = graph.invoke(Command(resume={"start_date": None, "end_date": None}), config)
    assert result["status"] == "failed"
    assert "after two questions" in result["explanation"]
    assert "find" not in [entry["step"] for entry in result["logs"]]


def test_place_search_retries_but_never_more_than_three_times():
    calls = 0

    def flaky_search(_trip):
        nonlocal calls
        calls += 1
        if calls < 3:
            raise RuntimeError("temporary search issue")
        return [{"name": "Test place", "category": "test"}]

    graph = build_trip_graph(checkpointer=InMemorySaver(), search=flaky_search)
    result = graph.invoke(
        {"trip": {"destination": "Rome", "start_date": "2026-11-01", "end_date": "2026-11-02"}},
        {"configurable": {"thread_id": "flaky-search"}},
    )

    assert calls == 3
    assert result["status"] == "completed"
    assert [log.get("attempt") for log in result["logs"] if log["step"] == "find"] == [1, 2, 3]


def test_place_search_failure_explains_after_three_tries():
    def failed_search(_trip):
        raise RuntimeError("search unavailable")

    graph = build_trip_graph(checkpointer=InMemorySaver(), search=failed_search)
    result = graph.invoke(
        {"trip": {"destination": "Rome", "start_date": "2026-11-01", "end_date": "2026-11-02"}},
        {"configurable": {"thread_id": "failed-search"}},
    )

    assert result["status"] == "failed"
    assert result["find_attempts"] == MAX_FIND_ATTEMPTS
    assert "search unavailable" in result["explanation"]


def test_save_failure_is_bounded_and_explained():
    calls = 0

    def failed_save(_record):
        nonlocal calls
        calls += 1
        raise RuntimeError("storage unavailable")

    graph = build_trip_graph(checkpointer=InMemorySaver(), save=failed_save)
    result = graph.invoke(
        {"trip": {"destination": "Rome", "start_date": "2026-11-01", "end_date": "2026-11-02"}},
        {"configurable": {"thread_id": "failed-save"}},
    )

    assert calls == MAX_FIND_ATTEMPTS
    assert result["status"] == "failed"
    assert "storage unavailable" in result["explanation"]