"""Real place search with Geoapify (free plan: 3,000 requests a day, OpenStreetMap data).

It follows the PlaceSearch shape from base.py, so it can replace MockPlaceSearch without
changing any code that uses it. get_place_search() in __init__.py picks which one to use.

Free plan rule: the app must show "Powered by Geoapify" and "© OpenStreetMap contributors".
Geoapify has no ratings, review counts or prices, so those stay None (we never invent them).
"""

from datetime import UTC, datetime
from typing import Any

import httpx

from app.tools.base import LatLng, Mode
from app.tools.mock_places import SPEED_KMH, _words
from app.tools.osm_hours import parse_osm_hours
from app.tools.place import Place

PLACES_URL = "https://api.geoapify.com/v2/places"
TIMEOUT_S = 10
# Our demo city. Used when the caller does not say where to search.
SEATTLE_CENTER = LatLng(lat=47.6062, lng=-122.3321)
DEFAULT_RADIUS_M = 5000
MAX_RADIUS_M = 20000

# Our words (interests, categories) -> Geoapify category names.
CATEGORY_MAP: dict[str, list[str]] = {
    "food": ["catering.restaurant"],
    "restaurant": ["catering.restaurant"],
    "cafe": ["catering.cafe"],
    "coffee": ["catering.cafe"],
    "bakery": ["commercial.food_and_drink.bakery"],
    "nature": ["leisure.park", "natural"],
    "park": ["leisure.park"],
    "culture": ["entertainment.museum", "entertainment.culture"],
    "museum": ["entertainment.museum"],
    "art": ["entertainment.culture.gallery"],
    "shopping": ["commercial.marketplace", "commercial.shopping_mall", "commercial.books"],
    "market": ["commercial.marketplace"],
    "bookstore": ["commercial.books"],
    "nightlife": ["catering.bar", "catering.pub", "adult.nightclub"],
    "bar": ["catering.bar", "catering.pub"],
    "landmark": ["tourism.attraction", "tourism.sights"],
    "viewpoint": ["tourism.attraction.viewpoint"],
}
# Used when the search has no category words ("pike place", or nothing at all).
DEFAULT_CATEGORIES = [
    "tourism.attraction", "tourism.sights", "catering.cafe", "catering.restaurant",
    "leisure.park", "entertainment.museum", "commercial.marketplace",
]

# Geoapify category prefix -> our experience type. A place can match several.
EXPERIENCE_PREFIXES = [
    ("catering.cafe", "cafe"),
    ("catering.bar", "nightlife"),
    ("catering.pub", "nightlife"),
    ("adult.nightclub", "nightlife"),
    ("catering", "food"),
    ("commercial.food_and_drink", "food"),
    ("leisure.park", "nature"),
    ("natural", "nature"),
    ("entertainment.museum", "culture"),
    ("entertainment.culture", "culture"),
    ("commercial", "shopping"),
    ("tourism", "landmark"),
]


def _geoapify_categories(query: str, categories: list[str] | None) -> tuple[list[str], list[str]]:
    """Split the request into Geoapify categories and leftover name words.

    "coffee museum" -> categories for cafes and museums, no name words.
    "pike place"    -> no category words, so default categories and name words ["pike", "place"].
    """
    words = [*_words(query), *(w for c in categories or [] for w in _words(c))]
    wanted: list[str] = []
    for word in words:
        for name in CATEGORY_MAP.get(word, []):
            if name not in wanted:
                wanted.append(name)
    if wanted:
        return wanted, []
    return DEFAULT_CATEGORIES, _words(query)


def _experience_types(geo_categories: list[str]) -> list[str]:
    found: list[str] = []
    for prefix, experience in EXPERIENCE_PREFIXES:
        hit = any(c == prefix or c.startswith(prefix + ".") for c in geo_categories)
        if hit and experience not in found:
            found.append(experience)
    return found


def _short_categories(geo_categories: list[str]) -> list[str]:
    """'catering.cafe.coffee_shop' -> 'coffee_shop'. Keeps each readable name once."""
    names: list[str] = []
    for category in geo_categories:
        name = category.split(".")[-1]
        if name not in names:
            names.append(name)
    return names


def _to_place(feature: dict[str, Any], retrieved_at: str) -> Place | None:
    """Turn one Geoapify result into our Place. Returns None for places with no name."""
    props = feature.get("properties", {})
    name = (props.get("name") or "").strip()
    place_id = props.get("place_id")
    if not name or not place_id or props.get("lat") is None or props.get("lon") is None:
        return None
    geo_categories = props.get("categories", [])
    raw = props.get("datasource", {}).get("raw", {})
    # OpenStreetMap "fee=no" is a real fact that entry is free. Anything else stays unknown.
    free = raw.get("fee") == "no"
    return Place(
        id=f"geoapify:{place_id}",
        sources=["geoapify"],
        provider_ids={"geoapify": place_id},
        name=name,
        categories=_short_categories(geo_categories),
        experience_types=_experience_types(geo_categories),
        lat=props["lat"],
        lng=props["lon"],
        address=props.get("address_line2") or props.get("formatted") or "",
        est_cost_low=0 if free else None,
        est_cost_high=0 if free else None,
        cost_basis="free" if free else "unknown",
        hours=parse_osm_hours(props.get("opening_hours")),
        retrieved_at=retrieved_at,
    )


class PlaceSearchError(RuntimeError):
    """The place provider could not answer. The message is safe to show (no keys in it)."""


class GeoapifyPlaceSearch:
    """Searches real places through the Geoapify Places API."""

    def __init__(self, api_key: str, client: httpx.Client | None = None) -> None:
        self._api_key = api_key
        # Tests pass a fake client; the app uses a normal one.
        self._client = client or httpx.Client(timeout=TIMEOUT_S)

    def search_places(
        self,
        query: str = "",
        near: LatLng | None = None,
        categories: list[str] | None = None,
        radius_min: int | None = None,
        mode: Mode = "walking",
        limit: int = 20,
    ) -> list[Place]:
        center = near or SEATTLE_CENTER
        radius_m = DEFAULT_RADIUS_M
        if radius_min is not None:  # minutes of travel -> metres, using our rough speeds
            radius_m = min(SPEED_KMH[mode] * radius_min / 60 * 1000, MAX_RADIUS_M)
        geo_categories, name_words = _geoapify_categories(query, categories)

        params = {
            "categories": ",".join(geo_categories),
            "filter": f"circle:{center.lng},{center.lat},{int(radius_m)}",
            "bias": f"proximity:{center.lng},{center.lat}",  # nearest first
            # Ask for more when we still have to filter by name ourselves.
            "limit": 100 if name_words else limit,
            "apiKey": self._api_key,
        }
        # Errors go up to the graph, which retries a few times. httpx error messages contain
        # the full URL (with our API key), so we raise a short message of our own instead
        # and drop the original ("from None") so the key never reaches logs or the browser.
        try:
            response = self._client.get(PLACES_URL, params=params)
            response.raise_for_status()
        except httpx.HTTPStatusError as error:
            status = error.response.status_code
            raise PlaceSearchError(f"Geoapify answered with HTTP {status}") from None
        except httpx.HTTPError as error:
            raise PlaceSearchError(f"Geoapify request failed ({type(error).__name__})") from None

        retrieved_at = datetime.now(UTC).isoformat()
        places: list[Place] = []
        for feature in response.json().get("features", []):
            place = _to_place(feature, retrieved_at)
            if place is None:
                continue
            if name_words and not set(name_words) <= set(_words(place.name)):
                continue  # whole words only, like the mock search
            places.append(place)
        return places[:limit]
