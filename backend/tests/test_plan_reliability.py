"""Planning must survive what a live demo throws at it.

Each test was a real bug found in a full-app probe (2026-11-12):
- a failed plan could never be retried (the same failed run came back forever);
- a crash inside planning left the trip stuck in "planning" with a 500;
- two "Build my plan" clicks planned twice and the second crashed (version 1 twice);
- graph state (retry counters) leaked from one run into the next of the same trip;
- a date with a time part was accepted, then crashed planning.
"""

import threading
import time

import pytest
from fastapi.testclient import TestClient

from app.api import trips as trips_api
from app.main import app

client = TestClient(app)

TRIP = {
    "destination": "Seattle",
    "start_date": "2026-12-01",
    "end_date": "2026-12-01",
    "interests": ["coffee"],
}


def new_trip() -> str:
    response = client.post("/api/trips", json=TRIP)
    assert response.status_code == 201
    return response.json()["trip"]["id"]


# --- a failed plan can be tried again ---------------------------------------------------


def test_try_again_after_a_failed_plan_plans_again(monkeypatch):
    trip_id = new_trip()
    real_invoke = trips_api.trip_graph.invoke
    monkeypatch.setattr(
        trips_api.trip_graph,
        "invoke",
        lambda *a, **k: {"status": "failed", "explanation": "Place search failed", "logs": []},
    )
    failed_run = client.post(f"/api/trips/{trip_id}/plan").json()["run_id"]
    assert client.get(f"/api/runs/{failed_run}").json()["status"] == "failed"

    monkeypatch.setattr(trips_api.trip_graph, "invoke", real_invoke)  # the provider is back
    retry = client.post(f"/api/trips/{trip_id}/plan").json()["run_id"]

    assert retry != failed_run
    assert client.get(f"/api/runs/{retry}").json()["status"] == "done"
    assert client.get(f"/api/trips/{trip_id}/itinerary").json()["version"] == 1
    assert client.get(f"/api/trips/{trip_id}").json()["status"] == "planned"


# --- a crash ends in ERROR, not stuck in "planning" -------------------------------------


def test_a_crash_while_planning_ends_as_a_failed_run(monkeypatch):
    trip_id = new_trip()

    def crash(*args, **kwargs):
        raise RuntimeError("planner crashed")

    monkeypatch.setattr(trips_api.trip_graph, "invoke", crash)
    response = client.post(f"/api/trips/{trip_id}/plan")

    assert response.status_code == 200
    run = client.get(f"/api/runs/{response.json()['run_id']}").json()
    assert run["status"] == "failed"
    assert run["terminal"] == "ERROR"
    assert run["message"] == trips_api.PLANNING_CRASHED
    assert run["infeasible"]["explanation"] == trips_api.PLANNING_CRASHED
    assert client.get(f"/api/trips/{trip_id}").json()["status"] == "error"


# --- a double click plans once ----------------------------------------------------------


def test_two_plan_requests_at_once_plan_only_once(monkeypatch):
    trip_id = new_trip()
    real_invoke = trips_api.trip_graph.invoke
    calls = []

    def slow_invoke(*args, **kwargs):
        calls.append(1)
        time.sleep(0.3)  # long enough for the second click to arrive mid-plan
        return real_invoke(*args, **kwargs)

    monkeypatch.setattr(trips_api.trip_graph, "invoke", slow_invoke)
    responses = []

    def click():
        responses.append(client.post(f"/api/trips/{trip_id}/plan"))

    clicks = [threading.Thread(target=click) for _ in range(2)]
    for thread in clicks:
        thread.start()
    for thread in clicks:
        thread.join()

    assert [r.status_code for r in responses] == [200, 200]
    assert len({r.json()["run_id"] for r in responses}) == 1  # both get the same run
    assert len(calls) == 1  # planned once, not twice


def test_plan_gives_409_when_the_trip_stays_busy(monkeypatch):
    trip_id = new_trip()
    monkeypatch.setattr(trips_api, "PLAN_WAIT_SECONDS", 0.05)
    lock = trips_api.lock_for(trip_id)
    lock.acquire()  # another plan or change is still running
    try:
        response = client.post(f"/api/trips/{trip_id}/plan")
    finally:
        lock.release()

    assert response.status_code == 409


# --- each run starts with fresh graph state ---------------------------------------------


def test_each_plan_uses_its_own_graph_thread_and_cleans_it_up(monkeypatch):
    trip_id = new_trip()
    real_invoke = trips_api.trip_graph.invoke
    thread_ids = []

    def spy(state, config):
        thread_ids.append(config["configurable"]["thread_id"])
        return real_invoke(state, config)

    monkeypatch.setattr(trips_api.trip_graph, "invoke", spy)
    run_id = client.post(f"/api/trips/{trip_id}/plan").json()["run_id"]

    assert thread_ids == [run_id]  # not the trip id, so no counters carry over
    saved = trips_api.trip_graph.checkpointer.list({"configurable": {"thread_id": run_id}})
    assert list(saved) == []  # nothing kept in memory after the run


# --- dates are exactly YYYY-MM-DD -------------------------------------------------------


@pytest.mark.parametrize("bad", ["2026-12-01T23:59", "20261201", "2026-W48-1", "12/01/2026"])
def test_trip_dates_must_be_plain_dates(bad):
    response = client.post("/api/trips", json={**TRIP, "start_date": bad})

    assert response.status_code == 422
    assert trips_api.DATE_FORMAT_ERROR in response.text


def test_answered_dates_must_be_plain_dates():
    trip_id = client.post("/api/trips", json={"destination": "Seattle"}).json()["trip"]["id"]

    response = client.post(
        f"/api/trips/{trip_id}/answers",
        json={"answers": {"start_date": "2026-12-01T23:59", "end_date": "2026-12-02"}},
    )

    assert response.status_code == 422
    assert response.json()["detail"] == trips_api.DATE_FORMAT_ERROR
