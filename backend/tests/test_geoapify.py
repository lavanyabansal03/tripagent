"""Geoapify adapter tests. No real network: a fake HTTP client replays a recorded answer."""

import json
from pathlib import Path

import httpx
import pytest

from app.config import settings
from app.tools import GeoapifyPlaceSearch, MockPlaceSearch, get_place_search
from app.tools.base import LatLng
from app.tools.geoapify import DEFAULT_CATEGORIES, PlaceSearchError, _to_place

FIXTURE = Path(__file__).parent / "fixtures" / "geoapify" / "seattle_cafes_parks_museums.json"
RECORDED = json.loads(FIXTURE.read_text(encoding="utf-8"))
NOW = "2026-11-10T00:00:00Z"


def fake_client(status: int = 200, body: dict | None = None, seen: list | None = None):
    """An httpx client that never goes online. It remembers each request in `seen`."""

    def handler(request: httpx.Request) -> httpx.Response:
        if seen is not None:
            seen.append(request)
        return httpx.Response(status, json=RECORDED if body is None else body)

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_recorded_answer_becomes_places():
    search = GeoapifyPlaceSearch("test-key", client=fake_client())
    places = search.search_places("coffee")
    assert len(places) == 8
    first = places[0]
    assert first.name == "Howdy Y'all Coffee"
    assert first.sources == ["geoapify"]
    assert first.id.startswith("geoapify:")
    assert "cafe" in first.experience_types and "food" in first.experience_types
    assert first.hours is not None and first.hours[0].day == "monday"
    assert first.retrieved_at  # every place says when we fetched it


def test_never_invents_ratings_or_prices():
    for place in GeoapifyPlaceSearch("k", client=fake_client()).search_places("coffee"):
        assert place.rating is None
        assert place.review_count is None
        assert place.price_level is None
        assert place.cost_basis in ("unknown", "free")


def test_unclear_hours_stay_unknown():
    places = GeoapifyPlaceSearch("k", client=fake_client()).search_places("coffee")
    belle = next(p for p in places if p.name == "Belle Epicurean")  # "Mo-Fr 07:00+"
    assert belle.hours is None


def test_request_uses_our_categories_and_area():
    seen: list[httpx.Request] = []
    search = GeoapifyPlaceSearch("k", client=fake_client(seen=seen))
    near = LatLng(lat=47.6097, lng=-122.3425)
    search.search_places("museums", near=near, radius_min=20, mode="walking", limit=5)
    params = seen[0].url.params
    assert params["categories"] == "entertainment.museum"
    assert params["filter"] == "circle:-122.3425,47.6097,1666"  # 20 min walking ~ 1.7 km
    assert params["limit"] == "5"


def test_words_without_a_category_filter_names():
    seen: list[httpx.Request] = []
    search = GeoapifyPlaceSearch("k", client=fake_client(seen=seen))
    places = search.search_places("retro")
    assert [p.name for p in places] == ["Retro Coffee"]
    assert seen[0].url.params["categories"] == ",".join(DEFAULT_CATEGORIES)


def test_free_only_when_osm_says_fee_no():
    feature = {
        "properties": {
            "name": "Kerry Park", "place_id": "abc", "lat": 47.63, "lon": -122.36,
            "categories": ["leisure.park"], "datasource": {"raw": {"fee": "no"}},
        }
    }
    park = _to_place(feature, NOW)
    assert park.cost_basis == "free" and park.est_cost_low == 0
    assert park.experience_types == ["nature"]


def test_places_without_a_name_are_skipped():
    feature = {"properties": {"place_id": "x", "lat": 47.6, "lon": -122.3, "categories": []}}
    assert _to_place(feature, NOW) is None


def test_errors_never_show_the_api_key():
    search = GeoapifyPlaceSearch("SECRET-KEY-123", client=fake_client(status=429, body={}))
    with pytest.raises(PlaceSearchError) as caught:
        search.search_places("coffee")
    assert "429" in str(caught.value)
    assert "SECRET-KEY-123" not in str(caught.value)
    assert caught.value.__cause__ is None and caught.value.__suppress_context__


def test_get_place_search_picks_geoapify_only_in_live_mode(monkeypatch):
    monkeypatch.setattr(settings, "GEOAPIFY_API_KEY", "k")
    monkeypatch.setattr(settings, "DEMO_MODE", True)
    assert isinstance(get_place_search(), MockPlaceSearch)
    monkeypatch.setattr(settings, "DEMO_MODE", False)
    assert isinstance(get_place_search(), GeoapifyPlaceSearch)
    monkeypatch.setattr(settings, "GEOAPIFY_API_KEY", "")
    assert isinstance(get_place_search(), MockPlaceSearch)  # no key: still works


def test_diet_words_become_a_geoapify_filter():
    seen: list[httpx.Request] = []
    search = GeoapifyPlaceSearch("k", client=fake_client(seen=seen))
    search.search_places("vegetarian restaurant", categories=["restaurant"])
    params = seen[0].url.params
    assert params["categories"] == "catering.restaurant"
    assert params["conditions"] == "vegetarian"
    assert params["limit"] == "20"  # "vegetarian" is a filter, not a name to look for
