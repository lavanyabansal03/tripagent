"""A6 Repair, LLM part: pick the best of the replacements that code already checked.

Code finds which places are valid (open, not on the avoid list, reachable in
time, within budget). The LLM only chooses among those and says why in one
sentence, so it cannot invent a place or break a rule. If it gives no valid
answer, Repair uses code's first choice (see app/agents/repair.py).
"""

from typing import Any

from pydantic import BaseModel, Field

from app.agents.llm import ask_json
from app.tools.base import LatLng
from app.tools.mock_places import distance_km, rough_minutes


class RepairChoice(BaseModel):
    choice: int = Field(description="The number of the chosen option, starting at 1.")
    reason: str = Field(
        description="One short sentence for the traveller, using only the facts given."
    )


def _option_line(number: int, original: dict[str, Any], place: dict[str, Any], mode: str) -> str:
    minutes = "unknown"
    if all(p.get(k) is not None for p in (original, place) for k in ("lat", "lng")):
        start = LatLng(lat=original["lat"], lng=original["lng"])
        km = distance_km(start, place["lat"], place["lng"])
        minutes = f"{round(rough_minutes(km, mode))} min {mode} from the original stop"
    cost = place.get("est_cost_low")
    types = ", ".join(place.get("experience_types") or []) or "unknown"
    categories = ", ".join((place.get("categories") or [])[:4]) or "unknown"
    return (
        f"{number}. {place.get('name')} | types: {types}"
        f" | categories: {categories}"
        f" | {minutes}"
        f" | opening hours: {'listed and checked' if place.get('hours') else 'not listed'}"
        f" | cost: {'unknown' if cost is None else f'${cost}'}"
    )


def build_prompt(
    trip: dict[str, Any], activity: dict[str, Any], options: list[dict[str, Any]], problem: str
) -> str:
    mode = trip.get("mode", "walking")
    original = activity.get("place") or {}
    slot = f"{activity.get('start', '')[11:16]}-{activity.get('end', '')[11:16]}"
    purpose = ", ".join(activity.get("purpose_tags") or [])
    lines = "\n".join(
        _option_line(number, original, place, mode)
        for number, place in enumerate(options, 1)
    )
    return f"""You help repair one stop in a travel plan.

The traveller likes: {", ".join(trip.get("interests") or []) or "not stated"}.
The traveller wants to avoid: {", ".join(trip.get("avoid") or []) or "nothing stated"}.
Their note: {trip.get("free_text") or "none"}

The stop "{original.get("name")}" ({purpose}) at {slot} must be replaced.
Problem: {problem}

Every option below has already been checked: it is open (or its hours are not listed),
not on the avoid list, and reachable in time. Choose the one that best keeps the purpose
of the stop and fits what this traveller likes. Prefer options whose opening hours are
listed. Prefer shorter detours when options are otherwise similar.

{lines}

Answer with the option number and one short sentence for the traveller explaining the
choice. Use only the facts above; do not invent prices, hours, ratings or descriptions."""


def choose_with_llm(
    trip: dict[str, Any], activity: dict[str, Any], options: list[dict[str, Any]], problem: str
) -> tuple[int, str] | None:
    """Return (index into options, reason), or None so Repair falls back to code's choice."""
    answer = ask_json(build_prompt(trip, activity, options, problem), RepairChoice)
    if answer is None:
        return None
    index = answer.choice - 1
    if not 0 <= index < len(options):
        return None  # an option that does not exist: ignore the answer
    return index, answer.reason
