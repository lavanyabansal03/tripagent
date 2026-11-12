from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from app.config import MAX_FIND_ATTEMPTS
from app.graph import trip_planner
from app.graph.retry_example import run_retry_example
from app.graph.trip_planner import build_trip_graph
from app.tools.mock_places import MockPlaceSearch


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
    graph.invoke({"trip": {"destination": "Seattle"}, "logs": []}, config)

    waiting = graph.get_state(config).values
    assert waiting["status"] == "awaiting_input"
    assert waiting["question"]["fields"] == ["start_date", "end_date"]
    assert waiting["logs"][0]["node"] == "read"
    assert waiting["logs"][1]["node"] == "ask_question"

    result = graph.invoke(
        Command(resume={"start_date": "2026-11-01", "end_date": "2026-11-05"}), config
    )

    assert result["status"] == "completed"
    nodes = [entry["node"] for entry in result["logs"]]
    assert nodes[:5] == ["read", "ask_question", "answer", "find", "planner"]
    assert "validator" in nodes
    assert nodes[-1] == "save"
    assert len(result["places"]) == 21
    assert len(result["itinerary"]["days"]) == 5
    assert result["itinerary"]["days"][0]["activities"]
    assert result["validation"]


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
    assert "find" not in [entry["node"] for entry in result["logs"]]


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
    find_attempts = [
        log["metadata"].get("attempt") for log in result["logs"] if log["node"] == "find"
    ]
    assert find_attempts == [1, 2, 3]


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


def test_trip_graph_clarifies_reversed_dates_before_search():
    graph = build_trip_graph(checkpointer=InMemorySaver())
    config = {"configurable": {"thread_id": "reversed-dates"}}
    graph.invoke(
        {
            "trip": {
                "destination": "Seattle",
                "start_date": "2026-11-05",
                "end_date": "2026-11-01",
            }
        },
        config,
    )
    waiting = graph.get_state(config).values
    assert waiting["status"] == "awaiting_input"
    assert "End date cannot be before start date" in waiting["question"]["prompt"]

    result = graph.invoke(
        Command(resume={"start_date": "2026-11-01", "end_date": "2026-11-05"}),
        config,
    )
    assert result["status"] == "completed"
    assert "find" in [entry["node"] for entry in result["logs"]]


def test_searches_each_interest_and_merges_results(monkeypatch):
    mock_search = MockPlaceSearch()
    queries = []

    class RecordingSearch:
        def search_places(self, **kwargs):
            queries.append(kwargs["query"])
            return mock_search.search_places(**kwargs)

    # The graph now searches through the Discovery agent (one search per interest).
    # The graph picks the place search itself (so it can check demo mode).
    monkeypatch.setattr(trip_planner, "get_place_search", lambda: RecordingSearch())
    trip = {"destination": "Seattle", "interests": ["coffee", "museums"]}
    places = trip_planner._search_places(trip)

    assert queries[:2] == ["coffee", "museums"]
    # Plus one lunch search, because neither interest brought a restaurant.
    assert set(queries) == {"coffee", "museums", "restaurant"}
    names = {place["name"] for place in places}
    assert "Storyville Coffee Pike Place" in names
    assert "Museum of Pop Culture" in names
    assert "Discovery Park" not in names


def test_save_failure_is_bounded_and_explained():
    calls = 0

    def failed_save(_record):
        nonlocal calls
        calls += 1
        raise RuntimeError("storage unavailable")

    graph = build_trip_graph(checkpointer=InMemorySaver(), save=failed_save)
    result = graph.invoke(
        {"trip": {"destination": "Seattle", "start_date": "2026-11-01", "end_date": "2026-11-02"}},
        {"configurable": {"thread_id": "failed-save"}},
    )

    assert calls == MAX_FIND_ATTEMPTS
    assert result["status"] == "failed"
    assert "storage unavailable" in result["explanation"]