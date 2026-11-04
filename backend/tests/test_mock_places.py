import pytest
from pydantic import ValidationError

from app.tools import get_place_search
from app.tools.base import LatLng
from app.tools.mock_places import MockPlaceSearch, distance_km, rough_minutes
from app.tools.place import Place
from app.tools.seattle_seed import load_seattle_places

PIKE_PLACE = LatLng(lat=47.6097, lng=-122.3425)
search = MockPlaceSearch()


def names(places: list[Place]) -> set[str]:
    return {place.name for place in places}


def test_seed_has_21_valid_seattle_places():
    places = load_seattle_places()
    assert len(places) == 21
    assert len({p.id for p in places}) == 21  # every id is unique
    for p in places:
        assert p.sources == ["seed"]
        assert 47.4 < p.lat < 47.8
        assert -122.5 < p.lng < -122.2


def test_seed_never_invents_data():
    for p in load_seattle_places():
        assert p.hours is None
        assert p.rating is None
        assert p.review_count is None
        assert p.popularity is None
        assert p.price_level is None
        assert p.local_signal == "unknown"


def test_unknown_cost_is_not_zero():
    by_name = {p.name: p for p in load_seattle_places()}
    park = by_name["Kerry Park"]
    assert park.cost_basis == "free"
    assert park.est_cost_low == 0
    assert park.est_cost_high == 0
    needle = by_name["Space Needle"]
    assert needle.cost_basis == "unknown"
    assert needle.est_cost_low is None
    assert needle.est_cost_high is None


def test_coffee_finds_the_cafes():
    result = search.search_places("coffee")
    assert names(result) == {
        "Storyville Coffee Pike Place",
        "Starbucks Reserve Roastery",
        "Victrola Coffee Roasters",
    }


def test_plural_words_match():
    result = names(search.search_places("parks"))
    assert "Discovery Park" in result
    assert "Canon" not in result


def test_museum_search():
    result = names(search.search_places("museum"))
    assert {"Chihuly Garden and Glass", "Museum of Pop Culture"} <= result
    assert "Terra Plata" not in result


def test_category_filter():
    result = search.search_places(categories=["nightlife"])
    assert names(result) == {"Canon", "Needle & Thread"}


def test_nearby_search_sorts_nearest_first():
    result = search.search_places(near=PIKE_PLACE, radius_min=10, mode="walking")
    assert result[0].name == "Pike Place Market"
    assert "Storyville Coffee Pike Place" in names(result)
    assert "Alki Beach Park" not in names(result)
    assert "Kerry Park" not in names(result)


def test_radius_depends_on_travel_mode():
    walking = names(search.search_places(near=PIKE_PLACE, radius_min=10, mode="walking"))
    driving = names(search.search_places(near=PIKE_PLACE, radius_min=10, mode="driving"))
    assert "Space Needle" not in walking  # about 1.3 km, roughly 16 minutes on foot
    assert "Space Needle" in driving


def test_limit():
    assert len(search.search_places(limit=3)) == 3
    assert len(search.search_places(limit=100)) == 21


def test_no_match_returns_empty_list_not_an_error():
    assert search.search_places("zzzz") == []


def test_results_are_copies():
    first = search.search_places("coffee")[0]
    first.name = "CHANGED"
    assert "CHANGED" not in names(search.search_places("coffee"))


def test_distance_and_rough_minutes():
    space_needle = (47.6205, -122.3493)
    km = distance_km(PIKE_PLACE, *space_needle)
    assert 1.0 < km < 1.6
    assert rough_minutes(5, "walking") == 60


def test_get_place_search_works():
    assert get_place_search().search_places("coffee")


def test_cost_range_must_make_sense():
    with pytest.raises(ValidationError):
        Place(
            id="x", sources=["seed"], name="x", lat=0, lng=0, address="",
            est_cost_low=10, est_cost_high=5, retrieved_at="2026-10-13T00:00:00Z",
        )


def test_impossible_latitude_is_rejected():
    with pytest.raises(ValidationError):
        Place(
            id="x", sources=["seed"], name="x", lat=95, lng=0, address="",
            retrieved_at="2026-10-13T00:00:00Z",
        )
