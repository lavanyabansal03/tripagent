"""A6 Repair with an LLM: code finds the valid options, the LLM picks one (fake LLMs here)."""

import pytest
from pydantic import BaseModel

from app.agents import llm, repair_choice
from app.agents.planner import build_plan_with_repairs
from app.agents.repair import repair_itinerary
from app.config import MAX_REPAIR_LLM_CALLS, REPAIR_OPTIONS_FOR_LLM, settings

MONDAY_OPEN = [{"day": "monday", "open": "08:00", "close": "21:00"}]
SUNDAY_ONLY = [{"day": "sunday", "open": "08:00", "close": "21:00"}]


def place(place_id, lat=47.610, *, hours=MONDAY_OPEN, kind="culture"):
    return {
        "id": place_id,
        "name": place_id.title(),
        "categories": [kind],
        "experience_types": [kind],
        "lat": lat,
        "lng": -122.330,
        "est_cost_low": 0,
        "est_cost_high": 0,
        "cost_basis": "known",
        "hours": hours,
    }


def closed_plan():
    closed = place("closed", hours=SUNDAY_ONLY)
    activity = {
        "id": "b",
        "trip_id": "trip-1",
        "version": 1,
        "day": 1,
        "place_id": "closed",
        "start": "2026-11-09T10:30:00-08:00",
        "end": "2026-11-09T11:30:00-08:00",
        "est_cost": 0,
        "priority": "medium",
        "purpose_tags": ["culture"],
        "status": "planned",
        "place": closed,
        "backups": [],
    }
    itinerary = {"trip_id": "trip-1", "version": 1, "days": [{"day": 1, "activities": [activity]}]}
    return itinerary, activity


TRIP = {"mode": "walking", "max_travel_min": 60, "interests": ["art"], "avoid": []}
SPARES = [place("near", 47.6101), place("middle", 47.6110), place("far", 47.6130)]


# --- Repair uses the LLM's pick, but only among valid options ---------------


def test_llm_pick_is_used_and_its_reason_recorded():
    itinerary, activity = closed_plan()
    seen = {}

    def choose(trip, act, options, problem):
        seen["names"] = [o["name"] for o in options]
        seen["problem"] = problem
        return 2, "Far fits your love of art best."

    changes = repair_itinerary(TRIP, itinerary, SPARES, choose)

    assert seen["names"] == ["Near", "Middle", "Far"]  # code's order, all valid
    assert seen["problem"] == "It is closed then."
    assert activity["place_id"] == "far"
    assert "Far fits your love of art best." in activity["reason"]
    assert changes[0]["chosen_by"] == "llm"
    assert changes[0]["why"] == "Far fits your love of art best."
    assert changes[0]["options"] == 3


def test_llm_never_sees_an_invalid_option():
    itinerary, _ = closed_plan()
    also_closed = place("also-closed", 47.6102, hours=SUNDAY_ONLY)
    wrong_purpose = place("park", 47.6103, kind="nature")
    seen = {}

    def choose(trip, act, options, problem):
        seen["ids"] = [o["id"] for o in options]
        return 0, "ok"

    repair_itinerary(TRIP, itinerary, [also_closed, wrong_purpose, *SPARES], choose)

    assert "also-closed" not in seen["ids"] and "park" not in seen["ids"]


@pytest.mark.parametrize("answer", [None, (7, "made up"), (-1, "bad"), ("1", "not a number")])
def test_bad_or_missing_llm_answer_falls_back_to_codes_first_choice(answer):
    itinerary, activity = closed_plan()

    changes = repair_itinerary(TRIP, itinerary, SPARES, lambda *a: answer)

    assert activity["place_id"] == "near"
    assert changes[0]["chosen_by"] == "rule-fallback"
    assert changes[0]["why"] is None


def test_llm_error_falls_back_too():
    itinerary, activity = closed_plan()

    def broken(*_args):
        raise TimeoutError("LLM down")

    repair_itinerary(TRIP, itinerary, SPARES, broken)

    assert activity["place_id"] == "near"


def test_llm_is_not_asked_when_there_is_only_one_option():
    itinerary, activity = closed_plan()

    def must_not_be_called(*_args):
        raise AssertionError("no choice to make")

    changes = repair_itinerary(TRIP, itinerary, SPARES[:1], must_not_be_called)

    assert activity["place_id"] == "near"
    assert changes[0]["chosen_by"] == "rule"


