"""Trips are planned around the real destination, not Seattle (no network in these tests)."""

import httpx
import pytest
from fastapi.testclient import TestClient

from app.agents.planner import plan_and_validate
from app.config import settings
from app.graph import trip_planner
from app.main import app
from app.tools import geocode
from app.tools.geocode import locate_city
from app.tools.mock_places import MockPlaceSearch

client = TestClient(app)


# --- Looking the city up -------------------------------------------------------


@pytest.mark.parametrize("name", ["Paris", "  paris ", "Paris, France", "PARIS"])
def test_known_city_is_found_without_a_key(name):
    location = locate_city(name)

    assert location is not None
    assert (round(location.lat), round(location.lng)) == (49, 2)
    assert location.timezone == "Europe/Paris"
    assert location.source == "builtin"


@pytest.mark.parametrize("name", ["", "   ", "Narnia", "Parisville"])
def test_unknown_city_is_none(name):
    assert locate_city(name) is None


class FakeResponse:
    def __init__(self, status, body):
        self.status_code = status
        self._body = body

    def json(self):
        return self._body

    def raise_for_status(self):
        if self.status_code >= 400:
            request = httpx.Request("GET", "https://api.geoapify.com/v1/geocode/search?apiKey=SECRET")
            response = httpx.Response(self.status_code)
            raise httpx.HTTPStatusError("bad", request=request, response=response)


@pytest.fixture
def live_geocoding(monkeypatch):
    monkeypatch.setattr(settings, "DEMO_MODE", False)
    monkeypatch.setattr(settings, "GEOAPIFY_API_KEY", "SECRET")
    geocode._ask_geoapify.cache_clear()
    yield
    geocode._ask_geoapify.cache_clear()


def test_live_lookup_uses_geoapify_and_its_time_zone(monkeypatch, live_geocoding):
    calls = []

    def fake_get(url, params, timeout):
        calls.append(params["text"])
        return FakeResponse(200, {"results": [{
            "lat": 12.97, "lon": 77.59, "formatted": "Bengaluru, India",
            "timezone": {"name": "Asia/Kolkata"},
        }]})

    monkeypatch.setattr(geocode.httpx, "get", fake_get)

    location = locate_city("Bengaluru")
    locate_city("bengaluru")  # same city again: cached, no second request

    assert location.name == "Bengaluru, India"
    assert location.timezone == "Asia/Kolkata"
    assert location.source == "geoapify"
    assert calls == ["bengaluru"]


def test_live_lookup_with_no_result_is_none(monkeypatch, live_geocoding):
    monkeypatch.setattr(geocode.httpx, "get", lambda *a, **k: FakeResponse(200, {"results": []}))

    assert locate_city("Atlantis") is None


def test_provider_error_falls_back_to_the_built_in_list(monkeypatch, live_geocoding):
    monkeypatch.setattr(geocode.httpx, "get", lambda *a, **k: FakeResponse(503, {}))

    assert locate_city("Rome").source == "builtin"


def test_provider_error_message_never_contains_the_key(monkeypatch, live_geocoding):
    monkeypatch.setattr(geocode.httpx, "get", lambda *a, **k: FakeResponse(401, {}))

    with pytest.raises(geocode.GeocodeError) as error:
        geocode._ask_geoapify("somewhere")

    assert "SECRET" not in str(error.value)


# --- Searching around the destination ------------------------------------------


class RecordingSearch:
    """A live-style search (not the Seattle mock) that remembers where it searched."""

    def __init__(self):
        self.near = []
        self.mock = MockPlaceSearch()

    def search_places(self, **kwargs):
        self.near.append(kwargs.get("near"))
        return self.mock.search_places(**{**kwargs, "near": None})


def test_places_are_searched_around_the_destination(monkeypatch):
    search = RecordingSearch()
    monkeypatch.setattr(trip_planner, "get_place_search", lambda: search)

    trip_planner._search_places({"destination": "Chicago", "interests": ["coffee"]})

    assert search.near and all(
        (round(p.lat), round(p.lng)) == (42, -88) for p in search.near
    )


