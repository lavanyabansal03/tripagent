"""Changes during the trip through the API (demo Seattle data, no LLM keys, test DB)."""

import pytest
from fastapi.testclient import TestClient

from app.api import changes
from app.main import app

client = TestClient(app)


def planned_trip():
    trip_id = client.post("/api/trips", json={
        "destination": "Seattle", "start_date": "2026-11-12", "end_date": "2026-11-12",
        "interests": ["coffee", "museums"], "mode": "walking",
    }).json()["trip"]["id"]
    client.post(f"/api/trips/{trip_id}/plan")
    return trip_id


def current(trip_id):
    return client.get(f"/api/trips/{trip_id}/itinerary").json()


def activities(itinerary):
    return [a for day in itinerary["days"] for a in day["activities"]]


def change(trip_id, **body):
    response = client.post(f"/api/trips/{trip_id}/changes", json={"day": 1, **body})
    assert response.status_code == 200, response.text
    return response.json()


def run_of(result):
    return client.get(f"/api/runs/{result['run_id']}").json()


# --- each change type -------------------------------------------------------------


def test_running_late_moves_the_day_and_saves_version_2():
    trip_id = planned_trip()
    before = current(trip_id)

    result = change(trip_id, text="I'm running 30 minutes late")
    after = current(trip_id)

    assert run_of(result)["status"] == "done" and run_of(result)["phase"] == "adapt"
    assert result["change"]["type"] == "time" and result["change"]["status"] == "applied"
    assert after["version"] == 2
    assert client.get(f"/api/trips/{trip_id}/versions").json() == [1, 2]
    first_before, first_after = activities(before)[0], activities(after)[0]
    assert first_after["id"] == first_before["id"]
    assert first_after["start"] != first_before["start"]
    replans = client.get(f"/api/trips/{trip_id}/replans").json()
    assert len(replans) == 1
    assert replans[0]["from_version"] == 1 and replans[0]["to_version"] == 2
    assert replans[0]["trigger_text"] == "you're running 30 minutes late"
    assert set(replans[0]["diff"]["moved"]) == {a["id"] for a in activities(before)}


def test_quick_buttons_budget_walking_and_skip():
    trip_id = planned_trip()

    budget = change(trip_id, typed={"type": "budget", "payload": {"budget": 300}})
    walk = change(trip_id, typed={"type": "transport", "payload": {"mode": "walking"}})
    skip = change(trip_id, typed={"type": "preference", "payload": {"avoid": ["starbucks"]}})

    requirements = client.get(f"/api/trips/{trip_id}/requirements").json()
    assert requirements["budget"] == 300 and requirements["mode"] == "walking"
    assert "starbucks" in requirements["avoid"]
    assert all(run_of(r)["status"] in ("done", "infeasible") for r in (budget, walk, skip))
    names = [a["place"]["name"].lower() for a in activities(current(trip_id))]
    assert not any("starbucks" in n for n in names)  # avoid-list repair ran
    assert client.get(f"/api/trips/{trip_id}/versions").json() == [1, 2, 3, 4]


def test_closed_place_is_replaced_or_removed_and_explained():
    trip_id = planned_trip()
    closed = activities(current(trip_id))[0]

    result = change(trip_id, typed={"type": "closure", "payload": {"activity_id": closed["id"]}})

    replan = client.get(f"/api/trips/{trip_id}/replans").json()[-1]
    touched = replan["diff"]["changed"] + replan["diff"]["removed"]
    assert closed["id"] in touched
    assert replan["reasons"][closed["id"]]
    assert run_of(result)["status"] in ("done", "infeasible")
    after = {a["id"]: a for a in activities(current(trip_id))}
    if closed["id"] in after:
        assert after[closed["id"]]["place_id"] != closed["place_id"]


def test_swap_to_a_stored_backup():
    trip_id = planned_trip()
    target = next(a for a in activities(current(trip_id)) if a.get("backups"))
    backup = target["backups"][0]

    response = client.post(
        f"/api/trips/{trip_id}/activities/{target['id']}/swap",
        json={"backup_id": backup["place_id"]},
    )

    assert response.status_code == 200
    swapped = next(a for a in activities(current(trip_id)) if a["id"] == target["id"])
    assert swapped["place_id"] == backup["place_id"]


