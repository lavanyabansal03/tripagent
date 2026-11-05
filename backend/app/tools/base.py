"""The shape every place-search tool must have (the real ones and the mock)."""

from typing import Literal, Protocol

from pydantic import BaseModel, Field

from app.tools.place import Place

Mode = Literal["walking", "transit", "driving", "cycling"]


class LatLng(BaseModel):
    """A point on the map."""

    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)


class PlaceSearch(Protocol):
    """Anything with a search_places method like this counts as a place search."""

    def search_places(
        self,
        query: str = "",
        near: LatLng | None = None,
        categories: list[str] | None = None,
        radius_min: int | None = None,
        mode: Mode = "walking",
        limit: int = 20,
    ) -> list[Place]:
        """Find places.

        query:      words to look for ("coffee", "museum"). Empty means everything.
        near:       a map point; results are sorted nearest first.
        categories: only keep places of these kinds (for example ["nature"]).
        radius_min: only keep places within this many minutes of `near` by `mode`.
        limit:      the most places to return.
        """
        ...
