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


_geoapify: GeoapifyPlaceSearch | None = None
_geoapify_key = ""


def get_place_search() -> PlaceSearch:
    """Return the place search the app should use.

    Real Geoapify search when DEMO_MODE is false and GEOAPIFY_API_KEY is set.
    Otherwise the built-in Seattle mock, so the app always works with no keys.
    One Geoapify search is kept and reused, so its open connection is reused too
    (opening a new connection for every search made planning slower).
    """
    global _geoapify, _geoapify_key
    if not settings.DEMO_MODE and settings.GEOAPIFY_API_KEY:
        if _geoapify is None or _geoapify_key != settings.GEOAPIFY_API_KEY:
            _geoapify = GeoapifyPlaceSearch(settings.GEOAPIFY_API_KEY)
            _geoapify_key = settings.GEOAPIFY_API_KEY
        return _geoapify
    return MockPlaceSearch()
