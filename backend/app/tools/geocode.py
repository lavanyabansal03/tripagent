"""Find where a destination is: its coordinates and time zone.

Every place search, backup search and time in the plan depends on this. Before,
the app never looked the city up, so every trip searched around Seattle.

- Live (DEMO_MODE=false and GEOAPIFY_API_KEY set): Geoapify's geocoding API, which
  also returns the city's time zone (for example "Europe/Paris").
- Otherwise, or if Geoapify fails: a small built-in list of known cities.
- Unknown city: None, and the trip planner asks the traveller to check the name.
"""

from functools import lru_cache
from typing import Literal

import httpx
from pydantic import BaseModel

from app.config import settings

GEOCODE_URL = "https://api.geoapify.com/v1/geocode/search"
TIMEOUT_S = 10


class CityLocation(BaseModel):
    name: str  # what the provider calls it, e.g. "Paris, France"
    lat: float
    lng: float
    timezone: str | None  # IANA name such as "America/New_York"; None if unknown
    source: Literal["geoapify", "builtin"]


# Used in demo mode, without a key, or when Geoapify cannot be reached.
KNOWN_CITIES: dict[str, tuple[float, float, str]] = {
    "seattle": (47.6062, -122.3321, "America/Los_Angeles"),
    "portland": (45.5152, -122.6784, "America/Los_Angeles"),
    "san francisco": (37.7749, -122.4194, "America/Los_Angeles"),
    "los angeles": (34.0522, -118.2437, "America/Los_Angeles"),
    "vancouver": (49.2827, -123.1207, "America/Vancouver"),
    "new york": (40.7128, -74.0060, "America/New_York"),
    "boston": (42.3601, -71.0589, "America/New_York"),
    "chicago": (41.8781, -87.6298, "America/Chicago"),
    "denver": (39.7392, -104.9903, "America/Denver"),
    "phoenix": (33.4484, -112.0740, "America/Phoenix"),
    "honolulu": (21.3069, -157.8583, "Pacific/Honolulu"),
    "london": (51.5074, -0.1278, "Europe/London"),
    "lisbon": (38.7223, -9.1393, "Europe/Lisbon"),
    "paris": (48.8566, 2.3522, "Europe/Paris"),
    "rome": (41.9028, 12.4964, "Europe/Rome"),
    "oslo": (59.9139, 10.7522, "Europe/Oslo"),
    "tokyo": (35.6762, 139.6503, "Asia/Tokyo"),
    "sydney": (-33.8688, 151.2093, "Australia/Sydney"),
}


class GeocodeError(Exception):
    """Geoapify could not be reached or answered with an error."""


def locate_city(destination: str) -> CityLocation | None:
    """Coordinates and time zone of a destination, or None if we cannot find it."""
    name = " ".join(destination.split())
    if not name:
        return None
    if settings.GEOAPIFY_API_KEY and not settings.DEMO_MODE:
        try:
            return _ask_geoapify(name.lower())
        except GeocodeError:
            pass  # provider down: try the built-in list below
    return _builtin(name)


def _builtin(name: str) -> CityLocation | None:
    lowered = name.lower()
    for city, (lat, lng, timezone) in KNOWN_CITIES.items():
        if city == lowered or lowered.startswith(city + ",") or lowered.startswith(city + " "):
            return CityLocation(
                name=city.title(), lat=lat, lng=lng, timezone=timezone, source="builtin"
            )
    return None


def _search(name: str, only_cities: bool) -> dict | None:
    """Geoapify's best match for `name`, or None."""
    params = {"text": name, "format": "json", "limit": 1, "apiKey": settings.GEOAPIFY_API_KEY}
    if only_cities:
        params["type"] = "city"
    # httpx error messages contain the full URL with our key, so we raise our own
    # short message instead and drop the original ("from None").
    try:
        response = httpx.get(GEOCODE_URL, params=params, timeout=TIMEOUT_S)
        response.raise_for_status()
    except httpx.HTTPStatusError as error:
        raise GeocodeError(f"Geoapify geocoding answered {error.response.status_code}") from None
    except httpx.HTTPError as error:
        raise GeocodeError(f"Geoapify geocoding failed ({type(error).__name__})") from None
    results = response.json().get("results") or []
    best = results[0] if results else None
    if best is None or best.get("lat") is None or best.get("lon") is None:
        return None
    return best


@lru_cache(maxsize=256)
def _ask_geoapify(name: str) -> CityLocation | None:
    """Look a destination up (cached). None means Geoapify found no such place.

    The best match is used, except when it is a whole state or region and a city with
    that name exists in the same country: "New York" is the state's middle (near
    Syracuse) but the traveller means New York City. "Goa" stays the Indian state,
    because the only city called Goa is in the Philippines.
    """
    best = _search(name, only_cities=False)
    if best is None:
        return None
    if best.get("result_type") in ("state", "county", "region"):
        city = _search(name, only_cities=True)
        if city is not None and city.get("country_code") == best.get("country_code"):
            best = city
    return CityLocation(
        name=best.get("formatted") or name,
        lat=best["lat"],
        lng=best["lon"],
        timezone=(best.get("timezone") or {}).get("name"),
        source="geoapify",
    )
