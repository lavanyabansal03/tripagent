"""Famous places: the LLM names them, code finds them on the map (no network here)."""

import httpx
import pytest

from app.agents import famous
from app.agents.discovery import famous_first
from app.agents.famous import FamousNames, FamousPlace, find_famous, how_many, suggest_names
from app.tools.base import LatLng
from app.tools.geoapify import GeoapifyPlaceSearch
from app.tools.mock_places import MockPlaceSearch, name_match, same_name
from app.tools.place import Place

NYC = LatLng(lat=40.7484, lng=-73.9857)


def trip(**overrides):
    return {
        "destination": "New York", "start_date": "2026-11-20", "end_date": "2026-11-22",
        "pace": "moderate", "tourist_local_ratio": 50, "interests": ["food", "culture"],
        "avoid": [], **overrides,
    }


def fake_llm(monkeypatch, names):
    prompts = []

    def ask(prompt, shape):
        prompts.append(prompt)
        if names is None:
            return None
        # "Name" or ("Name", "Short name")
        pairs = [n if isinstance(n, tuple) else (n, "") for n in names]
        return FamousNames(places=[FamousPlace(name=n, short_name=s) for n, s in pairs])

    monkeypatch.setattr(famous, "ask_json", ask)
    return prompts


EXPERIENCES = {"food", "cafe", "nature", "culture", "shopping", "nightlife", "landmark"}


def place(name, kinds=("landmark",), place_id=None):
    return Place(
        id=place_id or f"geoapify:{name}", sources=["geoapify"], name=name,
        categories=list(kinds), experience_types=[k for k in kinds if k in EXPERIENCES],
        lat=40.75, lng=-73.98, address="", retrieved_at="2026-11-12T00:00:00Z",
    )


class FakeSearch:
    """Knows a few places by name, like the map does."""

    def __init__(self, known):
        self.known = {p.name: p for p in known}
        self.asked = []

    def find_by_name(self, name, near, area=""):
        self.asked.append((name, area))
        if name == "Broken":
            raise RuntimeError("provider down")
        return self.known.get(name)


# --- how many -----------------------------------------------------------------


@pytest.mark.parametrize(
    "ratio, pace, expected",
    [
        (50, "moderate", 6),   # 3 days x 4 stops = 12, half famous
        (0, "packed", 12),     # all famous, capped at MAX_FAMOUS_PLACES
        (100, "moderate", 0),  # all local favourites: no famous lookup at all
        (40, "relaxed", 5),    # 9 stops x 60 %
    ],
)
def test_the_slider_decides_how_many(ratio, pace, expected):
    assert how_many(trip(tourist_local_ratio=ratio, pace=pace)) == expected


# --- the LLM's names are checked -------------------------------------------------


def test_names_are_cleaned(monkeypatch):
    fake_llm(monkeypatch, [
        "  Times   Square ", "", "times square", "x" * 200,
        ("The Museum of Modern Art", " MoMA "), ("Joe's Pizza", "joe's pizza"),
    ])

    assert suggest_names(trip(), 5) == [
        ("Times Square", ""), ("The Museum of Modern Art", "MoMA"), ("Joe's Pizza", ""),
    ]


def test_short_name_is_tried_only_when_the_full_name_is_not_found(monkeypatch):
    # Seen live: the map calls it "MoMA", not "The Museum of Modern Art".
    fake_llm(monkeypatch, [("The Museum of Modern Art", "MoMA"), ("Central Park", "The Park")])
    search = FakeSearch([place("MoMA", ("culture",)), place("Central Park", ("nature",))])

    found, asked = find_famous(trip(), search, NYC)

    assert [p.name for p in found] == ["MoMA", "Central Park"]
    assert asked == ["The Museum of Modern Art", "Central Park"]
    tried = sorted(name for name, _ in search.asked)  # lookups run in parallel
    assert tried == ["Central Park", "MoMA", "The Museum of Modern Art"]  # never "The Park"


def test_no_llm_means_no_famous_places(monkeypatch):
    fake_llm(monkeypatch, None)

    assert suggest_names(trip(), 5) == []


