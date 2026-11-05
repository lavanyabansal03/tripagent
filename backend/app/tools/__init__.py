"""Tools: helpers that look up real places and travel times."""

from app.tools.base import LatLng, Mode, PlaceSearch
from app.tools.mock_places import MockPlaceSearch
from app.tools.place import Place

__all__ = ["LatLng", "Mode", "Place", "PlaceSearch", "MockPlaceSearch", "get_place_search"]


def get_place_search() -> PlaceSearch:
    """Return the place search the app should use.

    For now that is always the mock. When the Foursquare and Mapbox adapters exist, this will
    return them if DEMO_MODE is false and the API keys are set.
    """
    return MockPlaceSearch()
