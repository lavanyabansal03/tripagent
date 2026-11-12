"""Backup Agent (A4): find alternatives for important activities.

For every high or medium priority activity (FR-41), find up to two nearby
places with the same purpose that pass the checks we can run. A check that
cannot run because the data is missing (hours or price not listed) does not
reject the place: the backup is kept, ranked after fully checked ones, and the
missing pieces are listed in its `unknown` field. We never invent hours or
prices. Backups are checked again before use (FR-44).
"""

from datetime import UTC, datetime
from typing import Any

from app.config import BACKUPS_PER_ACTIVITY, MAX_BACKUP_SEARCHES
from app.tools import get_place_search
from app.tools.base import LatLng
from app.tools.mock_places import distance_km, rough_minutes
from app.tools.parallel import run_all
from app.validation.avoid import check_avoid_list
from app.validation.budget import check_budget
from app.validation.opening_hours import check_opening_hours
from app.validation.travel_time import check_travel_time

IMPORTANT_PRIORITIES = {"high", "medium"}
SKIPPED_STATUSES = {"cancelled", "done"}


def _as_dict(value: Any) -> dict:
    if isinstance(value, dict):
        return value.copy()
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    return {}


def _get_preferences(plan: dict) -> dict:
    preferences = plan.get("requirements")

    if preferences is None:
        preferences = plan.get("trip", plan)

    return _as_dict(preferences)


def _get_activities(plan: dict) -> list[dict]:
    if "days" in plan:
        return [
            _as_dict(activity)
            for day in plan["days"]
            for activity in day.get("activities", [])
        ]

    return [
        _as_dict(activity)
        for activity in plan.get("activities", [])
    ]


def _normalize(value: str) -> str:
    return " ".join(str(value).lower().split())


def _is_important(activity: dict, preferences: dict) -> bool:
    """High and medium priority activities and the user's must-do places (FR-41)."""

    if activity.get("priority") in IMPORTANT_PRIORITIES:
        return True

    if activity.get("must_do") is True:
        return True

    place = activity.get("place") or {}
    place_id = str(activity.get("place_id") or place.get("id") or "")
    place_name = _normalize(place.get("name") or "")

    for item in preferences.get("must_do", []):
        item = _as_dict(item) if not isinstance(item, str) else {
            "text": item
        }

        required_id = str(item.get("place_id") or "")
        required_text = _normalize(item.get("text") or "")

        if required_id and place_id and required_id == place_id:
            return True

        if place_name and required_text:
            if place_name == required_text:
                return True

            if place_name in required_text.split(" - "):
                return True

    return False


def _purpose_tags(activity: dict) -> list[str]:
    tags = activity.get("purpose_tags") or []

    if not tags:
        place = activity.get("place") or {}
        tags = place.get("experience_types") or []

    return [str(tag).strip().lower() for tag in tags]


def _candidate_cost(place: dict) -> float | None:
    cost = place.get("est_cost_high")

    if cost is None:
        cost = place.get("est_cost_low")

    return cost


def _travel_limit(preferences: dict, radius_min: int) -> int:
    max_travel = preferences.get("max_travel_min")
    return radius_min if max_travel is None else min(radius_min, max_travel)


def _minutes_between(a: dict, b: dict, mode: str) -> float:
    distance = distance_km(LatLng(lat=a["lat"], lng=a["lng"]), b["lat"], b["lng"])
    return rough_minutes(distance, mode)


def _neighbours(activity: dict, activities: list[dict], replacement: dict) -> list[dict]:
    """The stop before, the replacement, and the stop after, on the same day."""
    same_day = sorted(
        (
            item
            for item in activities
            if item.get("day") == activity.get("day")
            and item.get("status") != "cancelled"
        ),
        key=lambda item: datetime.fromisoformat(item["start"]),
    )
    ids = [item.get("id") for item in same_day]
    if activity.get("id") not in ids:
        return [replacement]
    position = ids.index(activity.get("id"))
    before = same_day[position - 1 : position] if position > 0 else []
    after = same_day[position + 1 : position + 2]
    return [*before, replacement, *after]


