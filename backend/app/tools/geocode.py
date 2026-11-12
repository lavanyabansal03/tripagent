"""Find where a destination is: its coordinates and time zone.

Every place search, backup search and time in the plan depends on this. Before,
the app never looked the city up, so every trip searched around Seattle.

- Live (DEMO_MODE=false and GEOAPIFY_API_KEY set): Geoapify's geocoding API, which
  also returns the city's time zone (for example "Europe/Paris").
- Otherwise, or if Geoapify fails: a small built-in list of known cities.
- Unknown city, or a city outside ALLOWED_COUNTRIES (USA only for now): None, and the
  trip planner asks the traveller to check the name.
"""

from functools import lru_cache
from typing import Literal

import httpx
from pydantic import BaseModel

from app.config import ALLOWED_COUNTRIES, settings

GEOCODE_URL = "https://api.geoapify.com/v1/geocode/search"
TIMEOUT_S = 10


class CityLocation(BaseModel):
    name: str  # what the provider calls it, e.g. "Paris, France"
    lat: float
    lng: float
    timezone: str | None  # IANA name such as "America/New_York"; None if unknown
    source: Literal["geoapify", "builtin"]


# Used in demo mode, without a key, or when Geoapify cannot be reached.
# TripAgent plans US trips for now (ALLOWED_COUNTRIES in config.py), so US cities only.
KNOWN_CITIES: dict[str, tuple[float, float, str]] = {
    "seattle": (47.6062, -122.3321, "America/Los_Angeles"),
    "portland": (45.5152, -122.6784, "America/Los_Angeles"),
    "san francisco": (37.7749, -122.4194, "America/Los_Angeles"),
    "los angeles": (34.0522, -118.2437, "America/Los_Angeles"),
    "san diego": (32.7157, -117.1611, "America/Los_Angeles"),
    "las vegas": (36.1699, -115.1398, "America/Los_Angeles"),
    "phoenix": (33.4484, -112.0740, "America/Phoenix"),
    "denver": (39.7392, -104.9903, "America/Denver"),
    "chicago": (41.8781, -87.6298, "America/Chicago"),
    "austin": (30.2672, -97.7431, "America/Chicago"),
    "san antonio": (29.4241, -98.4936, "America/Chicago"),
    "new york": (40.7128, -74.0060, "America/New_York"),
    "boston": (42.3601, -71.0589, "America/New_York"),
    "washington": (38.9072, -77.0369, "America/New_York"),
    "miami": (25.7617, -80.1918, "America/New_York"),
    "honolulu": (21.3069, -157.8583, "Pacific/Honolulu"),
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
    params = {
        "text": name,
        "format": "json",
        "limit": 1,
        "filter": "countrycode:" + ",".join(ALLOWED_COUNTRIES),  # US trips only for now
        "apiKey": settings.GEOAPIFY_API_KEY,
    }
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
    if best.get("country_code") not in ALLOWED_COUNTRIES:
        return None  # safety net: never plan outside the allowed countries
    if not _names_match(best, name):
        return None  # "Tokyo" -> "Little Tokyo, Los Angeles" is not the place asked for
    return best


def _names_match(result: dict, name: str) -> bool:
    """The place's own name (city, state or county) must be what the traveller typed."""
    wanted = " ".join(name.split(",")[0].lower().split())
    own_names = [
        " ".join(str(result.get(key) or "").lower().split())
        for key in ("city", "name", "state", "county")
    ]
    return any(
        own == wanted or own.startswith(wanted + " ") or wanted.startswith(own + " ")
        for own in own_names
        if own
    )  # "New York City" matches "New York"; "Tokyo" does not match "Little Tokyo"


# A match below this importance (Geoapify's 0-1 score) is a small place; check whether a
# well-known city with that name was meant (San Antonio, Texas vs a Mexican village).
SMALL_PLACE_IMPORTANCE = 0.3
# Answers that can be a trip destination (not a street, building, postcode, ...).
TRIP_PLACE_TYPES = {"city", "state", "county", "region"}
CLEARLY_MORE_IMPORTANT = 0.2


def _importance(result: dict) -> float:
    return float((result.get("rank") or {}).get("importance") or 0)


@lru_cache(maxsize=256)
def _ask_geoapify(name: str) -> CityLocation | None:
    """Look a destination up (cached). None means Geoapify found no such place.

    The best match is used, except:
    - it is a whole state or region and a city with that name exists in the same
      country: "New York" is the state's middle (near Syracuse) but the traveller means
      New York City. "Goa" stays the Indian state (the only city Goa is in the Philippines).
    - it is a small place and a city with that name is clearly more important:
      "San Antonio, Texas" first matches a village called "San Antonio Texas" in Mexico,
      but the traveller means San Antonio, TX.
    """
    best = _search(name, only_cities=False)
    if best is None:
        return None
    if best.get("result_type") not in TRIP_PLACE_TYPES:
        # A street, neighbourhood or building ("Goa Way", "Little Tokyo") is not a trip
        # destination: only a city with that name counts, otherwise "not found".
        return _location(_search(name, only_cities=True), name)
    # States have no importance score, so they only follow the same-country rule.
    is_region = best.get("result_type") in ("state", "county", "region")
    is_small = not is_region and (
        best.get("result_type") != "city" or _importance(best) < SMALL_PLACE_IMPORTANCE
    )
    if is_region or is_small:
        city = _search(name, only_cities=True)
        if city is not None and (city.get("lat"), city.get("lon")) != (best["lat"], best["lon"]):
            same_country = city.get("country_code") == best.get("country_code")
            clearly_bigger = _importance(city) >= _importance(best) + CLEARLY_MORE_IMPORTANT
            if (is_region and same_country) or (is_small and clearly_bigger):
                best = city
    return _location(best, name)


def _location(result: dict | None, name: str) -> CityLocation | None:
    if result is None:
        return None
    return CityLocation(
        name=result.get("formatted") or name,
        lat=result["lat"],
        lng=result["lon"],
        timezone=(result.get("timezone") or {}).get("name"),
        source="geoapify",
    )
