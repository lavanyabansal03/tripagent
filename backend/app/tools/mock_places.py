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


def name_match(asked: str, found: str) -> int:
    """How well a map name fits the name asked for: 0 no, 1 weak, 2 good, 3 exact.

    Whole words only ("The Met" is not "Metropolitan Opera House"); "Joe's" = "Joes".
      3  the same name                       "The Alamo"   / "Alamo"
      2  the map's name is the shorter one   "Katz's Delicatessen" / "Katz's"
      1  the map's name adds words           "The Alamo"   / "Alamo Gift Shop"
    """

    def words(text: str) -> str:
        text = text.replace("'", "").replace("’", "")  # "Joe's" -> "Joes"
        return " ".join(w for w in _words(text) if w != "the")

    a, b = words(asked), words(found)
    if not a or not b:
        return 0
    if a == b:
        return 3
    if f" {b} " in f" {a} ":
        return 2
    return 1 if f" {a} " in f" {b} " else 0


# A weak match (the map's name adds words) is often a different place: "The Alamo Gift
# Shop", "Museum of Modern Art (MoMA) films". Seen live, so only good matches count.
GOOD_NAME_MATCH = 2


def same_name(asked: str, found: str) -> bool:
    """Is `found` (a map name) the place that was asked for? See name_match."""
    return name_match(asked, found) >= GOOD_NAME_MATCH


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

    def find_by_name(self, name: str, near: LatLng, area: str = "") -> Place | None:
        """The seed place that best fits the name ("Space Needle"), or None. Same rule as live."""
        scored = [(name_match(name, place.name), place) for place in self._places]
        best_score, best = max(scored, key=lambda pair: pair[0], default=(0, None))
        if best is None or best_score < GOOD_NAME_MATCH:
            return None
        return best.model_copy(deep=True)