def _check_candidate(
    activity: dict,
    candidate: dict,
    activities: list[dict],
    preferences: dict,
    trip_id: str,
    version: int,
    radius_min: int,
) -> list[str] | None:
    """Return None if the candidate fails a check, else the list of unknowns.

    An empty list means every check ran and passed; ["hours"] means the hours
    are not listed, so that check could not run.
    """
    original = activity.get("place") or {}
    planned_ids = {
        (item.get("place") or {}).get("id") or item.get("place_id")
        for item in activities
        if item.get("status") != "cancelled"
    }

    if not candidate.get("id") or candidate.get("id") in planned_ids:
        return None  # the same place, or one already in the plan

    if any(
        place.get(key) is None
        for place in (original, candidate)
        for key in ("lat", "lng")
    ):
        return None

    purpose = set(_purpose_tags(activity))
    candidate_types = {
        str(tag).strip().lower()
        for tag in (candidate.get("experience_types") or [])
    }
    if not purpose or not purpose & candidate_types:
        return None

    mode = preferences.get("mode", "walking")
    if _minutes_between(original, candidate, mode) > _travel_limit(preferences, radius_min):
        return None

    unknown: list[str] = []
    replacement = {
        **activity,
        "place_id": candidate["id"],
        "place": candidate,
        "est_cost": _candidate_cost(candidate),
    }

    # Opening hours: closed rejects; not listed is unknown (contracts.md 5.2).
    hours = candidate.get("hours")
    if hours is None:
        hours = candidate.get("opening_hours")
    opening = check_opening_hours(
        activity["start"],
        activity["end"],
        hours if isinstance(hours, list) else None,
        trip_id=trip_id,
        version=version,
        activity_id=activity.get("id"),
    )
    if not opening.passed:
        if opening.severity != "data-gap":
            return None
        unknown.append("hours")

    avoid = check_avoid_list(
        [replacement],
        preferences.get("avoid", []),
        trip_id=trip_id,
        version=version,
    )
    if not avoid.passed and avoid.severity == "hard":
        return None

    # Budget: a known price over the limit rejects; no price is unknown.
    budget_max = preferences.get("budget_max")
    if budget_max is None:
        budget_max = preferences.get("budget")
    if budget_max is not None:
        if replacement["est_cost"] is None:
            unknown.append("price")
        else:
            updated = [
                replacement if item.get("id") == activity.get("id") else item
                for item in activities
            ]
            budget = check_budget(
                updated,
                budget_max,
                preferences.get("budget_strictness", "strict"),
                trip_id=trip_id,
                version=version,
            )
            if not budget.passed and budget.severity == "hard":
                return None

    path = _neighbours(activity, activities, replacement)
    if len(path) > 1:
        travel = check_travel_time(
            path,
            mode=mode,
            max_travel_min=preferences.get("max_travel_min"),
            trip_id=trip_id,
            version=version,
        )
        if not travel.passed and travel.severity != "data-gap":
            return None

    return unknown


def _make_backup(
    activity: dict,
    candidate: dict,
    unknown: list[str],
    purpose: list[str],
    mode: str,
    validated_at: str,
) -> dict:
    """One backup in the docs/contracts.md 6.1 shape, plus `place` and `unknown`."""
    candidate_types = {str(t).strip().lower() for t in candidate.get("experience_types") or []}
    shared = set(purpose) & candidate_types
    cost = _candidate_cost(candidate)
    planned_cost = activity.get("est_cost")
    return {
        "activity_id": activity.get("id"),
        "place_id": candidate["id"],
        "rank": 0,  # set after sorting
        "purpose_similarity": round(len(shared) / len(set(purpose)), 2),
        "cost_delta": (
            None if cost is None or planned_cost is None else round(cost - planned_cost, 2)
        ),
        "travel_delta_min": round(_minutes_between(activity["place"], candidate, mode)),
        "validated_at": validated_at,
        "place": candidate,
        "unknown": unknown,
    }


