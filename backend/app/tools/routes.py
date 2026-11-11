"""Route legs: the trip from each activity to the next one on the same day.

The planner leaves `legs` empty. Once the plan is final (after repairs), add_route_legs()
fills them in, so the app can show "18 min transit · 1.3 km" between stops and draw the
route on the map. Times come from travel_minutes(): real providers in live mode, a rough
estimate in DEMO_MODE or when a provider fails. Each leg says which one in `source`.
"""

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from app.tools.base import LatLng, Mode
from app.tools.travel_time import TravelTime, travel_minutes

# A few legs at a time keeps planning fast without hammering the free providers.
MAX_PARALLEL_CALLS = 4

Travel = Callable[[LatLng, LatLng, Mode], TravelTime]


def _point(activity: dict[str, Any]) -> LatLng | None:
    place = activity.get("place") or {}
    if place.get("lat") is None or place.get("lng") is None:
        return None
    return LatLng(lat=place["lat"], lng=place["lng"])


def _leg(first: dict[str, Any], second: dict[str, Any], mode: Mode, time: TravelTime) -> dict:
    start, end = _point(first), _point(second)
    # Without a real street path we draw a straight line between the two stops.
    path = time.geometry or [start, end]
    return {
        "from_activity_id": first["id"],
        "to_activity_id": second["id"],
        "mode": mode,
        "duration_min": max(1, round(time.minutes)),
        "distance_km": round(time.distance_km, 1) if time.distance_km is not None else 0,
        "geometry": [{"lat": p.lat, "lng": p.lng} for p in path],
        "changed": False,
        "source": time.source,
    }


def add_route_legs(
    itinerary: dict[str, Any], mode: Mode = "walking", travel: Travel = travel_minutes
) -> int:
    """Fill every day's `legs` in place and return how many legs were added.

    Pairs where a place has no map position are skipped (we never guess a location).
    """
    pairs: list[tuple[dict, dict, dict]] = []  # (day, first activity, next activity)
    for day in itinerary.get("days", []):
        day["legs"] = []
        activities = [a for a in day.get("activities", []) if a.get("status") != "cancelled"]
        for first, second in zip(activities, activities[1:]):
            if _point(first) is not None and _point(second) is not None:
                pairs.append((day, first, second))

    def measure(pair: tuple[dict, dict, dict]) -> TravelTime:
        _, first, second = pair
        return travel(_point(first), _point(second), mode)

    with ThreadPoolExecutor(max_workers=MAX_PARALLEL_CALLS) as pool:
        times = list(pool.map(measure, pairs))  # same order as `pairs`

    for (day, first, second), time in zip(pairs, times):
        day["legs"].append(_leg(first, second, mode, time))
    return len(pairs)
