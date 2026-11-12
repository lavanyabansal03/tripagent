from fastapi.testclient import TestClient

from app.agents.preferences import Preferences
from app.api import trips as trips_api
from app.main import app

client = TestClient(app)


def test_trip_create_clarify_plan_and_trace_follow_svelte_contract():
    created = client.post(
        "/api/trips",
        json={
            "destination": "Seattle",
            "interests": ["food"],
            "free_text": "A relaxed trip",
        },
    )

    assert created.status_code == 201
    payload = created.json()
    trip_id = payload["trip"]["id"]
    assert payload["trip"]["destination"] == "Seattle"
    assert payload["requirements"]["interests"] == ["food"]
    assert [
        (question["id"], question["field"]) for question in payload["questions"]
    ] == [("start_date", "start_date"), ("end_date", "end_date")]

    answered = client.post(
        f"/api/trips/{trip_id}/answers",
        json={"answers": {"start_date": "2026-11-01", "end_date": "2026-11-05"}},
    )
    assert answered.status_code == 200
    assert answered.json()["start_date"] == "2026-11-01"
    assert answered.json()["end_date"] == "2026-11-05"

    planned = client.post(f"/api/trips/{trip_id}/plan")
    assert planned.status_code == 200
    run_id = planned.json()["run_id"]

    run = client.get(f"/api/runs/{run_id}")
    assert run.status_code == 200
    assert run.json()["trip_id"] == trip_id
    assert run.json()["status"] == "done"
    assert run.json()["terminal"] == "PASS"

    itinerary = client.get(f"/api/trips/{trip_id}/itinerary")
    assert itinerary.status_code == 200
    assert len(itinerary.json()["days"]) == 5
    assert itinerary.json()["days"][0]["activities"]
    # Every day with 2+ stops has a travel leg between each pair (the app draws routes).
    for day in itinerary.json()["days"]:
        assert len(day["legs"]) == max(0, len(day["activities"]) - 1)

    trace = client.get(f"/api/trips/{trip_id}/trace")
    assert trace.status_code == 200
    events = trace.json()
    assert [event["node"] for event in events] == [
        "read", "find", "planner", "backup", "routes", "validator", "save"
    ]
    assert next(event for event in events if event["node"] == "validator")["type"] == "validation"
    assert next(event for event in events if event["node"] == "backup")["type"] == "tool"
    assert all(
        {"node", "type", "iteration", "status", "duration_ms"} <= event.keys()
        for event in events
    )
    assert all(event["trip_id"] == trip_id and event["run_id"] == run_id for event in events)


def test_plan_requires_answers_to_missing_date_questions():
    created = client.post("/api/trips", json={"destination": "Oslo"})
    trip_id = created.json()["trip"]["id"]

    response = client.post(f"/api/trips/{trip_id}/plan")

    assert response.status_code == 409
    assert "Trip dates are required" in response.json()["detail"]


def test_trip_rejects_end_date_before_start_date():
    response = client.post(
        "/api/trips",
        json={
            "destination": "Oslo",
            "start_date": "2026-11-05",
            "end_date": "2026-11-01",
        },
    )
    assert response.status_code == 422
    assert "End date cannot be before start date" in response.text


def test_date_clarification_stops_after_two_rounds():
    created = client.post("/api/trips", json={"destination": "Oslo"})
    trip_id = created.json()["trip"]["id"]

    first_answer = client.post(f"/api/trips/{trip_id}/answers", json={"answers": {}})
    assert first_answer.status_code == 200
    second_answer = client.post(f"/api/trips/{trip_id}/answers", json={"answers": {}})
    assert second_answer.status_code == 200

    planning = client.post(f"/api/trips/{trip_id}/plan")
    assert planning.status_code == 409
    assert "two-round" in planning.json()["detail"]

    third_answer = client.post(f"/api/trips/{trip_id}/answers", json={"answers": {}})
    assert third_answer.status_code == 409


