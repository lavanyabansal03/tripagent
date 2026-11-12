"""Discovery agent: find enough candidate places for a trip, one interest at a time.

This is a bounded tool loop. An LLM may translate each interest into search words
first (app/agents/discovery_plan.py); code checks the words and runs every search.
  1. One focused search per interest: with the LLM's search words ("hiking" -> nature,
     park) when it gave usable ones, else the interest itself ("museum").
  2. For interests that came back with too few places, one wider search (any category).
  3. Merge duplicates (same id, or a very similar name less than 50 m away).
It stops at a hard cap of search calls (MAX_DISCOVERY_CALLS in config.py) and always ends
in a named state:
  PASS        every interest has at least MIN_PER_INTEREST places
  INFEASIBLE  we stopped (cap reached or nothing new found) with some interests short
  ERROR       every search call failed
"""

import logging
from collections.abc import Callable
from difflib import SequenceMatcher
from typing import Any, Literal

from pydantic import BaseModel

from app.config import MAX_DISCOVERY_CALLS
from app.tools import PlaceSearch, get_place_search
from app.tools.base import LatLng
from app.tools.mock_places import distance_km
from app.tools.parallel import run_all
from app.tools.place import Place

logger = logging.getLogger(__name__)

MIN_PER_INTEREST = 3
SAME_NAME_SIMILARITY = 0.85
SAME_PLACE_KM = 0.05  # 50 metres
# Exactly the same name this close is one place listed twice (a park and its playground).
SAME_NAME_KM = 1.0
RESULTS_PER_SEARCH = 10
RESULTS_FOR_ANYTHING = 30  # a search with no interest returns a bigger mix


class DiscoveryResult(BaseModel):
    status: Literal["PASS", "INFEASIBLE", "ERROR"]
    places: list[Place]
    coverage: dict[str, int]  # interest -> how many places we found for it
    calls_used: int
    reason: str
    search_words: dict[str, list[str]] = {}  # interest -> words the LLM chose (empty: none)


def _same_place(a: Place, b: Place) -> bool:
    """Same id; nearly the same name within 50 m; or exactly the same name within 1 km."""
    if a.id == b.id:
        return True
    km = distance_km(LatLng(lat=a.lat, lng=a.lng), b.lat, b.lng)
    if " ".join(a.name.lower().split()) == " ".join(b.name.lower().split()) and km < SAME_NAME_KM:
        return True
    similarity = SequenceMatcher(None, a.name.lower(), b.name.lower()).ratio()
    return similarity >= SAME_NAME_SIMILARITY and km < SAME_PLACE_KM


def _add(found: list[Place], place: Place) -> tuple[Place, bool]:
    """Add a place unless we already have it. Returns (the kept place, was it new?)."""
    for kept in found:
        if _same_place(kept, place):
            # Keep the first copy, but remember every provider that listed it.
            for source in place.sources:
                if source not in kept.sources:
                    kept.sources.append(source)
            kept.provider_ids.update(place.provider_ids)
            return kept, False
    found.append(place)
    return place, True


def _mix(per_interest: dict[str, list[str]], found: list[Place]) -> list[Place]:
    """Order places by taking turns between interests, so the first few are varied.

    The planner uses the first places in the list, so "museum, cafe, park, museum, ..."
    gives a better day than "museum, museum, museum, ...".
    """
    by_id = {place.id: place for place in found}
    queues = [list(ids) for ids in per_interest.values()]
    ordered: list[str] = []
    while any(queues):
        for queue in queues:
            if queue:
                place_id = queue.pop(0)
                if place_id not in ordered:
                    ordered.append(place_id)
    ordered += [place.id for place in found if place.id not in ordered]
    return [by_id[place_id] for place_id in ordered]


def famous_first(famous: list[Place], others: list[Place]) -> list[Place]:
    """Famous places first, then the rest; a place found both ways is kept once.

    The planner uses the first places in the list, so the famous ones get into the plan.
    """
    found: list[Place] = []
    for place in [*famous, *others]:
        _add(found, place)
    return found


