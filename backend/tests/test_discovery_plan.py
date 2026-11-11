"""A2 Discovery with an LLM search plan (fake LLMs; no network)."""

from langgraph.checkpoint.memory import InMemorySaver

from app.agents import discovery_plan
from app.agents.discovery import discover_places
from app.agents.discovery_plan import SEARCH_WORDS, SearchPlan, plan_with_llm
from app.graph.trip_planner import build_trip_graph
from app.tools.mock_places import MockPlaceSearch


class RecordingSearch:
    def __init__(self):
        self.calls = []
        self.mock = MockPlaceSearch()

    def search_places(self, **kwargs):
        self.calls.append(kwargs)
        return self.mock.search_places(**kwargs)


TRIP = {"destination": "Seattle", "mode": "walking", "interests": ["hiking", "lattes"]}


# --- Discovery uses the plan, inside the same call limit ---------------------


def test_focused_searches_use_the_llm_words():
    search = RecordingSearch()

    def plan(trip, interests):
        return {"hiking": ["nature", "park"], "lattes": ["cafe"]}

    result = discover_places(TRIP, search=search, plan=plan)

    focused = search.calls[:2]
    assert focused[0]["categories"] == ["nature", "park"] and focused[0]["query"] == ""
    assert focused[1]["categories"] == ["cafe"]
    assert result.search_words == {"hiking": ["nature", "park"], "lattes": ["cafe"]}
    assert result.coverage["hiking"] > 0 and result.coverage["lattes"] > 0


def test_plan_finds_places_that_the_raw_words_miss():
    without = discover_places(TRIP, search=MockPlaceSearch())
    with_plan = discover_places(
        TRIP, search=MockPlaceSearch(), plan=lambda t, i: {"hiking": ["nature", "park"]}
    )

    assert with_plan.coverage["hiking"] > without.coverage["hiking"]


def test_interest_without_words_is_searched_as_written():
    search = RecordingSearch()

    discover_places(TRIP, search=search, plan=lambda t, i: {"hiking": ["nature"]})

    lattes = next(c for c in search.calls if c.get("query") == "lattes")
    assert lattes["categories"] == ["lattes"]


def test_plan_error_means_searching_the_interests_as_written():
    search = RecordingSearch()

    def broken(trip, interests):
        raise TimeoutError("LLM down")

    result = discover_places(TRIP, search=search, plan=broken)

    assert search.calls[0]["query"] == "hiking"
    assert result.search_words == {}


def test_plan_never_adds_search_calls():
    plan_calls = discover_places(
        TRIP, search=RecordingSearch(), plan=lambda t, i: {"hiking": ["nature"]}
    ).calls_used
    no_plan_calls = discover_places(TRIP, search=RecordingSearch()).calls_used

    assert plan_calls <= no_plan_calls


def test_no_interests_means_no_llm_call():
    def must_not_be_called(trip, interests):
        raise AssertionError("nothing to plan")

    discover_places({"mode": "walking"}, search=MockPlaceSearch(), plan=must_not_be_called)


# --- The LLM answer is checked (discovery_plan.py) ----------------------------


def fake_answer(monkeypatch, items):
    prompts = []

    def fake_ask(prompt, shape):
        prompts.append(prompt)
        return SearchPlan(interests=items)

    monkeypatch.setattr(discovery_plan, "ask_json", fake_ask)
    return prompts


def test_only_allowed_words_and_given_interests_are_kept(monkeypatch):
    fake_answer(
        monkeypatch,
        [
            {"interest": "Hiking", "words": ["Nature", "trails", "park", "viewpoint"]},
            {"interest": "lattes", "words": ["coffee", "coffee"]},
            {"interest": "made up interest", "words": ["museum"]},
        ],
    )

    plan = plan_with_llm(TRIP, ["hiking", "lattes"])

    assert plan == {"hiking": ["nature", "park"], "lattes": ["coffee"]}


def test_words_on_the_avoid_list_are_dropped(monkeypatch):
    fake_answer(monkeypatch, [{"interest": "evenings", "words": ["nightlife", "bar"]}])

    plan = plan_with_llm({"avoid": ["nightlife"]}, ["evenings"])

    assert plan == {"evenings": ["bar"]}


def test_interest_with_no_usable_words_is_left_out(monkeypatch):
    fake_answer(monkeypatch, [{"interest": "hiking", "words": ["mountains"]}])

    assert plan_with_llm(TRIP, ["hiking"]) == {}


def test_prompt_lists_the_allowed_words_and_the_interests(monkeypatch):
    prompts = fake_answer(monkeypatch, [])

    plan_with_llm({**TRIP, "free_text": "we love long walks"}, ["hiking", "lattes"])

    assert all(word in prompts[0] for word in SEARCH_WORDS)
    assert "hiking; lattes" in prompts[0] and "we love long walks" in prompts[0]


def test_no_llm_means_an_empty_plan():
    # The shared test setup removes both keys, so no request is made.
    assert plan_with_llm(TRIP, ["hiking"]) == {}


# --- The Agent trace shows the LLM step ----------------------------------------


def test_trace_shows_the_llm_search_plan():
    def search(trip):
        return [], {"hiking": ["nature", "park"]}

    graph = build_trip_graph(checkpointer=InMemorySaver(), search=search)
    result = graph.invoke(
        {"trip": {"destination": "Seattle", "start_date": "2026-11-12",
                  "end_date": "2026-11-12", "interests": ["hiking"]}},
        {"configurable": {"thread_id": "a2-trace"}},
    )

    plan_events = [e for e in result["logs"] if e["node"] == "search_plan"]
    assert plan_events and plan_events[0]["type"] == "llm"
    assert plan_events[0]["metadata"]["search_words"] == {"hiking": ["nature", "park"]}