def test_answer_rejects_reversed_trip_dates():
    created = client.post("/api/trips", json={"destination": "Oslo"})
    trip_id = created.json()["trip"]["id"]
    response = client.post(
        f"/api/trips/{trip_id}/answers",
        json={"answers": {"start_date": "2026-11-05", "end_date": "2026-11-01"}},
    )
    assert response.status_code == 422
    assert "End date cannot be before start date" in response.json()["detail"]


def test_unknown_trip_and_run_return_404():
    assert client.get("/api/trips/not-a-trip").status_code == 404
    assert client.get("/api/runs/not-a-run").status_code == 404


def test_create_trip_merges_extracted_preferences_without_overwriting_form_values(
    monkeypatch,
):
    monkeypatch.setattr(
        trips_api,
        "read_preferences",
        lambda _text: Preferences(
            interests=["coffee", "art"],
            avoid=["nightclubs", "bars"],
            max_travel_min=20,
        ),
    )

    response = client.post(
        "/api/trips",
        json={
            "destination": "Seattle",
            "interests": ["art", "museums"],
            "avoid": ["bars"],
            "max_travel_min": 25,
            "budget": 150,
            "free_text": "We love coffee and galleries.",
        },
    )

    assert response.status_code == 201
    requirements = response.json()["requirements"]
    assert requirements["interests"] == ["art", "museums", "coffee"]
    assert requirements["avoid"] == ["bars", "nightclubs"]
    assert requirements["max_travel_min"] == 25
    assert requirements["budget"] == 150


def test_create_trip_uses_extracted_preferences_when_form_values_are_omitted(monkeypatch):
    monkeypatch.setattr(
        trips_api,
        "read_preferences",
        lambda _text: Preferences(
            interests=["coffee"], avoid=["crowds"], max_travel_min=18
        ),
    )

    response = client.post(
        "/api/trips",
        json={"destination": "Seattle", "free_text": "Coffee, avoid crowds, short travel."},
    )

    assert response.status_code == 201
    requirements = response.json()["requirements"]
    assert requirements["interests"] == ["coffee"]
    assert requirements["avoid"] == ["crowds"]
    assert requirements["max_travel_min"] == 18
    assert requirements["provenance"]["interests"] == "inferred"
    assert requirements["provenance"]["avoid"] == "inferred"
    assert requirements["provenance"]["max_travel_min"] == "inferred"


def test_create_trip_continues_when_preference_extraction_fails(monkeypatch):
    def fail_extraction(_text):
        raise ValueError("GOOGLE_API_KEY is not set.")

    monkeypatch.setattr(trips_api, "read_preferences", fail_extraction)
    response = client.post(
        "/api/trips",
        json={
            "destination": "Seattle",
            "interests": ["parks"],
            "free_text": "A relaxed trip.",
        },
    )

    assert response.status_code == 201
    assert response.json()["requirements"]["interests"] == ["parks"]


# The Svelte form always sends every field, including defaults the traveller
# never changed, and lists the fields they did change in `touched`.
FORM_DEFAULTS = {
    "destination": "Seattle",
    "start_date": "2026-11-10",
    "end_date": "2026-11-11",
    "budget": 500,
    "budget_strictness": "strict",
    "mode": "transit",
    "pace": "moderate",
    "max_travel_min": 30,
    "interests": [],
    "avoid": [],
    "tourist_local_ratio": 50,
}


def fake_extraction(monkeypatch, **fields):
    monkeypatch.setattr(
        trips_api, "read_preferences", lambda _text: Preferences(**fields)
    )


def test_note_replaces_form_defaults_the_traveller_never_touched(monkeypatch):
    fake_extraction(
        monkeypatch, interests=["museums"], budget_max=300, max_travel_min=20
    )

    response = client.post(
        "/api/trips",
        json={
            **FORM_DEFAULTS,
            "free_text": "Museums, under $300, no more than 20 minutes between stops.",
            "touched": ["destination"],
        },
    )

    assert response.status_code == 201
    requirements = response.json()["requirements"]
    assert requirements["max_travel_min"] == 20
    assert requirements["budget"] == 300
    assert requirements["interests"] == ["museums"]
    provenance = requirements["provenance"]
    assert provenance["max_travel_min"] == "inferred"
    assert provenance["budget"] == "inferred"
    assert provenance["interests"] == "inferred"


