"""Route legs between stops. Uses a fake travel function, so no network."""

from app.tools.base import LatLng
from app.tools.routes import add_route_legs
from app.tools.travel_time import TravelTime


def activity(activity_id: str, lat: float | None, lng: float | None, status: str = "planned"):
    return {"id": activity_id, "status": status, "place": {"lat": lat, "lng": lng}}


def plan(*days: list[dict]) -> dict:
    return {"days": [{"day": i + 1, "activities": acts, "legs": []} for i, acts in enumerate(days)]}


def fake_travel(calls: list | None = None, geometry: list[LatLng] | None = None):
    def travel(origin: LatLng, destination: LatLng, mode: str) -> TravelTime:
        if calls is not None:
            calls.append((origin, destination, mode))
        return TravelTime(
            minutes=12.6, mode=mode, source="mapbox", distance_km=1.04, geometry=geometry
        )

    return travel


def test_one_leg_between_each_pair_of_stops():
    itinerary = plan(
        [
            activity("a", 47.60, -122.33),
            activity("b", 47.61, -122.34),
            activity("c", 47.62, -122.35),
        ],
        [activity("d", 47.60, -122.33)],
    )
    count = add_route_legs(itinerary, "transit", travel=fake_travel())
    assert count == 2
    day_one, day_two = itinerary["days"]
    assert [(leg["from_activity_id"], leg["to_activity_id"]) for leg in day_one["legs"]] == [
        ("a", "b"),
        ("b", "c"),
    ]
    assert day_two["legs"] == []  # one stop: nothing to travel between


def test_leg_has_what_the_app_shows():
    itinerary = plan([activity("a", 47.60, -122.33), activity("b", 47.61, -122.34)])
    add_route_legs(itinerary, "walking", travel=fake_travel())
    leg = itinerary["days"][0]["legs"][0]
    assert leg["duration_min"] == 13  # whole minutes
    assert leg["distance_km"] == 1.0
    assert leg["mode"] == "walking"
    assert leg["changed"] is False
    assert leg["source"] == "mapbox"
    # No street path from the provider: a straight line between the two stops.
    assert leg["geometry"] == [{"lat": 47.60, "lng": -122.33}, {"lat": 47.61, "lng": -122.34}]


def test_uses_the_real_street_path_when_there_is_one():
    path = [
        LatLng(lat=47.60, lng=-122.33),
        LatLng(lat=47.605, lng=-122.335),
        LatLng(lat=47.61, lng=-122.34),
    ]
    itinerary = plan([activity("a", 47.60, -122.33), activity("b", 47.61, -122.34)])
    add_route_legs(itinerary, "walking", travel=fake_travel(geometry=path))
    assert len(itinerary["days"][0]["legs"][0]["geometry"]) == 3


def test_never_guesses_a_missing_location():
    calls: list = []
    itinerary = plan([activity("a", 47.60, -122.33), activity("b", None, None)])
    assert add_route_legs(itinerary, "walking", travel=fake_travel(calls)) == 0
    assert calls == []


def test_skips_cancelled_activities():
    itinerary = plan(
        [
            activity("a", 47.60, -122.33),
            activity("x", 47.70, -122.40, status="cancelled"),
            activity("b", 47.61, -122.34),
        ]
    )
    add_route_legs(itinerary, "walking", travel=fake_travel())
    legs = itinerary["days"][0]["legs"]
    assert [(leg["from_activity_id"], leg["to_activity_id"]) for leg in legs] == [("a", "b")]


def test_demo_mode_estimate_gives_a_leg_with_distance(monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "DEMO_MODE", True)
    itinerary = plan([activity("a", 47.6097, -122.3425), activity("b", 47.6205, -122.3493)])
    add_route_legs(itinerary, "walking")
    leg = itinerary["days"][0]["legs"][0]
    assert leg["source"] == "estimate"
    assert 12 <= leg["duration_min"] <= 18
    assert leg["distance_km"] > 1


def test_slow_provider_gets_the_estimate_after_the_time_limit():
    # Seen live: transit for 27 legs took 48 s, most of a 76 s plan.
    import time as clock

    from app.tools.routes import add_route_legs
    from app.tools.travel_time import TravelTime

    def slow(origin, destination, mode):
        clock.sleep(2)
        return TravelTime(minutes=99, mode=mode, source="transitous")

    itinerary = {"days": [{"day": 1, "activities": [
        {"id": "a", "place": {"lat": 40.75, "lng": -73.98}},
        {"id": "b", "place": {"lat": 40.76, "lng": -73.97}},
    ]}]}
    started = clock.perf_counter()

    assert add_route_legs(itinerary, "transit", travel=slow, time_limit_s=0.2) == 1

    assert clock.perf_counter() - started < 1.5  # did not wait for the slow provider
    leg = itinerary["days"][0]["legs"][0]
    assert leg["source"] == "estimate" and leg["duration_min"] < 99