def test_unknown_destination_gives_a_clear_message():
    with pytest.raises(RuntimeError, match="could not find the destination 'Narnia'"):
        trip_planner._search_places({"destination": "Narnia", "interests": ["coffee"]})


def test_demo_mode_says_it_only_has_seattle():
    with pytest.raises(RuntimeError, match="Demo mode only has places in Seattle"):
        trip_planner._search_places({"destination": "Paris", "interests": ["coffee"]})


def test_read_step_stores_the_center_and_time_zone():
    state = trip_planner._read_trip({"trip": {"destination": "Tokyo"}, "logs": []})

    assert state["trip"]["center"] == {"lat": 35.6762, "lng": 139.6503}
    assert state["trip"]["timezone"] == "Asia/Tokyo"
    assert "destination found: Tokyo" in state["logs"][-1]["metadata"]["message"]


# --- Times in the destination's time zone ----------------------------------------


def test_plan_uses_the_looked_up_time_zone():
    place = {
        "id": "p1", "name": "Somewhere", "experience_types": ["culture"],
        "lat": 12.97, "lng": 77.59, "est_cost_low": 0, "hours": None,
    }
    trip = {
        "destination": "Bengaluru", "timezone": "Asia/Kolkata",
        "start_date": "2026-11-20", "end_date": "2026-11-20",
    }

    itinerary, _ = plan_and_validate(trip, [place])

    assert itinerary["days"][0]["activities"][0]["start"].endswith("+05:30")


# --- Through the API ----------------------------------------------------------------


def plan(destination):
    trip_id = client.post(
        "/api/trips",
        json={"destination": destination, "start_date": "2026-11-20", "end_date": "2026-11-20"},
    ).json()["trip"]["id"]
    run_id = client.post(f"/api/trips/{trip_id}/plan").json()["run_id"]
    return client.get(f"/api/runs/{run_id}").json()


def test_api_explains_an_unknown_destination():
    run = plan("Narnia")

    assert run["status"] == "failed"
    assert "could not find the destination" in run["message"]


def test_api_seattle_still_works_in_demo_mode():
    assert plan("Seattle")["terminal"] == "PASS"


# --- A state name means its big city, but only in the same country -------------


def answer(formatted, lat, lon, kind, country, tz="America/New_York"):
    return {"results": [{
        "formatted": formatted, "lat": lat, "lon": lon, "result_type": kind,
        "country_code": country, "timezone": {"name": tz},
    }]}


def test_state_name_becomes_the_city_in_the_same_country(monkeypatch, live_geocoding):
    def fake_get(url, params, timeout):
        if params.get("type") == "city":
            return FakeResponse(200, answer("New York, NY", 40.71, -74.01, "city", "us"))
        return FakeResponse(200, answer("New York (state)", 43.16, -75.84, "state", "us"))

    monkeypatch.setattr(geocode.httpx, "get", fake_get)

    location = locate_city("New York")

    assert (round(location.lat), round(location.lng)) == (41, -74)


def test_state_name_stays_when_the_city_is_in_another_country(monkeypatch, live_geocoding):
    def fake_get(url, params, timeout):
        if params.get("type") == "city":
            return FakeResponse(200, answer("Goa, Philippines", 13.70, 123.49, "city", "ph"))
        return FakeResponse(200, answer("Goa, India", 15.30, 74.09, "state", "in"))

    monkeypatch.setattr(geocode.httpx, "get", fake_get)

    assert locate_city("Goa").name == "Goa, India"


# --- The same place listed twice is one place ------------------------------------


def place(place_id, name, lat):
    from app.tools.place import Place

    return Place(
        id=place_id, sources=["geoapify"], name=name, categories=["park"],
        experience_types=["nature"], lat=lat, lng=-75.89, address="",
        cost_basis="unknown", retrieved_at="2026-11-11T00:00:00Z",
    )


def test_same_name_close_together_is_one_place():
    from app.agents.discovery import _same_place

    assert _same_place(place("a", "Chapman Park", 43.150), place("b", "Chapman  park", 43.154))


def test_same_name_far_apart_is_two_places():
    from app.agents.discovery import _same_place

    assert not _same_place(place("a", "Central Park", 43.15), place("b", "Central Park", 43.30))