def test_options_are_capped():
    itinerary, _ = closed_plan()
    many = [place(f"spare-{i}", 47.6101 + i * 0.0001) for i in range(10)]
    seen = {}

    def choose(trip, act, options, problem):
        seen["count"] = len(options)
        return 0, "ok"

    repair_itinerary(TRIP, itinerary, many, choose)

    assert seen["count"] == REPAIR_OPTIONS_FOR_LLM


def test_llm_choices_per_plan_are_limited():
    calls = []

    def choose(trip, act, options, problem):
        calls.append(1)
        return 0, "ok"

    trip = {
        "trip_id": "trip-1", "destination": "Seattle", "start_date": "2026-11-09",
        "end_date": "2026-11-10", "mode": "walking", "max_travel_min": 180,
        "daily_start": "09:00", "daily_end": "20:00", "budget": None, "avoid": [],
    }
    closed = [place(f"closed-{i}", 47.61 + i * 0.0002, hours=SUNDAY_ONLY) for i in range(6)]
    spares = [place(f"spare-{i}", 47.61 + i * 0.0002 + 0.0001) for i in range(12)]

    build_plan_with_repairs(trip, closed + spares, choose=choose)

    assert len(calls) <= MAX_REPAIR_LLM_CALLS


# --- The LLM chooser itself (repair_choice.py) ------------------------------


def test_choose_with_llm_turns_a_1_based_answer_into_an_index(monkeypatch):
    prompts = []

    def fake_ask(prompt, shape):
        prompts.append(prompt)
        return shape(choice=2, reason="Middle has listed opening hours.")

    monkeypatch.setattr(repair_choice, "ask_json", fake_ask)
    _, activity = closed_plan()

    result = repair_choice.choose_with_llm(TRIP, activity, SPARES, "It is closed then.")

    assert result == (1, "Middle has listed opening hours.")
    assert "1. Near" in prompts[0] and "3. Far" in prompts[0]
    assert "do not invent" in prompts[0]
    assert "art" in prompts[0]  # the traveller's interests are given


@pytest.mark.parametrize("choice", [0, 4, 99])
def test_choose_with_llm_rejects_options_that_do_not_exist(monkeypatch, choice):
    def fake_ask(_prompt, shape):
        return shape(choice=choice, reason="x")

    monkeypatch.setattr(repair_choice, "ask_json", fake_ask)
    _, activity = closed_plan()

    assert repair_choice.choose_with_llm(TRIP, activity, SPARES, "closed") is None


def test_choose_with_llm_returns_none_without_any_llm():
    # The shared test setup removes both keys, so no real request is made.
    _, activity = closed_plan()

    assert repair_choice.choose_with_llm(TRIP, activity, SPARES, "closed") is None


# --- The shared helper (llm.py) ----------------------------------------------


class Answer(BaseModel):
    word: str


def use_providers(monkeypatch, gemini, nvidia):
    log = []

    def make(name, outcome):
        def provider(prompt, shape):
            log.append(name)
            if isinstance(outcome, Exception):
                raise outcome
            return outcome

        return provider

    providers = {"gemini": make("gemini", gemini), "nvidia": make("nvidia", nvidia)}
    monkeypatch.setattr(llm, "PROVIDERS", providers)
    return log


def test_ask_json_uses_the_primary_llm_first(monkeypatch):
    log = use_providers(monkeypatch, Answer(word="g"), Answer(word="n"))

    assert llm.ask_json("q", Answer).word == "g"
    assert log == ["gemini"]


def test_ask_json_falls_back_to_the_other_llm(monkeypatch):
    log = use_providers(monkeypatch, RuntimeError("504"), Answer(word="n"))

    assert llm.ask_json("q", Answer).word == "n"
    assert log == ["gemini", "nvidia"]


def test_ask_json_respects_llm_primary(monkeypatch):
    monkeypatch.setattr(settings, "LLM_PRIMARY", "nvidia")
    log = use_providers(monkeypatch, Answer(word="g"), Answer(word="n"))

    assert llm.ask_json("q", Answer).word == "n"
    assert log == ["nvidia"]


def test_ask_json_gives_none_when_both_fail(monkeypatch):
    use_providers(monkeypatch, RuntimeError("down"), ValueError("bad json"))

    assert llm.ask_json("q", Answer) is None


def test_ask_json_makes_no_request_without_keys():
    assert llm.ask_json("q", Answer) is None
