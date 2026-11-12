"""Tests for the database layer (app/storage.py, ADR-005)."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

from app import storage
from app.main import app

client = TestClient(app)


def trip_row(trip_id="t1", status="draft"):
    return {"id": trip_id, "destination": "Seattle", "status": status}


def test_trip_is_saved_and_updated():
    storage.save_trip(trip_row(), {"trip_id": "t1"}, [{"id": "q"}], 1, False)
    storage.save_trip(trip_row(status="planned"), {"trip_id": "t1"}, [], 1, True)

    record = storage.get_trip("t1")

    assert record["trip"]["status"] == "planned"
    assert record["questions"] == []
    assert record["clarification_exhausted"] is True
    assert storage.get_trip("missing") is None


def test_itinerary_versions_are_kept_and_never_overwritten():
    storage.save_itinerary("t1", {"version": 1, "days": ["first"]})
    storage.save_itinerary("t1", {"version": 2, "days": ["second"]})

    assert storage.list_versions("t1") == [1, 2]
    assert storage.get_itinerary("t1")["days"] == ["second"]  # newest
    assert storage.get_itinerary("t1", 1)["days"] == ["first"]
    assert storage.get_itinerary("t1", 9) is None
    with pytest.raises(IntegrityError):
        storage.save_itinerary("t1", {"version": 1, "days": ["again"]})


def test_runs_are_saved_found_and_updated():
    storage.save_run({"run_id": "r1", "trip_id": "t1", "status": "running"})
    storage.save_run({"run_id": "r1", "trip_id": "t1", "status": "done"})

    assert storage.get_run("r1")["status"] == "done"
    assert storage.run_id_for_trip("t1") == "r1"
    assert storage.get_run("missing") is None
    assert storage.run_id_for_trip("other") is None


def test_a_failed_planning_run_is_not_reused():
    # A failed plan must not block "Try again" (it used to hand back the failure forever).
    storage.save_run({"run_id": "bad", "trip_id": "t1", "status": "failed", "phase": "done"})
    assert storage.run_id_for_trip("t1") is None

    storage.save_run({"run_id": "good", "trip_id": "t1", "status": "done", "phase": "done"})
    assert storage.run_id_for_trip("t1") == "good"


def test_trace_keeps_order_and_a_rerun_replaces_it():
    storage.save_trace("t1", "r1", [{"node": "read"}, {"node": "find"}])
    storage.save_trace("t1", "r1", [{"node": "read"}, {"node": "find"}, {"node": "save"}])

    assert [e["node"] for e in storage.get_trace("t1")] == ["read", "find", "save"]
    assert storage.get_trace("other") == []


@pytest.mark.parametrize(
    "given, expected",
    [
        ("postgres://u:p@host/db", "postgresql+psycopg://u:p@host/db"),
        ("postgresql://u:p@host/db?sslmode=require", "postgresql+psycopg://u:p@host/db?sslmode=require"),
        ("sqlite:///./tripagent.db", "sqlite:///./tripagent.db"),
    ],
)
def test_postgres_links_use_the_psycopg_driver(given, expected):
    assert storage._database_url(given) == expected


# --- Through the API ---------------------------------------------------------


def plan_a_trip():
    created = client.post(
        "/api/trips",
        json={
            "destination": "Seattle",
            "start_date": "2026-11-12",
            "end_date": "2026-11-12",
            "interests": ["coffee"],
        },
    ).json()
    trip_id = created["trip"]["id"]
    run_id = client.post(f"/api/trips/{trip_id}/plan").json()["run_id"]
    return trip_id, run_id


def test_planning_saves_a_version_the_run_and_the_trace():
    trip_id, run_id = plan_a_trip()

    assert client.get(f"/api/trips/{trip_id}/versions").json() == [1]
    assert client.get(f"/api/trips/{trip_id}/itinerary?version=1").json()["version"] == 1
    assert client.get(f"/api/trips/{trip_id}").json()["current_version"] == 1
    assert client.get(f"/api/runs/{run_id}").json()["status"] == "done"
    assert client.get(f"/api/trips/{trip_id}/trace").json()[0]["node"] == "read"


def test_trips_survive_a_server_restart(tmp_path):
    """The point of the database: data is still there after a restart."""
    database_file = f"sqlite:///{tmp_path / 'tripagent.db'}"
    storage.use_database(database_file)
    trip_id, run_id = plan_a_trip()
    storage.engine().dispose()

    storage.use_database(database_file)  # like the server starting again

    assert client.get(f"/api/trips/{trip_id}").json()["status"] == "planned"
    assert client.get(f"/api/trips/{trip_id}/itinerary").json()["days"]
    assert client.get(f"/api/runs/{run_id}").json()["terminal"] == "PASS"
    assert client.get(f"/api/trips/{trip_id}/trace").json()
    storage.engine().dispose()


def test_empty_database_url_means_the_local_sqlite_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    engine = storage.use_database("   ")

    assert str(engine.url) == "sqlite:///./tripagent.db"
    assert (tmp_path / "tripagent.db").exists()
    engine.dispose()
