"""A fake place search that works with no API keys (DEMO_MODE).

It follows the PlaceSearch shape from base.py, so the real Foursquare/Mapbox search can
replace it later without changing any code that uses it.
"""

import math

from app.tools.base import LatLng, Mode
from app.tools.place import Place
from app.tools.seattle_seed import load_seattle_places

# Rough average speeds in km/h. Real travel times will come from Mapbox later.
SPEED_KMH: dict[str, float] = {"walking": 5, "cycling": 15, "transit": 15, "driving": 30}

# A few everyday words mapped to our category names.
_SYNONYMS = {"coffee": "cafe"}


def distance_km(point: LatLng, lat: float, lng: float) -> float:
    """Straight-line distance over the earth's surface (the 'haversine' formula)."""
    earth_radius_km = 6371.0
    lat1, lat2 = math.radians(point.lat), math.radians(lat)
    d_lat = lat2 - lat1
    d_lng = math.radians(lng - point.lng)
    h = math.sin(d_lat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(d_lng / 2) ** 2
    return 2 * earth_radius_km * math.asin(math.sqrt(h))


def rough_minutes(km: float, mode: Mode) -> float:
    """A rough guess of travel time. Only for the mock, not a real route."""
    return km / SPEED_KMH[mode] * 60


def _words(text: str) -> list[str]:
    """Lowercase words, with a trailing 's' removed so 'parks' matches 'park'."""
    cleaned = "".join(ch if ch.isalnum() else " " for ch in text.lower())
    return [w[:-1] if len(w) > 3 and w.endswith("s") else w for w in cleaned.split()]


class MockPlaceSearch:
    """Searches the built-in Seattle seed places."""

    def __init__(self, places: list[Place] | None = None) -> None:
        self._places = places if places is not None else load_seattle_places()

    def search_places(
        self,
        query: str = "",
        near: LatLng | None = None,
        categories: list[str] | None = None,
        radius_min: int | None = None,
        mode: Mode = "walking",
        limit: int = 20,
    ) -> list[Place]:
        query_words = [_SYNONYMS.get(w, w) for w in _words(query)]
        wanted = {w for category in (categories or []) for w in _words(category)}

        found: list[tuple[float, Place]] = []
        for place in self._places:
            labels = _words(" ".join([place.name, *place.categories, *place.experience_types]))
            # Every word the user typed must appear somewhere in the place's name or labels.
            if not all(any(q in label for label in labels) for q in query_words):
                continue
            kinds = set(_words(" ".join([*place.categories, *place.experience_types])))
            if wanted and not (wanted & kinds):
                continue

            distance = 0.0
            if near is not None:
                distance = distance_km(near, place.lat, place.lng)
                if radius_min is not None and rough_minutes(distance, mode) > radius_min:
                    continue
            found.append((distance, place))

        if near is not None:
            found.sort(key=lambda pair: pair[0])  # nearest first
        # Hand back copies so callers cannot accidentally change our stored data.
        return [place.model_copy(deep=True) for _, place in found[:limit]]
