"""L4: handle one change during the trip (docs/03 section 5.4, SRS section 7).

    checked change (A5) -> apply it to a copy (code) -> L3 repair of only what broke (A6)
    -> compare old and new -> explain (A7) -> version N+1 (version N is kept for Undo)

The current version is never modified. Done and locked activities never change.
The repair loop has its own caps (MAX_REPAIR_ITERATIONS, MAX_REPAIR_LLM_CALLS) and ends
in PASS or INFEASIBLE.
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from time import perf_counter
from typing import Any
from uuid import uuid4

from app.agents.apply_change import apply_change
from app.agents.explainer import explain
from app.agents.planner import repair_until_valid
from app.tools.routes import add_route_legs

logger = logging.getLogger(__name__)


@dataclass
class ReplanResult:
    itinerary: dict[str, Any]
    requirements: dict[str, Any]
    event: dict[str, Any]  # the ReplanEvent (frontend contract)
    terminal: str  # PASS or INFEASIBLE
    explanation: str | None
    timings: dict[str, int] = field(default_factory=dict)  # ms per step, for the trace
    explained_by: str = "rules"
    iterations: int = 0


def diff(before: dict[str, Any], after: dict[str, Any]) -> dict[str, list[str]]:
    """Which activities were replaced, moved, removed, added or kept (by activity id)."""
    def active(plan):
        return {
            a["id"]: a
            for day in plan.get("days", [])
            for a in day["activities"]
            if a.get("status") != "cancelled"
        }

    old, new = active(before), active(after)
    result: dict[str, list[str]] = {
        "changed": [], "moved": [], "preserved": [], "added": [], "removed": []
    }
    for activity_id, was in old.items():
        now = new.get(activity_id)
        if now is None:
            result["removed"].append(activity_id)
        elif now.get("place_id") != was.get("place_id"):
            result["changed"].append(activity_id)
        elif now.get("start") != was.get("start"):
            result["moved"].append(activity_id)
        else:
            result["preserved"].append(activity_id)
    result["added"] = [activity_id for activity_id in new if activity_id not in old]
    return result


def _ms(start: float) -> int:
    return int((perf_counter() - start) * 1000)


def _refresh_legs(
    itinerary: dict[str, Any],
    mode: Any,
    changes: dict[str, list[str]],
    route_legs: Callable[[dict[str, Any], Any], int],
) -> None:
    """Travel times between stops for the new version (stops and the mode may have changed).

    Legs that touch a replaced, moved or added stop are marked changed, for the map. A
    failure only means no route lines; the new version itself is still good.
    """
    try:
        route_legs(itinerary, mode)
    except Exception as error:
        logger.warning("Travel times after the change failed: %s", error)
        for day in itinerary.get("days", []):
            day["legs"] = []
        return
    touched = {*changes["changed"], *changes["moved"], *changes["added"]}
    for day in itinerary.get("days", []):
        for leg in day.get("legs", []):
            leg["changed"] = bool({leg["from_activity_id"], leg["to_activity_id"]} & touched)


def replan(
    *,
    change_type: str,
    payload: dict[str, Any],
    trigger: str,
    trigger_id: str,
    trip_id: str,
    requirements: dict[str, Any],
    itinerary: dict[str, Any],
    places: list[dict[str, Any]],
    versions: list[int],
    choose: Callable[..., Any] | None = None,
    add_backups: Callable[[dict[str, Any], set[str] | None], int] | None = None,
    explain_fn: Callable[..., tuple[str, dict[str, str], str]] = explain,
    route_legs: Callable[[dict[str, Any], Any], int] = add_route_legs,
) -> ReplanResult:
    timings: dict[str, int] = {}
    from_version = itinerary["version"]
    new_version = max([*versions, from_version]) + 1

    started = perf_counter()
    new_requirements, after, touched = apply_change(change_type, payload, requirements, itinerary)
    after["version"] = new_version
    after["repairs"] = []
    after["created_at"] = datetime.now(UTC).isoformat()
    for day in after.get("days", []):
        for activity in day["activities"]:
            activity["version"] = new_version
            if activity["id"] not in touched:  # last change's labels do not carry over
                activity.pop("change_type", None)
                activity.pop("reason", None)
    timings["apply"] = _ms(started)

    # Candidates for replacements: the places found when planning + every stored backup.
    candidates = list(places)
    known = {p.get("id") for p in candidates}
    for day in after.get("days", []):
        for activity in day["activities"]:
            for backup in activity.get("backups") or []:
                place = backup.get("place")
                if place and place.get("id") not in known:
                    candidates.append(place)
                    known.add(place.get("id"))

    started = perf_counter()
    trip = {**new_requirements, "trip_id": trip_id}
    _, iterations, terminal, explanation = repair_until_valid(
        trip, after, candidates, version=new_version, choose=choose, add_backups=add_backups
    )
    if add_backups is not None and change_type == "swap":
        add_backups(after, set(touched))  # the swapped-in place needs its own backups
    timings["repair"] = _ms(started)

    changes = diff(itinerary, after)
    started = perf_counter()
    _refresh_legs(after, new_requirements.get("mode", "walking"), changes, route_legs)
    timings["routes"] = _ms(started)

    started = perf_counter()
    trigger_text, reasons, explained_by = explain_fn(
        trigger, changes, itinerary, after, after["repairs"]
    )
    timings["explain"] = _ms(started)
    for day in after.get("days", []):
        for activity in day["activities"]:
            if activity["id"] in reasons:
                activity["reason"] = reasons[activity["id"]]

    event = {
        "id": str(uuid4()),
        "trip_id": trip_id,
        "from_version": from_version,
        "to_version": new_version,
        "trigger_id": trigger_id,
        "diff": changes,
        "reasons": reasons,
        "iterations": iterations,
        "trigger_text": trigger_text,
    }
    return ReplanResult(
        itinerary=after,
        requirements=new_requirements,
        event=event,
        terminal=terminal,
        explanation=explanation,
        timings=timings,
        explained_by=explained_by,
        iterations=iterations,
    )