def find_backups(
    plan: dict,
    search=None,
    radius_min: int = 20,
    per_activity: int = BACKUPS_PER_ACTIVITY,
    max_searches: int = MAX_BACKUP_SEARCHES,
    only_ids: set[str] | None = None,
) -> list[dict]:
    """Find up to `per_activity` backups for each important activity.

    Returns one result per important activity:
    {"activity_id", "purpose_tags", "backups": [Backup, ...], "reason"}.
    At most `max_searches` place searches are made for the whole plan.
    With `only_ids`, only those activities are searched (the others keep theirs).
    """

    if radius_min <= 0:
        raise ValueError("radius_min must be positive")

    if search is None:
        search = get_place_search()

    preferences = _get_preferences(plan)
    activities = _get_activities(plan)

    trip_id = str(plan.get("trip_id", "unknown"))
    version = plan.get("version", 0)
    mode = preferences.get("mode", "walking")
    validated_at = datetime.now(UTC).isoformat()
    searches = 0

    results = []
    jobs = []  # (activity, result, purpose, original) that need a place search

    for activity in activities:
        if only_ids is not None and activity.get("id") not in only_ids:
            continue

        if activity.get("status") in SKIPPED_STATUSES:
            continue

        if not _is_important(activity, preferences):
            continue

        original = activity.get("place") or {}
        purpose = _purpose_tags(activity)

        result = {
            "activity_id": activity.get("id"),
            "purpose_tags": purpose,
            "backups": [],
            "reason": "No verified backup available.",
        }
        results.append(result)

        if not purpose:
            result["reason"] = "Activity purpose is unknown."
            continue

        if original.get("lat") is None or original.get("lng") is None:
            result["reason"] = "Original place coordinates are missing."
            continue

        if searches >= max_searches:
            result["reason"] = "Search limit for backups reached."
            continue

        searches += 1
        jobs.append((activity, result, purpose, original))

    # All searches run at the same time; the checks below stay one by one, in order.
    def search_near(original, purpose):
        return lambda: search.search_places(
            query="",
            near=LatLng(lat=original["lat"], lng=original["lng"]),
            categories=purpose,
            radius_min=radius_min,
            mode=mode,
            limit=20,
        )

    answers = run_all([search_near(original, purpose) for _, _, purpose, original in jobs])

    for (activity, result, purpose, original), candidates in zip(jobs, answers, strict=True):
        if isinstance(candidates, Exception):  # a provider error must not stop the plan
            result["reason"] = "Place search could not be completed."
            continue

        found = []
        for candidate in candidates:
            place = _as_dict(candidate)
            unknown = _check_candidate(
                activity, place, activities, preferences, trip_id, version, radius_min
            )
            if unknown is not None:
                found.append(_make_backup(activity, place, unknown, purpose, mode, validated_at))

        # Fully checked first, then closest purpose, shortest detour, lowest cost.
        found.sort(
            key=lambda b: (
                len(b["unknown"]),
                -b["purpose_similarity"],
                b["travel_delta_min"],
                b["cost_delta"] if b["cost_delta"] is not None else 0,
            )
        )
        result["backups"] = found[:per_activity]
        for rank, backup in enumerate(result["backups"], start=1):
            backup["rank"] = rank

        if result["backups"]:
            result["reason"] = (
                "Passed the opening-hours, budget, avoid-list and travel checks "
                "that the available data allows."
            )

    return results


def attach_backups(
    itinerary: dict, trip: dict, search=None, only_ids: set[str] | None = None
) -> int:
    """Store backups on each activity (or only on `only_ids`).

    Returns how many backups the whole plan has afterwards.
    """
    results = find_backups(
        {**itinerary, "requirements": trip}, search=search, only_ids=only_ids
    )
    by_activity = {result["activity_id"]: result["backups"] for result in results}
    total = 0
    for day in itinerary.get("days", []):
        for activity in day.get("activities", []):
            if activity.get("id") in by_activity:
                activity["backups"] = by_activity[activity["id"]]
            total += len(activity.get("backups") or [])
    return total
