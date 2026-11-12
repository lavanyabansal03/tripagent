"""Trips are planned around the real destination, not Seattle (no network in these tests).

TripAgent plans US trips for now (ALLOWED_COUNTRIES in config.py).
"""

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


@pytest.mark.parametrize("name", ["Chicago", "  chicago ", "Chicago, IL", "CHICAGO"])
def test_known_city_is_found_without_a_key(name):
    location = locate_city(name)

    assert location is not None
    assert (round(location.lat), round(location.lng)) == (42, -88)
    assert location.timezone == "America/Chicago"
    assert location.source == "builtin"


# USA only for now: cities elsewhere are not in the built-in list.
@pytest.mark.parametrize("name", ["", "   ", "Narnia", "Parisville", "Paris", "Tokyo"])
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


def answer(formatted, lat, lon, kind, country, tz="America/New_York", importance=None, **names):
    """One Geoapify geocoding answer, shaped like the real API."""
    return {"results": [{
        "formatted": formatted, "lat": lat, "lon": lon, "result_type": kind,
        "country_code": country, "timezone": {"name": tz},
        "rank": {"importance": importance}, **names,
    }]}


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
        calls.append(params)
        return FakeResponse(200, answer("Boise, ID", 43.61, -116.20, "city", "us",
                                        tz="America/Boise", importance=0.6, city="Boise"))

    monkeypatch.setattr(geocode.httpx, "get", fake_get)

    location = locate_city("Boise")
    locate_city("boise")  # same city again: cached, no second request

    assert location.name == "Boise, ID"
    assert location.timezone == "America/Boise"
    assert location.source == "geoapify"
    assert len(calls) == 1
    assert calls[0]["filter"] == "countrycode:us"  # USA only for now


def test_live_lookup_with_no_result_is_none(monkeypatch, live_geocoding):
    monkeypatch.setattr(geocode.httpx, "get", lambda *a, **k: FakeResponse(200, {"results": []}))

    assert locate_city("Atlantis") is None


def test_provider_error_falls_back_to_the_built_in_list(monkeypatch, live_geocoding):
    monkeypatch.setattr(geocode.httpx, "get", lambda *a, **k: FakeResponse(503, {}))

    assert locate_city("Boston").source == "builtin"


def test_provider_error_message_never_contains_the_key(monkeypatch, live_geocoding):
    monkeypatch.setattr(geocode.httpx, "get", lambda *a, **k: FakeResponse(401, {}))

    with pytest.raises(geocode.GeocodeError) as error:
        geocode._ask_geoapify("somewhere")

    assert "SECRET" not in str(error.value)


def test_answer_outside_the_usa_is_ignored(monkeypatch, live_geocoding):
    monkeypatch.setattr(geocode.httpx, "get", lambda *a, **k: FakeResponse(
        200, answer("Paris, France", 48.85, 2.35, "city", "fr", importance=0.9, city="Paris")))

    assert locate_city("Paris") is None


def test_a_street_is_not_a_destination(monkeypatch, live_geocoding):
    # Seen live: "Goa" matched "Goa Way" in Colorado Springs.
    def fake_get(url, params, timeout):
        if params.get("type") == "city":
            return FakeResponse(200, {"results": []})
        return FakeResponse(200, answer("Goa Way, Colorado Springs", 38.9, -104.8, "street",
                                        "us", street="Goa Way", city="Colorado Springs"))

    monkeypatch.setattr(geocode.httpx, "get", fake_get)

    assert locate_city("Goa") is None


def test_a_place_with_another_name_is_not_a_match(monkeypatch, live_geocoding):
    # Seen live: "Tokyo" matched "Little Tokyo" in Los Angeles.
    monkeypatch.setattr(geocode.httpx, "get", lambda *a, **k: FakeResponse(
        200, answer("Little Tokyo, Los Angeles", 34.05, -118.24, "city", "us",
                    name="Little Tokyo", city="Los Angeles")))

    assert locate_city("Tokyo") is None


def test_longer_name_matches_the_city(monkeypatch, live_geocoding):
    monkeypatch.setattr(geocode.httpx, "get", lambda *a, **k: FakeResponse(
        200, answer("New York, NY", 40.71, -74.01, "city", "us", importance=0.9,
                    city="New York")))

    assert locate_city("New York City").name == "New York, NY"


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
    with pytest.raises(trip_planner.TripProblem,
                       match="could not find the destination 'Narnia' in the United States"):
        trip_planner._search_places({"destination": "Narnia", "interests": ["coffee"]})


