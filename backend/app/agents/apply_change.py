"""Apply one checked change to the trip (plain code, no LLM).

Works on copies: the current version is never modified, so Undo can return to it.
Done and locked activities are never touched (CLAUDE.md). After this, the L3 repair
loop (A6) fixes whatever the change broke.

- time:       move the not-done, not-locked stops of that day later by N minutes
- budget:     set the new budget
- closure:    mark that stop as closed today (repair replaces or removes it)
- transport:  set the new way of getting around
- preference: add things to skip to the avoid list
- swap:       put one of the stop's stored backups in its place
"""

import copy
from datetime import datetime, timedelta
from typing import Any

PROTECTED_STATUSES = {"done", "locked", "cancelled"}


class ChangeError(ValueError):
    """The change cannot be applied (for example an unknown backup)."""


def apply_change(
    change_type: str,
    payload: dict[str, Any],
    requirements: dict[str, Any],
    itinerary: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    """Return (new requirements, new itinerary, ids of activities this change touched)."""
    requirements = copy.deepcopy(requirements)
    itinerary = copy.deepcopy(itinerary)
    touched: list[str] = []

    if change_type == "time":
        minutes = int(payload["minutes"])
        for activity in _day(itinerary, payload.get("day", 1)):
            if activity.get("status") in PROTECTED_STATUSES:
                continue
            for key in ("start", "end"):
                moved = datetime.fromisoformat(activity[key]) + timedelta(minutes=minutes)
                activity[key] = moved.isoformat()
            activity["change_type"] = "moved"
            activity["reason"] = f"You're running {minutes} minutes late."
            touched.append(activity["id"])
    elif change_type == "budget":
        requirements["budget"] = payload["budget"]
    elif change_type == "closure":
        activity = _find(itinerary, payload["activity_id"])
        if activity.get("status") in PROTECTED_STATUSES:
            raise ChangeError("That activity is done or locked.")
        activity["unavailable"] = True
        touched.append(activity["id"])
    elif change_type == "transport":
        requirements["mode"] = payload["mode"]
    elif change_type == "preference":
        avoid = list(requirements.get("avoid") or [])
        known = {a.lower() for a in avoid}
        for item in payload.get("avoid", []):
            if item.lower() not in known:
                avoid.append(item)
                known.add(item.lower())
        requirements["avoid"] = avoid
    elif change_type == "swap":
        activity = _find(itinerary, payload["activity_id"])
        if activity.get("status") in PROTECTED_STATUSES:
            raise ChangeError("That activity is done or locked.")
        backup = next(
            (b for b in activity.get("backups") or [] if b.get("place_id") == payload["backup_id"]),
            None,
        )
        if backup is None or not backup.get("place"):
            raise ChangeError("That backup is not stored for this activity.")
        old_name = activity["place"].get("name")
        place = backup["place"]
        activity.update({
            "place_id": place["id"],
            "place": place,
            "est_cost": place.get("est_cost_low"),
            "cost_basis": place.get("cost_basis", "unknown"),
            "change_type": "replaced",
            "reason": f"You picked {place.get('name')} instead of {old_name}.",
            "backups": [],
        })
        activity.pop("unavailable", None)
        touched.append(activity["id"])
    else:
        raise ChangeError(f"Unsupported change: {change_type}")

    return requirements, itinerary, touched


def _day(itinerary: dict[str, Any], day: int) -> list[dict[str, Any]]:
    for plan_day in itinerary.get("days", []):
        if plan_day.get("day") == day:
            return plan_day["activities"]
    return []


def _find(itinerary: dict[str, Any], activity_id: str) -> dict[str, Any]:
    for plan_day in itinerary.get("days", []):
        for activity in plan_day["activities"]:
            if activity.get("id") == activity_id:
                return activity
    raise ChangeError("Unknown activity.")