def test_note_never_overrides_a_value_the_traveller_set_in_the_form(monkeypatch):
    fake_extraction(monkeypatch, budget_max=300, max_travel_min=20)

    response = client.post(
        "/api/trips",
        json={
            **FORM_DEFAULTS,
            "budget": 450,
            "max_travel_min": 45,
            "free_text": "Under $300, max 20 minutes of travel.",
            "touched": ["destination", "budget", "max_travel_min"],
        },
    )

    requirements = response.json()["requirements"]
    assert requirements["budget"] == 450
    assert requirements["max_travel_min"] == 45
    assert requirements["provenance"]["budget"] == "explicit"
    assert requirements["provenance"]["max_travel_min"] == "explicit"


def test_untouched_form_fields_are_labelled_default():
    response = client.post(
        "/api/trips",
        json={**FORM_DEFAULTS, "mode": "walking", "touched": ["destination", "mode"]},
    )

    provenance = response.json()["requirements"]["provenance"]
    assert provenance["mode"] == "explicit"
    assert provenance["pace"] == "default"
    assert provenance["budget"] == "default"
    assert provenance["max_travel_min"] == "default"
    assert provenance["tourist_local_ratio"] == "default"


def test_trip_is_created_from_the_form_when_there_is_no_api_key():
    # The shared test setup removes the key, so the real agent returns None.
    response = client.post(
        "/api/trips",
        json={
            **FORM_DEFAULTS,
            "interests": ["parks"],
            "free_text": "Museums, max 20 minutes.",
            "touched": ["interests"],
        },
    )

    assert response.status_code == 201
    requirements = response.json()["requirements"]
    assert requirements["interests"] == ["parks"]
    assert requirements["max_travel_min"] == 30


def test_same_interest_in_form_and_note_is_kept_once(monkeypatch):
    fake_extraction(monkeypatch, interests=["coffee", "Museums"])

    response = client.post(
        "/api/trips",
        json={
            **FORM_DEFAULTS,
            "interests": ["Coffee", "museums"],
            "free_text": "Coffee and museums.",
            "touched": ["interests"],
        },
    )

    assert response.json()["requirements"]["interests"] == ["Coffee", "museums"]


def test_note_cannot_set_a_travel_limit_below_one_minute(monkeypatch):
    fake_extraction(monkeypatch, max_travel_min=0)

    response = client.post(
        "/api/trips",
        json={**FORM_DEFAULTS, "free_text": "No travel.", "touched": []},
    )

    assert response.json()["requirements"]["max_travel_min"] == 30


def test_unknown_touched_field_is_rejected():
    response = client.post(
        "/api/trips", json={**FORM_DEFAULTS, "touched": ["not_a_field"]}
    )

    assert response.status_code == 422


def test_each_interest_and_avoid_item_says_where_it_came_from(monkeypatch):
    fake_extraction(monkeypatch, interests=["museums", "Coffee"], avoid=["nightclubs"])

    response = client.post(
        "/api/trips",
        json={
            **FORM_DEFAULTS,
            "interests": ["coffee"],
            "free_text": "Museums and coffee, no nightclubs.",
            "touched": ["interests"],
        },
    )

    provenance = response.json()["requirements"]["provenance"]
    assert provenance["interests.coffee"] == "explicit"  # picked in the form
    assert provenance["interests.museums"] == "inferred"  # only in the note
    assert provenance["avoid.nightclubs"] == "inferred"


def test_untouched_form_default_interest_is_labelled_default_or_from_note(monkeypatch):
    fake_extraction(monkeypatch, interests=["museums", "coffee"])

    response = client.post(
        "/api/trips",
        json={
            **FORM_DEFAULTS,
            "interests": ["coffee", "parks"],  # the form's pre-selected chips
            "free_text": "Museums and good coffee.",
            "touched": ["destination"],  # the traveller never touched the interests
        },
    )

    provenance = response.json()["requirements"]["provenance"]
    assert provenance["interests.coffee"] == "inferred"  # also in the note
    assert provenance["interests.parks"] == "default"  # only a form default
    assert provenance["interests.museums"] == "inferred"