def test_demo_mode_says_it_only_has_seattle():
    with pytest.raises(trip_planner.TripProblem, match="Demo mode only has places in Seattle"):
        trip_planner._search_places({"destination": "Chicago", "interests": ["coffee"]})


def test_read_step_stores_the_center_and_time_zone():
    state = trip_planner._read_trip({"trip": {"destination": "Honolulu"}, "logs": []})

    assert state["trip"]["center"] == {"lat": 21.3069, "lng": -157.8583}
    assert state["trip"]["timezone"] == "Pacific/Honolulu"
    assert "destination found: Honolulu" in state["logs"][-1]["metadata"]["message"]


# --- Times in the destination's time zone ----------------------------------------


def test_plan_uses_the_looked_up_time_zone():
    place = {
        "id": "p1", "name": "Somewhere", "experience_types": ["culture"],
        "lat": 21.30, "lng": -157.86, "est_cost_low": 0, "hours": None,
    }
    trip = {
        "destination": "Honolulu", "timezone": "Pacific/Honolulu",
        "start_date": "2026-11-20", "end_date": "2026-11-20",
    }

    itinerary, _ = plan_and_validate(trip, [place])

    assert itinerary["days"][0]["activities"][0]["start"].endswith("-10:00")


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
    assert run["infeasible"]["explanation"] == run["message"]  # shown by the website


def test_api_seattle_still_works_in_demo_mode():
    run = plan("Seattle")

    assert run["terminal"] == "PASS"
    assert run["infeasible"] is None


class EmptySearch:
    calls = 0

    def search_places(self, **kwargs):
        EmptySearch.calls += 1
        return []


def test_no_places_found_stops_with_a_clear_message(monkeypatch):
    # Before: 0 places gave a plan of empty days and no explanation ("no trips").
    EmptySearch.calls = 0
    monkeypatch.setattr(trip_planner, "get_place_search", lambda: EmptySearch())

    run = plan("Seattle")

    assert run["status"] == "failed"
    assert "couldn't find any places near Seattle" in run["message"]
    assert run["infeasible"]["explanation"] == run["message"]
    first_round = EmptySearch.calls
    assert first_round > 0
    # A traveller problem is not retried: the searches ran once, not MAX_FIND_ATTEMPTS times.
    assert first_round <= 8


# --- A state name means its big city; a small town loses to a well-known city -----


def test_state_name_becomes_the_city_in_the_same_country(monkeypatch, live_geocoding):
    def fake_get(url, params, timeout):
        if params.get("type") == "city":
            return FakeResponse(200, answer("New York, NY", 40.71, -74.01, "city", "us",
                                            importance=0.9, city="New York"))
        return FakeResponse(200, answer("New York (state)", 43.16, -75.84, "state", "us",
                                        state="New York"))

    monkeypatch.setattr(geocode.httpx, "get", fake_get)

    location = locate_city("New York")

    assert (round(location.lat), round(location.lng)) == (41, -74)


def test_small_town_loses_to_a_clearly_bigger_city(monkeypatch, live_geocoding):
    # Seen live: "San Antonio, Texas" first matched a small place, giving 0 places.
    def fake_get(url, params, timeout):
        if params.get("type") == "city":
            return FakeResponse(200, answer("San Antonio, TX", 29.42, -98.49, "city", "us",
                                            tz="America/Chicago", importance=0.8,
                                            city="San Antonio"))
        return FakeResponse(200, answer("San Antonio Village", 31.0, -99.0, "city", "us",
                                        tz="America/Chicago", importance=0.1,
                                        city="San Antonio"))

    monkeypatch.setattr(geocode.httpx, "get", fake_get)

    assert locate_city("San Antonio, Texas").name == "San Antonio, TX"


def test_well_known_city_is_kept(monkeypatch, live_geocoding):
    calls = []

    def fake_get(url, params, timeout):
        calls.append(params)
        return FakeResponse(200, answer("Austin, TX", 30.27, -97.74, "city", "us",
                                        tz="America/Chicago", importance=0.8, city="Austin"))

    monkeypatch.setattr(geocode.httpx, "get", fake_get)

    assert locate_city("Austin").name == "Austin, TX"
    assert len(calls) == 1  # no second lookup needed


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
