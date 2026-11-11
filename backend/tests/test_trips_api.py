from fastapi.testclient import TestClient

from app.agents.preferences import Preferences
from app.api import trips as trips_api
from app.main import app

client = TestClient(app)


def test_trip_create_clarify_plan_and_trace_follow_svelte_contract():
    created = client.post(
        "/api/trips",
        json={
            "destination": "Lisbon",
            "interests": ["food"],
            "free_text": "A relaxed trip",
        },
    )

    assert created.status_code == 201
    payload = created.json()
    trip_id = payload["trip"]["id"]
    assert payload["trip"]["destination"] == "Lisbon"
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

    trace = client.get(f"/api/trips/{trip_id}/trace")
    assert trace.status_code == 200
    events = trace.json()
    assert [event["node"] for event in events] == [
        "read", "find", "planner", "validator", "save"
    ]
    assert next(event for event in events if event["node"] == "validator")["type"] == "validation"
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
        "extract_preferences",
        lambda _text: Preferences(
            interests=["coffee", "art"],
            avoid=["nightclubs", "bars"],
            budget_min=50,
            budget_max=200,
            budget_level="moderate",
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
            "budget_min": 100,
            "budget_max": 250,
            "budget_level": "expensive",
            "free_text": "We love coffee and galleries.",
        },
    )

    assert response.status_code == 201
    requirements = response.json()["requirements"]
    assert requirements["interests"] == ["art", "museums", "coffee"]
    assert requirements["avoid"] == ["bars", "nightclubs"]
    assert requirements["max_travel_min"] == 25
    assert requirements["budget_min"] == 100
    assert requirements["budget_max"] == 250
    assert requirements["budget_level"] == "expensive"


def test_create_trip_uses_extracted_preferences_when_form_values_are_omitted(monkeypatch):
    monkeypatch.setattr(
        trips_api,
        "extract_preferences",
        lambda _text: Preferences(
            interests=["coffee"],
            avoid=["crowds"],
            budget_min=40,
            budget_max=120,
            budget_level="cheap",
            max_travel_min=18,
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
    assert requirements["budget_min"] == 40
    assert requirements["budget_max"] == 120
    assert requirements["budget_level"] == "cheap"
    assert requirements["provenance"]["interests"] == "inferred"
    assert requirements["provenance"]["avoid"] == "inferred"
    assert requirements["provenance"]["max_travel_min"] == "inferred"
    assert requirements["provenance"]["budget_min"] == "inferred"
    assert requirements["provenance"]["budget_max"] == "inferred"
    assert requirements["provenance"]["budget_level"] == "inferred"


def test_create_trip_continues_when_preference_extraction_returns_none(monkeypatch):
    monkeypatch.setattr(trips_api, "extract_preferences", lambda _text: None)
    response = client.post(
        "/api/trips",
        json={
            "destination": "Seattle",
            "interests": ["parks"],
            "budget_max": 300,
            "free_text": "A relaxed trip.",
        },
    )

    assert response.status_code == 201
    requirements = response.json()["requirements"]
    assert requirements["interests"] == ["parks"]
    assert requirements["budget_max"] == 300
    assert requirements["max_travel_min"] == 30


def test_create_trip_continues_when_preference_extraction_fails(monkeypatch):
    def fail_extraction(_text):
        raise ValueError("GOOGLE_API_KEY is not set.")

    monkeypatch.setattr(trips_api, "extract_preferences", fail_extraction)
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
