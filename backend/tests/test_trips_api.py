from fastapi.testclient import TestClient

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

    trace = client.get(f"/api/trips/{trip_id}/trace")
    assert trace.status_code == 200
    events = trace.json()
    assert [event["node"] for event in events] == ["read", "find", "save"]
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
    assert "date questions" in response.json()["detail"]


def test_unknown_trip_and_run_return_404():
    assert client.get("/api/trips/not-a-trip").status_code == 404
    assert client.get("/api/runs/not-a-run").status_code == 404
