"""A2 Discovery, famous places: the well-known sights and food spots of the city.

The place search has no ratings or popularity (OpenStreetMap data), and it returns
the places nearest the city centre, so a plan was full of places nobody had heard of.
Here the LLM names the places a visitor would know ("Times Square", "The Met",
"Joe's Pizza"); code looks every name up on the map and keeps only the ones it really
finds there, with the provider's own data. A name the map does not know is dropped,
so nothing is invented. Found places are marked local_signal="tourist".

How many: the "Famous sights / Local favourites" slider (tourist_local_ratio, 0-100 =
share of local favourites) decides the share of the trip's stops, capped by
MAX_FAMOUS_PLACES.
"""

from datetime import date
from typing import Any

from pydantic import BaseModel, Field

from app.agents.llm import ask_json
from app.config import MAX_FAMOUS_PLACES, STOPS_PER_DAY
from app.tools.base import LatLng
from app.tools.parallel import run_all
from app.tools.place import Place

MAX_NAME_CHARS = 80


class FamousPlace(BaseModel):
    name: str = Field(description="The place's full name, e.g. 'The Museum of Modern Art'.")
    short_name: str = Field(default="", description="A common short name, e.g. 'MoMA', or ''.")


class FamousNames(BaseModel):
    places: list[FamousPlace]


def how_many(trip: dict[str, Any]) -> int:
    """Famous places wanted: the slider's share of all the trip's stops, capped."""
    try:
        start, end = date.fromisoformat(trip["start_date"]), date.fromisoformat(trip["end_date"])
        days = (end - start).days + 1
    except (KeyError, TypeError, ValueError):
        days = 1
    stops = max(1, days) * STOPS_PER_DAY.get(str(trip.get("pace")), STOPS_PER_DAY["moderate"])
    local_share = float(trip.get("tourist_local_ratio", 50)) / 100
    return max(0, min(MAX_FAMOUS_PLACES, round(stops * (1 - local_share))))


def build_prompt(trip: dict[str, Any], count: int) -> str:
    city = trip.get("location_name") or trip.get("destination") or "the city"
    return f"""Name {count} famous, well-known places in {city} that a visitor would love.

Interests: {", ".join(trip.get("interests") or []) or "anything"}
Things to avoid: {", ".join(trip.get("avoid") or []) or "nothing stated"}
Traveller's note: {trip.get("free_text") or "none"}

Rules:
- Real places that exist today, in or near {city}, each with its exact name as it
  appears on a map ("The Metropolitan Museum of Art", "Joe's Pizza", "Central Park"),
  plus its common short name when people use one ("The Met", "MoMA"), else "".
- Mix sights, museums, parks and famous food spots, matching the interests.
- Nothing from the "avoid" list. No hotels, no chains found everywhere, no whole
  neighbourhoods or streets."""


def _clean(text: str) -> str:
    name = " ".join(str(text).split())
    return name if len(name) <= MAX_NAME_CHARS else ""


def suggest_names(trip: dict[str, Any], count: int) -> list[tuple[str, str]]:
    """The LLM's (name, short name) pairs, cleaned: no blanks or repeats, at most `count`."""
    if count <= 0:
        return []
    answer = ask_json(build_prompt(trip, count), FamousNames)
    if answer is None:
        return []
    names: list[tuple[str, str]] = []
    for item in answer.places:
        name, short = _clean(item.name), _clean(item.short_name)
        if name and name.lower() not in {n.lower() for n, _ in names}:
            names.append((name, short if short.lower() != name.lower() else ""))
    return names[:count]


def _look_up(find: Any, name: str, short: str, near: LatLng, area: str) -> Place | None:
    """The full name first; the short name ("MoMA") only when the full one is not found."""
    return find(name, near, area) or (find(short, near, area) if short else None)


def _avoided(place: Place, avoid: list[str]) -> bool:
    labels = {label.lower() for label in [*place.categories, *place.experience_types]}
    return any(item.lower().strip() in labels for item in avoid if item.strip())


def find_famous(
    trip: dict[str, Any], search: Any, near: LatLng
) -> tuple[list[Place], list[str]]:
    """(famous places found on the map, the names the LLM gave). Never raises."""
    find = getattr(search, "find_by_name", None)
    if find is None:
        return [], []
    names = suggest_names(trip, how_many(trip))
    area = str(trip.get("location_name") or trip.get("destination") or "")
    results = run_all([
        lambda n=name, s=short: _look_up(find, n, s, near, area) for name, short in names
    ])
    places: list[Place] = []
    for result in results:
        if not isinstance(result, Place) or _avoided(result, trip.get("avoid") or []):
            continue  # not on the map, a failed lookup, or something the traveller avoids
        if any(result.id == kept.id for kept in places):
            continue
        result.local_signal = "tourist"
        result.field_provenance["local_signal"] = "inferred"
        if not result.experience_types:
            result.experience_types = ["landmark"]  # a famous sight with no map category
        places.append(result)
    return places, [name for name, _ in names]