def test_prompt_has_the_city_interests_and_avoid_list(monkeypatch):
    prompts = fake_llm(monkeypatch, [])

    suggest_names(trip(avoid=["nightlife"], location_name="New York, NY"), 4)

    assert "4 famous" in prompts[0] and "New York, NY" in prompts[0]
    assert "food, culture" in prompts[0] and "nightlife" in prompts[0]


# --- only places found on the map are used ---------------------------------------


def test_only_names_found_on_the_map_are_kept(monkeypatch):
    fake_llm(monkeypatch, ["Times Square", "Made Up Diner", "Broken", "Joe's Pizza"])
    search = FakeSearch([place("Times Square"), place("Joe's Pizza", ("restaurant", "food"))])

    found, asked = find_famous(trip(location_name="New York, NY"), search, NYC)

    assert [p.name for p in found] == ["Times Square", "Joe's Pizza"]
    assert asked == ["Times Square", "Made Up Diner", "Broken", "Joe's Pizza"]
    assert all(p.local_signal == "tourist" for p in found)
    assert found[0].field_provenance["local_signal"] == "inferred"
    assert search.asked[0] == ("Times Square", "New York, NY")  # searched in the right city


def test_avoided_kinds_are_dropped(monkeypatch):
    fake_llm(monkeypatch, ["McSorley's", "The Met"])
    search = FakeSearch([place("McSorley's", ("bar", "nightlife")), place("The Met", ("culture",))])

    found, _ = find_famous(trip(avoid=["nightlife"]), search, NYC)

    assert [p.name for p in found] == ["The Met"]


def test_a_search_without_name_lookup_is_skipped(monkeypatch):
    fake_llm(monkeypatch, ["Times Square"])

    assert find_famous(trip(), object(), NYC) == ([], [])


def test_famous_places_come_first_and_once():
    met = place("The Met", ("culture",), place_id="geoapify:1")
    nearby = [
        place("Corner Deli", ("food",), "geoapify:2"),
        place("The Met", ("culture",), "geoapify:1"),
    ]

    assert [p.name for p in famous_first([met], nearby)] == ["The Met", "Corner Deli"]


# --- matching a name ------------------------------------------------------------------


@pytest.mark.parametrize(
    "asked, found, score",
    [
        ("The Alamo", "Alamo", 3),
        ("Katz's Delicatessen", "Katz's", 2),
        ("The Alamo", "The Alamo Gift Shop", 1),
        ("Times Square", "Herald Square", 0),
    ],
)
def test_name_match_scores(asked, found, score):
    assert name_match(asked, found) == score


@pytest.mark.parametrize(
    "asked, found, same",
    [
        ("Joe's Pizza", "Joes Pizza", True),
        ("The Metropolitan Museum of Art", "Metropolitan Museum of Art", True),
        ("Eataly NYC Downtown", "Eataly", True),
        ("The Met", "Metropolitan Opera House", False),
        ("The Alamo", "The Alamo Gift Shop", False),  # seen live
        ("Museum of Modern Art", "Museum of Modern Art (MoMA) films", False),  # seen live
        ("Times Square", "Herald Square", False),
    ],
)
def test_same_name(asked, found, same):
    assert same_name(asked, found) is same


# --- the live adapter: geocoding, then details ----------------------------------------


def geoapify(answers):
    seen = []

    def handler(request):
        seen.append(request)
        return httpx.Response(200, json=answers.pop(0))

    client = httpx.Client(transport=httpx.MockTransport(handler))
    return GeoapifyPlaceSearch("SECRET", client=client), seen


DETAILS = {"features": [{"properties": {
    "place_id": "abc", "name": "Joe's Pizza", "lat": 40.73, "lon": -74.0,
    "categories": ["catering", "catering.fast_food.pizza"], "opening_hours": "Mo-Su 10:00-23:00",
    "formatted": "7 Carmine St, New York",
}}]}


