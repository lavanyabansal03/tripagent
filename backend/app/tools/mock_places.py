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

# Everyday words and phrases mapped to our category names. Longer phrases first, so
# "coffee shop" is found before "coffee".
_SYNONYMS = {"coffee shop": "cafe", "book store": "bookstore", "coffee": "cafe"}


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


def _query_terms(query: str) -> list[set[str]]:
    """Split what the user typed into terms. A place matches a term if it has any word in it.

    "coffee shop" becomes one term {"cafe"}, so a cafe matches even without the word "shop".
    "coffee" becomes {"cafe", "coffee"}, so "Victrola Coffee" matches by name or by category.
    """
    words = _words(query)
    terms: list[set[str]] = []
    i = 0
    while i < len(words):
        for phrase, category in _SYNONYMS.items():
            phrase_words = phrase.split()
            if words[i : i + len(phrase_words)] == phrase_words:
                terms.append({category} if len(phrase_words) > 1 else {category, phrase})
                i += len(phrase_words)
                break
        else:  # not a known phrase: the word itself must appear
            terms.append({words[i]})
            i += 1
    return terms


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
        terms = _query_terms(query)
        wanted = {w for category in (categories or []) for w in _words(category)}

        found: list[tuple[float, Place]] = []
        for place in self._places:
            labels = set(_words(" ".join([place.name, *place.categories, *place.experience_types])))
            # Whole words only: "bar" must not match "Barnes & Noble".
            if not all(term & labels for term in terms):
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