def discover_places(
    trip: dict[str, Any],
    search: PlaceSearch | None = None,
    max_calls: int = MAX_DISCOVERY_CALLS,
    plan: Callable[[dict[str, Any], list[str]], dict[str, list[str]]] | None = None,
    near: LatLng | None = None,
) -> DiscoveryResult:
    """Find candidate places for the trip's interests within a fixed number of searches.

    `plan` (an LLM) may give search words per interest; it never adds a search call.
    """
    search = search or get_place_search()
    mode = trip.get("mode", "walking")
    interests = [str(i).strip() for i in trip.get("interests", []) if str(i).strip()]
    if not interests:
        interests = [""]  # no interests given: one search for anything good nearby
    search_words: dict[str, list[str]] = {}
    if plan is not None and interests != [""]:
        try:
            search_words = plan(trip, interests) or {}
        except Exception as error:  # no plan: search the interests as written
            logger.warning("Search plan failed (%s); searching the interests as written", error)
            search_words = {}

    found: list[Place] = []
    per_interest: dict[str, list[str]] = {interest: [] for interest in interests}
    calls = failures = 0
    hit_cap = False

    # Step 1 is a focused search for every interest; step 2 a wider one for those still short.
    # The searches of one step run at the same time; their results are used in order.
    def focused(interest: str) -> Callable[[], list[Place]]:
        if search_words.get(interest):
            return lambda: search.search_places(
                near=near, query="", categories=search_words[interest], mode=mode,
                limit=RESULTS_PER_SEARCH,
            )
        return lambda: search.search_places(
            near=near, query=interest, categories=[interest] if interest else None, mode=mode,
            limit=RESULTS_PER_SEARCH if interest else RESULTS_FOR_ANYTHING,
        )

    def wide(interest: str) -> Callable[[], list[Place]]:
        return lambda: search.search_places(
            near=near, query=interest, mode=mode, limit=RESULTS_PER_SEARCH * 2
        )

    for step in ("focused", "wide"):
        batch: list[str] = []
        for interest in interests:
            if len(per_interest[interest]) >= MIN_PER_INTEREST:
                continue
            if step == "wide" and not interest:
                continue  # "anything" was already as wide as it gets
            if calls >= max_calls:
                hit_cap = True
                break
            calls += 1
            batch.append(interest)
        make = focused if step == "focused" else wide
        for interest, results in zip(batch, run_all([make(i) for i in batch]), strict=True):
            if isinstance(results, Exception):  # one failed call should not end the search
                failures += 1
                continue
            for result in results:
                kept, _ = _add(found, result)
                if kept.id not in per_interest[interest]:
                    per_interest[interest].append(kept.id)

    # Nothing matched any interest: one last search for anything, so the plan is not empty.
    if not found and interests != [""] and calls < max_calls:
        calls += 1
        try:
            for result in search.search_places(near=near, mode=mode, limit=RESULTS_FOR_ANYTHING):
                _add(found, result)
        except Exception as error:
            logger.warning("Last-resort place search failed: %s", error)
            failures += 1

    coverage = {interest: len(ids) for interest, ids in per_interest.items()}
    short = [interest or "anything" for interest, n in coverage.items() if n < MIN_PER_INTEREST]

    if calls and failures == calls:
        status, reason = "ERROR", f"All {calls} place searches failed."
    elif not short:
        status, reason = "PASS", f"Found at least {MIN_PER_INTEREST} places for every interest."
    else:
        why = f"hit the limit of {max_calls} searches" if hit_cap else "no more places were found"
        status, reason = "INFEASIBLE", f"Stopped ({why}); too few places for: {', '.join(short)}."

    return DiscoveryResult(
        status=status,
        places=_mix(per_interest, found),
        coverage=coverage,
        calls_used=calls,
        reason=reason,
        search_words=search_words,
    )
