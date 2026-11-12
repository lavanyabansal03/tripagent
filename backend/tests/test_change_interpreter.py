"""A5 Change Interpreter (fake LLMs; no network)."""

import pytest

from app.agents import change_interpreter as a5
from app.agents.change_interpreter import ChangeShape, interpret, rule_based


def place(name, kind):
    return {"id": f"p-{name}", "name": name, "categories": [kind], "experience_types": [kind]}


def activity(activity_id, name, kind, start, status="planned"):
    return {
        "id": activity_id, "day": 1, "status": status, "purpose_tags": [kind],
        "start": f"2026-11-20T{start}:00-08:00", "end": f"2026-11-20T{start[:2]}:59:00-08:00",
        "place": place(name, kind),
    }


ITINERARY = {"days": [{"day": 1, "activities": [
    activity("a1", "Storyville Coffee", "cafe", "09:00"),
    activity("a2", "Frye Art Museum", "museum", "11:00"),
    activity("a3", "Olympic Sculpture Park", "park", "14:00"),
]}]}
REQS = {"budget": 500, "mode": "transit"}


def run(text=None, typed=None, day=1):
    return interpret(text=text, typed=typed, itinerary=ITINERARY, requirements=REQS, day=day)


def fake_llm(monkeypatch, shape):
    prompts = []

    def ask(prompt, cls):
        prompts.append(prompt)
        return shape

    monkeypatch.setattr(a5, "ask_json", ask)
    return prompts


# --- LLM path: proposal checked by code -------------------------------------------


def test_llm_late_is_accepted(monkeypatch):
    prompts = fake_llm(monkeypatch, ChangeShape(type="time", minutes=90, trigger="running late"))

    result = run("we're running about an hour and a half behind")

    assert (result.status, result.type, result.source) == ("ok", "time", "llm")
    assert result.payload == {"minutes": 90, "day": 1}
    assert "id a2 | Frye Art Museum" in prompts[0]  # the LLM sees the real stops and ids


def test_llm_closure_must_name_a_real_stop(monkeypatch):
    fake_llm(monkeypatch, ChangeShape(type="closure", activity_id="made-up"))

    result = run("the museum is closed today")

    # The LLM's id is invalid; the words name the one museum, so code uses that id.
    assert (result.status, result.type, result.source) == ("ok", "closure", "llm")
    assert result.payload["activity_id"] == "a2"


def test_llm_question_is_passed_on_when_unsure(monkeypatch):
    fake_llm(monkeypatch, ChangeShape(type="unknown", question="Which day do you mean?"))

    result = run("something happened")

    assert result.status == "needs_clarification"
    assert result.question == "Which day do you mean?"


@pytest.mark.parametrize(
    "shape",
    [
        ChangeShape(type="time", minutes=0),
        ChangeShape(type="time", minutes=10_000),
        ChangeShape(type="budget", budget=-5),
        ChangeShape(type="preference", avoid=["  "]),
    ],
)
def test_out_of_range_llm_answers_are_not_used(monkeypatch, shape):
    fake_llm(monkeypatch, shape)

    assert run("hmm").status == "needs_clarification"


# --- word rules when no LLM answers ---------------------------------------------


@pytest.mark.parametrize(
    "text, expected",
    [
        ("I'm running 90 minutes late", ("time", {"minutes": 90, "day": 1})),
        ("we are 2 hours behind", ("time", {"minutes": 120, "day": 1})),
        ("running an hour late", ("time", {"minutes": 60, "day": 1})),
        ("my budget is now $300", ("budget", {"budget": 300.0})),
        ("let's walk everywhere", ("transport", {"mode": "walking"})),
        ("we'll take the bus", ("transport", {"mode": "transit"})),
        ("skip museums", ("preference", {"avoid": ["museums"]})),
        ("the park is closed", ("closure", {"activity_id": "a3", "day": 1})),
        ("Storyville is shut today", ("closure", {"activity_id": "a1", "day": 1})),
    ],
)
def test_rules_without_an_llm(text, expected):
    # The shared test setup removes both LLM keys, so ask_json returns None.
    result = run(text)

    assert result.status == "ok", result.question
    assert (result.type, result.payload) == expected
    assert result.source == "rules"


def test_closure_with_two_matches_asks_which():
    itinerary = {"days": [{"day": 1, "activities": [
        activity("m1", "Frye Art Museum", "museum", "10:00"),
        activity("m2", "Seattle Art Museum", "museum", "13:00"),
    ]}]}

    result = interpret(text="the museum is closed", typed=None, itinerary=itinerary,
                       requirements=REQS, day=1)

    assert result.status == "needs_clarification"
    assert result.question == "Which place is closed: Frye Art Museum or Seattle Art Museum?"


def test_closure_of_a_locked_stop_asks_first():
    itinerary = {"days": [{"day": 1, "activities": [
        activity("a2", "Frye Art Museum", "museum", "11:00", status="locked"),
    ]}]}

    result = interpret(text="the museum is closed", typed=None, itinerary=itinerary,
                       requirements=REQS, day=1)

    assert result.status == "needs_clarification"


def test_rule_based_unknown_text():
    assert rule_based("hello there", ITINERARY, 1).type == "unknown"


def test_unclear_text_gets_the_generic_question():
    result = run("blah")

    assert result.status == "needs_clarification"
    assert "We didn't catch what changed" in result.question


# --- quick buttons (typed) skip the LLM --------------------------------------------


def test_typed_change_does_not_call_the_llm(monkeypatch):
    def must_not_run(*_args):
        raise AssertionError("typed changes skip the LLM")

    monkeypatch.setattr(a5, "ask_json", must_not_run)

    late = run(typed={"type": "time", "payload": {"minutes": 90}})
    budget = run(typed={"type": "budget", "payload": {"budget": 300}})
    walk = run(typed={"type": "transport", "payload": {"mode": "walking"}})
    skip = run(typed={"type": "preference", "payload": {"avoid": ["shopping"]}})

    assert [r.type for r in (late, budget, walk, skip)] == [
        "time", "budget", "transport", "preference",
    ]
    assert all(r.status == "ok" and r.source == "typed" for r in (late, budget, walk, skip))


def test_adding_stops_on_the_way_is_not_supported_yet():
    typed = {"type": "preference", "payload": {"interests": ["coffee"], "along_route": True}}

    for result in (run(typed=typed), run("add a coffee stop on the way")):
        assert result.status == "needs_clarification"
        assert result.question == "Adding new stops on the way isn't supported yet."


def test_late_uses_the_day_on_screen():
    assert run("90 minutes late", day=2).payload["day"] == 2


def test_named_stop_beats_a_wrong_llm_pick(monkeypatch):
    # Seen live: "Starbucks is closed" and the LLM returned Monorail Espresso's id.
    itinerary = {"days": [{"day": 1, "activities": [
        activity("s", "Starbucks", "cafe", "10:00"),
        activity("m", "Monorail Espresso", "cafe", "12:00"),
    ]}]}
    fake_llm(monkeypatch, ChangeShape(type="closure", activity_id="m"))

    result = interpret(text="Starbucks is closed today", typed=None, itinerary=itinerary,
                       requirements=REQS, day=1)

    assert result.status == "ok" and result.payload["activity_id"] == "s"
