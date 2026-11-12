"""Travel time between two places, in minutes.

Real routes when we can:
  walking, cycling, driving -> Mapbox Directions API
  transit                   -> Transitous (a free community transit planner; Mapbox has none)
When DEMO_MODE is on, a key is missing, or the provider fails, we fall back to a rough guess
from straight-line distance. The `source` field always says which one you got.

Example:
    trip = travel_minutes(LatLng(lat=47.6097, lng=-122.3425), LatLng(lat=47.6205, lng=-122.3493))
    trip.minutes      # 16.4
    trip.distance_km  # 1.3
    trip.source       # "mapbox", "transitous" or "estimate"
    trip.geometry     # the street path from Mapbox, else None (draw a straight line)
"""

from typing import Literal

import httpx
from pydantic import BaseModel

from app.config import settings
from app.tools.base import LatLng, Mode
from app.tools.mock_places import distance_km, rough_minutes

MAPBOX_URL = "https://api.mapbox.com/directions/v5/mapbox/{profile}/{coords}"
TRANSITOUS_URL = "https://api.transitous.org/api/v1/plan"
# Transitous blocks generic clients; it asks callers to say who they are.
TRANSITOUS_HEADERS = {
    "User-Agent": "TripAgent-student-project (github.com/lavanyabansal03/tripagent)"
}
TIMEOUT_S = 10

TravelSource = Literal["mapbox", "transitous", "estimate"]


class TravelTime(BaseModel):
    """How long it takes to get from one place to another."""

    minutes: float
    mode: Mode
    source: TravelSource  # "estimate" = straight-line guess, not a real route
    distance_km: float | None = None
    # Points along the real route, when the provider gives them (Mapbox does).
    geometry: list[LatLng] | None = None


def estimate_minutes(origin: LatLng, destination: LatLng, mode: Mode = "walking") -> TravelTime:
    """A rough guess with no API call (straight-line distance at an average speed)."""
    km = distance_km(origin, destination.lat, destination.lng)
    return TravelTime(
        minutes=round(rough_minutes(km, mode), 1),
        mode=mode,
        source="estimate",
        distance_km=round(km, 2),
    )


def _mapbox_route(
    origin: LatLng, destination: LatLng, mode: Mode, client: httpx.Client
) -> TravelTime | None:
    if not settings.MAPBOX_SECRET_TOKEN:
        return None
    coords = f"{origin.lng},{origin.lat};{destination.lng},{destination.lat}"  # Mapbox: lng first
    url = MAPBOX_URL.format(profile=mode, coords=coords)
    response = client.get(
        url,
        params={
            "access_token": settings.MAPBOX_SECRET_TOKEN,
            # A simplified street path comes back in the same call, at no extra cost.
            "overview": "simplified",
            "geometries": "geojson",
        },
    )
    response.raise_for_status()
    routes = response.json().get("routes", [])
    if not routes:
        return None
    route = routes[0]
    points = (route.get("geometry") or {}).get("coordinates") or []
    return TravelTime(
        minutes=round(route["duration"] / 60, 1),  # Mapbox gives seconds and metres
        mode=mode,
        source="mapbox",
        distance_km=round(route["distance"] / 1000, 2) if route.get("distance") else None,
        geometry=[LatLng(lat=lat, lng=lng) for lng, lat in points] or None,
    )


def _transit_route(origin: LatLng, destination: LatLng, client: httpx.Client) -> TravelTime | None:
    response = client.get(
        TRANSITOUS_URL,
        params={
            "fromPlace": f"{origin.lat},{origin.lng}",  # Transitous: lat first
            "toPlace": f"{destination.lat},{destination.lng}",
        },
        headers=TRANSITOUS_HEADERS,
    )
    response.raise_for_status()
    data = response.json()
    # "itineraries" are bus/train trips; "direct" is just walking. Take the fastest.
    options = [*data.get("itineraries", []), *data.get("direct", [])]
    seconds = [option["duration"] for option in options if option.get("duration") is not None]
    if not seconds:
        return None
    km = distance_km(origin, destination.lat, destination.lng)  # Transitous has no total
    return TravelTime(
        minutes=round(min(seconds) / 60, 1),
        mode="transit",
        source="transitous",
        distance_km=round(km, 2),
    )


def travel_minutes(
    origin: LatLng,
    destination: LatLng,
    mode: Mode = "walking",
    *,
    live: bool | None = None,
    client: httpx.Client | None = None,
) -> TravelTime:
    """Minutes from origin to destination by mode. Never raises for provider problems.

    live:   call the real APIs? Defaults to "yes unless DEMO_MODE is on".
    client: tests pass a fake HTTP client here; leave it out in app code.
    """
    if live is None:
        live = not settings.DEMO_MODE
    if not live:
        return estimate_minutes(origin, destination, mode)

    http = client or httpx.Client(timeout=TIMEOUT_S)
    try:
        if mode == "transit":
            result = _transit_route(origin, destination, http)
        else:
            result = _mapbox_route(origin, destination, mode, http)
    except (httpx.HTTPError, KeyError, TypeError, ValueError):
        # Provider down, rate-limited or odd answer: a guess is better than a crash.
        # We do not log the error because its text contains the URL with our Mapbox token.
        result = None
    finally:
        if client is None:
            http.close()

    return result or estimate_minutes(origin, destination, mode)
