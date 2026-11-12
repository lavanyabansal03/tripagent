"""Discovery agent tests. They use the Seattle mock or tiny fake searches, so no network."""

from app.agents.discovery import MIN_PER_INTEREST, discover_places
from app.config import MAX_DISCOVERY_CALLS
from app.graph.trip_planner import _search_places
from app.tools.mock_places import MockPlaceSearch
from app.tools.place import Place


def make_place(name: str, kinds: list[str], lat: float = 47.6, lng: float = -122.3) -> Place:
    return Place(
        id=name.lower().replace(" ", "-"), sources=["seed"], name=name, categories=kinds,
        experience_types=[], lat=lat, lng=lng, address="", retrieved_at="2026-11-10T00:00:00Z",
    )


class CountingSearch:
    """A fake search that counts calls and returns whatever `answer` gives back."""

    def __init__(self, answer):
        self.answer = answer
        self.calls: list[dict] = []

    def search_places(self, **kwargs):
        self.calls.append(kwargs)
        return self.answer(**kwargs)


def test_seattle_mock_covers_common_interests():
    result = discover_places({"interests": ["cafe", "nature", "culture"]}, MockPlaceSearch())
    assert result.status == "PASS"
    assert all(n >= MIN_PER_INTEREST for n in result.coverage.values())
    # One focused search each was enough, plus one lunch search (no interest found food).
    assert result.calls_used == 4
    assert any("restaurant" in p.categories for p in result.places)
    assert len({p.id for p in result.places}) == len(result.places)  # no duplicates


def test_first_places_mix_the_interests():
    result = discover_places({"interests": ["cafe", "nature"]}, MockPlaceSearch())
    first_two = result.places[:2]
    assert any("cafe" in p.experience_types for p in first_two)
    assert any("nature" in p.experience_types for p in first_two)


def test_thin_interest_gets_one_wider_search_then_stops():
    search = CountingSearch(lambda **kw: [make_place("Lone Gallery", ["art"])])
    result = discover_places({"interests": ["art"]}, search)
    # focused, then wide, then one lunch search (no restaurant yet), then no more
    assert len(search.calls) == 3
    assert "categories" not in search.calls[1] or search.calls[1]["categories"] is None
    assert search.calls[2]["query"] == "restaurant"
    assert result.status == "INFEASIBLE"
    assert "art" in result.reason


def test_never_more_calls_than_the_cap():
    search = CountingSearch(lambda **kw: [])
    interests = [f"interest{i}" for i in range(10)]
    result = discover_places({"interests": interests}, search)
    assert len(search.calls) == MAX_DISCOVERY_CALLS
    assert result.calls_used == MAX_DISCOVERY_CALLS
    assert result.status == "INFEASIBLE"
    assert "limit" in result.reason


def test_all_calls_failing_is_an_error():
    def broken(**kw):
        raise RuntimeError("provider down")

    result = discover_places({"interests": ["cafe"]}, CountingSearch(broken))
    assert result.status == "ERROR"
    assert result.places == []


def test_same_cafe_from_two_providers_is_merged():
    first = make_place("Victrola Coffee Roasters", ["cafe"])
    second = make_place("Victrola Coffee Roaster", ["cafe"], lat=47.6002)  # ~20 m away
    second.id, second.sources, second.provider_ids = "geo-1", ["geoapify"], {"geoapify": "1"}
    far = make_place("Victrola Coffee Roasters", ["cafe"], lat=47.61)  # ~1 km: a branch
    far.id = "branch"
    result = discover_places(
        {"interests": ["cafe"]}, CountingSearch(lambda **kw: [first, second, far])
    )
    assert [p.id for p in result.places] == ["victrola-coffee-roasters", "branch"]
    assert result.places[0].sources == ["seed", "geoapify"]


def test_no_interests_searches_anything():
    result = discover_places({"interests": []}, MockPlaceSearch())
    assert result.status == "PASS"
    assert result.calls_used == 1


def test_unknown_interest_still_returns_some_places():
    result = discover_places({"interests": ["zzzz"]}, MockPlaceSearch())
    assert result.status == "INFEASIBLE"
    assert result.places  # a last "anything" search keeps the plan from being empty


def test_graph_find_step_uses_discovery():
    trip = {"destination": "Seattle", "interests": ["cafe", "nature"], "mode": "walking"}
    places = _search_places(trip)
    assert places and isinstance(places[0], dict)
    assert {"id", "name", "lat", "lng"} <= places[0].keys()