def test_undo_returns_to_the_previous_version_and_keeps_all_versions():
    trip_id = planned_trip()
    first = current(trip_id)
    change(trip_id, text="running 30 minutes late")

    restored = client.post(f"/api/trips/{trip_id}/versions/1/restore")

    assert restored.json() == {"version": 1}
    assert current(trip_id) == first
    assert client.get(f"/api/trips/{trip_id}").json()["current_version"] == 1
    assert client.get(f"/api/trips/{trip_id}/versions").json() == [1, 2]

    change(trip_id, typed={"type": "budget", "payload": {"budget": 100}})
    assert current(trip_id)["version"] == 3  # a change after Undo gets the next number


def test_simulate_closure_and_delay():
    trip_id = planned_trip()

    for kind in ("closure", "delay"):
        response = client.post(f"/api/trips/{trip_id}/simulate", json={"type": kind})
        assert response.status_code == 200
        assert client.get(f"/api/runs/{response.json()['run_id']}").json()["phase"] == "adapt"

    assert len(client.get(f"/api/trips/{trip_id}/replans").json()) == 2


def test_trace_shows_the_change_steps():
    trip_id = planned_trip()

    change(trip_id, text="I'm running 30 minutes late")

    nodes = [e["node"] for e in client.get(f"/api/trips/{trip_id}/trace").json()]
    tail = nodes[nodes.index("interpret"):]
    assert tail[:2] == ["interpret", "apply"]
    assert "explain" in tail and tail[-1] == "save"


# --- A5 asks instead of guessing ------------------------------------------------------


def test_unclear_change_returns_a5s_question_and_changes_nothing():
    trip_id = planned_trip()

    result = change(trip_id, text="hmm something")

    assert result["run_id"] == ""
    assert result["change"]["status"] == "needs-clarification"
    assert "We didn't catch what changed" in result["change"]["payload"]["question"]
    assert client.get(f"/api/trips/{trip_id}/versions").json() == [1]


def test_adding_a_stop_on_the_way_is_not_supported_yet():
    trip_id = planned_trip()
    typed = {"type": "preference", "payload": {"interests": ["coffee"], "along_route": True}}

    result = change(trip_id, typed=typed)

    assert result["change"]["payload"]["question"] == (
        "Adding new stops on the way isn't supported yet."
    )


# --- errors ------------------------------------------------------------------------------


def test_second_change_while_one_runs_gets_409():
    trip_id = planned_trip()
    lock = changes._lock_for(trip_id)
    lock.acquire()
    try:
        response = client.post(
            f"/api/trips/{trip_id}/changes",
            json={"typed": {"type": "budget", "payload": {"budget": 1}}},
        )
    finally:
        lock.release()

    assert response.status_code == 409


@pytest.mark.parametrize(
    "path, body",
    [
        ("/activities/nope/swap", {"backup_id": "x"}),
        ("/versions/99/restore", None),
    ],
)
def test_unknown_activity_or_version_is_404(path, body):
    trip_id = planned_trip()

    response = client.post(f"/api/trips/{trip_id}{path}", json=body)

    assert response.status_code == 404


def test_unknown_backup_is_404():
    trip_id = planned_trip()
    target = activities(current(trip_id))[0]

    response = client.post(
        f"/api/trips/{trip_id}/activities/{target['id']}/swap", json={"backup_id": "not-stored"}
    )

    assert response.status_code == 404


def test_change_before_planning_is_409():
    trip_id = client.post("/api/trips", json={
        "destination": "Seattle", "start_date": "2026-11-12", "end_date": "2026-11-12",
    }).json()["trip"]["id"]

    response = client.post(f"/api/trips/{trip_id}/changes", json={"text": "late 30 minutes"})

    assert response.status_code == 409


def test_simulating_weather_is_not_supported():
    trip_id = planned_trip()

    assert client.post(f"/api/trips/{trip_id}/simulate", json={"type": "rain"}).status_code == 422
