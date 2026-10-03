from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_trip_api_pauses_for_dates_and_resumes():
    response = client.post("/api/trips/plan", json={"destination": "Lisbon", "interests": ["food"]})

    assert response.status_code == 200
    pending = response.json()
    assert pending["status"] == "awaiting_input"
    assert pending["question"]["fields"] == ["start_date", "end_date"]

    resumed = client.post(
        f"/api/trips/{pending['thread_id']}/answer",
        json={"start_date": "2026-11-01", "end_date": "2026-11-05"},
    )

    assert resumed.status_code == 200
    result = resumed.json()
    assert result["status"] == "completed"
    assert len(result["places"]) == 3
    assert [entry["step"] for entry in result["logs"]] == [
        "read",
        "ask_question",
        "answer",
        "find",
        "save",
    ]