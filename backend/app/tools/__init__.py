"""Tools: helpers that look up real places and travel times."""

from app.config import settings
from app.tools.base import LatLng, Mode, PlaceSearch
from app.tools.geoapify import GeoapifyPlaceSearch
from app.tools.mock_places import MockPlaceSearch
from app.tools.place import Place
from app.tools.travel_time import TravelTime, travel_minutes

__all__ = [
    "LatLng", "Mode", "Place", "PlaceSearch", "MockPlaceSearch", "GeoapifyPlaceSearch",
    "TravelTime", "travel_minutes", "get_place_search",
]


def get_place_search() -> PlaceSearch:
    """Return the place search the app should use.

    Real Geoapify search when DEMO_MODE is false and GEOAPIFY_API_KEY is set.
    Otherwise the built-in Seattle mock, so the app always works with no keys.
    """
    if not settings.DEMO_MODE and settings.GEOAPIFY_API_KEY:
        return GeoapifyPlaceSearch(settings.GEOAPIFY_API_KEY)
    return MockPlaceSearch()
