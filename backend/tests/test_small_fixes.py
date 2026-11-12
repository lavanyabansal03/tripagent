"""Small fixes: honest budget text, real step times, searches run at the same time."""

import time

from langgraph.checkpoint.memory import InMemorySaver

from app import tools
from app.agents.backup import find_backups
from app.agents.discovery import discover_places
from app.config import settings
from app.graph.trip_planner import build_trip_graph
from app.tools.mock_places import MockPlaceSearch
from app.tools.parallel import run_all
from app.validation.budget import check_budget

# --- Budget text does not say "passed" when prices are unknown ---------------


def test_unknown_prices_are_not_called_a_pass():
    activities = [{"id": "a", "est_cost": None}, {"id": "b", "est_cost": 10}]

    result = check_budget(activities, 300, "strict")

    assert result.passed is False and result.severity == "data-gap"
    assert "passed" not in result.message.lower()
    assert "not fully checked" in result.message
    assert "1 activities have unknown costs" in result.message


def test_known_prices_within_budget_still_pass():
    result = check_budget([{"id": "a", "est_cost": 10}], 300, "strict")

    assert result.passed is True
    assert "Budget check passed" in result.message


# --- Searches run at the same time -----------------------------------------------


class SlowSearch:
    """Takes 0.2 s per search, like a network call."""

    def __init__(self):
        self.mock = MockPlaceSearch()

    def search_places(self, **kwargs):
        time.sleep(0.2)
        return self.mock.search_places(**{**kwargs, "near": None, "radius_min": None})


def test_run_all_keeps_order_and_returns_errors():
    def boom():
        raise ValueError("down")

    results = run_all([lambda: 1, boom, lambda: 3])

    assert results[0] == 1 and isinstance(results[1], ValueError) and results[2] == 3


def test_discovery_searches_for_each_interest_together():
    trip = {"mode": "walking", "interests": ["cafe", "museum", "park", "market"]}

    started = time.perf_counter()
    result = discover_places(trip, search=SlowSearch())
    seconds = time.perf_counter() - started

    assert result.calls_used >= 4
    assert seconds < 0.2 * result.calls_used - 0.2  # one after another would take longer


def test_backup_searches_run_together():
    place = {
        "id": "orig", "name": "Original Cafe", "experience_types": ["cafe"],
        "categories": ["cafe"], "lat": 47.61, "lng": -122.34, "hours": None,
        "est_cost_low": 5, "est_cost_high": 5,
    }
    activities = [
        {
            "id": f"A{i}", "day": 1, "place_id": "orig", "priority": "medium",
            "status": "planned", "est_cost": 5, "purpose_tags": ["cafe"], "place": place,
            "start": f"2026-11-10T{10 + i}:00:00-08:00", "end": f"2026-11-10T{10 + i}:30:00-08:00",
        }
        for i in range(4)
    ]
    plan = {"trip_id": "t", "version": 1, "requirements": {"mode": "walking"},
            "days": [{"day": 1, "activities": activities}]}

    started = time.perf_counter()
    results = find_backups(plan, search=SlowSearch())
    seconds = time.perf_counter() - started

    assert len(results) == 4
    assert seconds < 0.6  # four 0.2 s searches one after another would take 0.8 s


# --- The Agent trace shows real step times ----------------------------------------


def test_trace_steps_have_real_durations():
    def slow_search(trip):
        time.sleep(0.05)
        return MockPlaceSearch().search_places(categories=["cafe"]), {}, 0

    def to_dicts(trip):
        places, words, ms = slow_search(trip)
        return [p.model_dump(mode="json") for p in places], words, ms

    graph = build_trip_graph(checkpointer=InMemorySaver(), search=to_dicts)
    result = graph.invoke(
        {"trip": {"destination": "Seattle", "start_date": "2026-11-12",
                  "end_date": "2026-11-12", "interests": ["cafe"]}},
        {"configurable": {"thread_id": "timing"}},
    )

    find = next(e for e in result["logs"] if e["node"] == "find")
    assert find["duration_ms"] >= 40
    assert all(e["duration_ms"] >= 0 for e in result["logs"])


# --- One Geoapify search (and connection) is reused --------------------------------


def test_live_place_search_is_reused(monkeypatch):
    monkeypatch.setattr(settings, "DEMO_MODE", False)
    monkeypatch.setattr(settings, "GEOAPIFY_API_KEY", "key-1")

    first, second = tools.get_place_search(), tools.get_place_search()
    monkeypatch.setattr(settings, "GEOAPIFY_API_KEY", "key-2")
    third = tools.get_place_search()

    assert first is second
    assert third is not first  # a new key gets a new search
