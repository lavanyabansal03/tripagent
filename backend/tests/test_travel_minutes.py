"""Travel-time tool tests. No real network: fake HTTP clients replay recorded answers."""

import json
from pathlib import Path

import httpx

from app.config import settings
from app.tools import travel_minutes
from app.tools.base import LatLng

FIXTURES = Path(__file__).parent / "fixtures"
MAPBOX_WALK = json.loads((FIXTURES / "mapbox" / "directions_walking.json").read_text())
TRANSIT = json.loads((FIXTURES / "transitous" / "plan_trimmed.json").read_text())
PIKE_PLACE = LatLng(lat=47.6097, lng=-122.3425)
SPACE_NEEDLE = LatLng(lat=47.6205, lng=-122.3493)


def fake_client(status: int = 200, body: dict | None = None, seen: list | None = None):
    def handler(request: httpx.Request) -> httpx.Response:
        if seen is not None:
            seen.append(request)
        return httpx.Response(status, json=body or {})

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_demo_mode_uses_the_estimate(monkeypatch):
    monkeypatch.setattr(settings, "DEMO_MODE", True)
    result = travel_minutes(PIKE_PLACE, SPACE_NEEDLE, "walking")
    assert result.source == "estimate"
    assert 12 < result.minutes < 18  # about 1.3 km at 5 km/h


def test_walking_uses_mapbox(monkeypatch):
    monkeypatch.setattr(settings, "MAPBOX_SECRET_TOKEN", "test-token")
    seen: list[httpx.Request] = []
    client = fake_client(body=MAPBOX_WALK, seen=seen)
    result = travel_minutes(PIKE_PLACE, SPACE_NEEDLE, "walking", live=True, client=client)
    assert result.source == "mapbox"
    assert result.minutes == 20.9  # 1251.8 seconds in the recorded answer
    assert "/mapbox/walking/-122.3425,47.6097;-122.3493,47.6205" in seen[0].url.path


def test_transit_uses_transitous_and_takes_the_fastest():
    seen: list[httpx.Request] = []
    client = fake_client(body=TRANSIT, seen=seen)
    result = travel_minutes(PIKE_PLACE, SPACE_NEEDLE, "transit", live=True, client=client)
    assert result.source == "transitous"
    assert result.minutes == 18.0  # fastest recorded trip: 1080 seconds
    assert seen[0].headers["User-Agent"].startswith("TripAgent")
    assert seen[0].url.params["fromPlace"] == "47.6097,-122.3425"  # lat first for Transitous


def test_provider_error_falls_back_to_estimate(monkeypatch):
    monkeypatch.setattr(settings, "MAPBOX_SECRET_TOKEN", "test-token")
    client = fake_client(status=429)
    result = travel_minutes(PIKE_PLACE, SPACE_NEEDLE, "driving", live=True, client=client)
    assert result.source == "estimate"


def test_no_mapbox_token_falls_back_without_calling(monkeypatch):
    monkeypatch.setattr(settings, "MAPBOX_SECRET_TOKEN", "")
    seen: list[httpx.Request] = []
    result = travel_minutes(
        PIKE_PLACE, SPACE_NEEDLE, "cycling", live=True, client=fake_client(seen=seen)
    )
    assert result.source == "estimate"
    assert seen == []


def test_empty_answers_fall_back():
    client = fake_client(body={"itineraries": [], "direct": []})
    result = travel_minutes(PIKE_PLACE, SPACE_NEEDLE, "transit", live=True, client=client)
    assert result.source == "estimate"


def test_same_place_is_zero_minutes(monkeypatch):
    monkeypatch.setattr(settings, "DEMO_MODE", True)
    assert travel_minutes(PIKE_PLACE, PIKE_PLACE).minutes == 0