def test_live_lookup_prefers_the_exact_name():
    # Seen live: "The Alamo" became "The Alamo Gift Shop" (the first answer).
    search, seen = geoapify([
        {"results": [
            {"name": "The Alamo Gift Shop", "result_type": "amenity", "place_id": "shop"},
            {"name": "Alamo Street", "result_type": "street", "place_id": "street"},
            {"name": "The Alamo", "result_type": "amenity", "place_id": "abc"},
        ]},
        {"features": [{"properties": {
            "place_id": "abc", "name": "The Alamo", "lat": 29.42, "lon": -98.48,
            "categories": ["tourism.sights"],
        }}]},
    ])

    assert search.find_by_name("The Alamo", NYC).name == "The Alamo"
    assert seen[1].url.params["id"] == "abc"


def test_both_llm_steps_are_in_the_trace(monkeypatch):
    from app.agents import discovery_plan
    from app.agents.discovery_plan import InterestWords, SearchPlan

    fake_llm(monkeypatch, ["Space Needle"])
    monkeypatch.setattr(discovery_plan, "ask_json", lambda prompt, shape: SearchPlan(
        interests=[InterestWords(interest="coffee", words=["cafe"])]))
    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)
    trip_id = client.post("/api/trips", json={
        "destination": "Seattle", "start_date": "2026-11-20", "end_date": "2026-11-20",
        "interests": ["coffee"], "tourist_local_ratio": 0,
    }).json()["trip"]["id"]
    client.post(f"/api/trips/{trip_id}/plan")

    nodes = [e["node"] for e in client.get(f"/api/trips/{trip_id}/trace").json()]
    assert "famous_places" in nodes and "search_plan" in nodes


def test_live_lookup_uses_the_place_details():
    search, seen = geoapify([
        {"results": [{"name": "Joe's Pizza", "result_type": "amenity", "place_id": "abc"}]},
        DETAILS,
    ])

    found = search.find_by_name("Joe's Pizza", NYC, "New York, NY")

    assert found.name == "Joe's Pizza" and found.id == "geoapify:abc"
    assert found.hours is not None  # real opening hours from the map
    assert seen[0].url.params["text"] == "Joe's Pizza, New York, NY"
    assert "circle:-73.9857,40.7484" in seen[0].url.params["filter"]
    assert seen[1].url.params["id"] == "abc"


@pytest.mark.parametrize(
    "result",
    [
        {"name": "Joe's Pizza Way", "result_type": "street", "place_id": "s"},
        {"name": "Little Italy", "result_type": "amenity", "place_id": "x"},
        {"result_type": "amenity", "place_id": "x"},
    ],
)
def test_live_lookup_refuses_other_places(result):
    search, seen = geoapify([{"results": [result]}])

    assert search.find_by_name("Joe's Pizza", NYC) is None
    assert len(seen) == 1  # no details call for a wrong match


def test_famous_places_reach_the_plan_and_the_trace(monkeypatch):
    from fastapi.testclient import TestClient

    from app.main import app

    fake_llm(monkeypatch, ["Space Needle", "Pike Place Market", "Imaginary Tower"])
    client = TestClient(app)
    trip_id = client.post("/api/trips", json={
        "destination": "Seattle", "start_date": "2026-11-20", "end_date": "2026-11-20",
        "interests": ["coffee"], "tourist_local_ratio": 0,
    }).json()["trip"]["id"]
    client.post(f"/api/trips/{trip_id}/plan")

    itinerary = client.get(f"/api/trips/{trip_id}/itinerary").json()
    names = [a["place"]["name"] for d in itinerary["days"] for a in d["activities"]]
    assert {"Space Needle", "Pike Place Market"} <= set(names)  # only coffee was asked for
    assert "Imaginary Tower" not in names  # not on the map, so never used

    trace = client.get(f"/api/trips/{trip_id}/trace").json()
    event = next(e for e in trace if e["node"] == "famous_places")
    assert event["type"] == "llm"
    assert event["metadata"]["found"] == ["Space Needle", "Pike Place Market"]


def test_demo_lookup_finds_seed_places():
    found = MockPlaceSearch().find_by_name("Space Needle", LatLng(lat=47.6, lng=-122.3))

    assert found is not None and found.name == "Space Needle"
    assert MockPlaceSearch().find_by_name("Times Square", NYC) is None
