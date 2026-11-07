"""Backup Agent (A4): find validated alternatives for priority activities."""

from datetime import datetime
from typing import Any

from app.tools.base import LatLng
from app.tools.mock_places import MockPlaceSearch, distance_km, rough_minutes
from app.validation.avoid import check_avoid_list
from app.validation.budget import check_budget
from app.validation.opening_hours import check_opening_hours
from app.validation.travel_time import check_travel_time


def _as_dict(value: Any) -> dict:
    """Accept dictionaries or Pydantic models."""
    if isinstance(value, dict):
        return value.copy()
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    return {}


def _get_preferences(plan: dict) -> dict:
    """Read preferences from the plan or its requirements."""
    preferences = plan.get("requirements")

    if preferences is None:
        preferences = plan.get("trip", plan)

    return _as_dict(preferences)


def _get_activities(plan: dict) -> list[dict]:
    """Collect activities from every itinerary day."""
    if "days" in plan:
        return [
            activity
            for day in plan["days"]
            for activity in day.get("activities", [])
        ]

    return list(plan.get("activities", []))


def _is_important(activity: dict) -> bool:
    """Identify activities that need a backup."""
    return (
        activity.get("priority") == "high"
        or activity.get("must_do") is True
    )


def _purpose_tags(activity: dict) -> list[str]:
    """Find the experience types the replacement should preserve."""
    tags = activity.get("purpose_tags") or []

    if not tags:
        place = activity.get("place") or {}
        tags = place.get("experience_types") or []

    return [str(tag).lower() for tag in tags]


def _candidate_cost(place: dict) -> float | None:
    """Use a known estimated cost, not an invented price."""
    cost = place.get("est_cost_high")

    if cost is None:
        cost = place.get("est_cost_low")

    return cost


def _check_candidate(
    activity: dict,
    candidate: dict,
    activities: list[dict],
    preferences: dict,
    trip_id: str,
    version: int,
    radius_min: int,
) -> bool:
    """Return True only when essential validation checks pass."""

    original = activity.get("place") or {}

    if candidate.get("id") == original.get("id"):
        return False

    if candidate.get("lat") is None or candidate.get("lng") is None:
        return False

    if original.get("lat") is None or original.get("lng") is None:
        return False

    purpose = set(_purpose_tags(activity))
    candidate_types = {
        str(tag).lower()
        for tag in candidate.get("experience_types", [])
    }

    if not purpose or not purpose.intersection(candidate_types):
        return False

    mode = preferences.get("mode", "walking")
    max_travel = preferences.get("max_travel_min")

    effective_limit = radius_min

    if max_travel is not None:
        effective_limit = min(effective_limit, max_travel)

    distance = distance_km(
        LatLng(lat=original["lat"], lng=original["lng"]),
        candidate["lat"],
        candidate["lng"],
    )

    travel_minutes = rough_minutes(distance, mode)

    if travel_minutes > effective_limit:
        return False

    replacement = {
        **activity,
        "place_id": candidate["id"],
        "place": candidate,
        "est_cost": _candidate_cost(candidate),
    }

    # Opening hours must be structured and verifiable.
    hours = candidate.get("hours")

    if not isinstance(hours, list):
        hours = candidate.get("opening_hours")

    if not isinstance(hours, list):
        return False

    opening_result = check_opening_hours(
        activity["start"],
        activity["end"],
        hours,
        trip_id=trip_id,
        version=version,
        activity_id=activity.get("id"),
    )

    if not opening_result.passed:
        return False

    # Reuse the existing avoid-list validator.
    avoid_result = check_avoid_list(
        [replacement],
        preferences.get("avoid", []),
        trip_id=trip_id,
        version=version,
    )

    if not avoid_result.passed:
        return False

    # Check the budget using the full itinerary with the replacement.
    budget_max = preferences.get(
        "budget_max", preferences.get("budget")
    )

    if budget_max is not None:
        if replacement["est_cost"] is None:
            return False

        updated = [
            replacement if item.get("id") == activity.get("id") else item
            for item in activities
        ]

        budget_result = check_budget(
            updated,
            budget_max,
            preferences.get("budget_strictness", "strict"),
            trip_id=trip_id,
            version=version,
        )

        if not budget_result.passed:
            return False

    # Check travel feasibility against neighbouring activities.
    same_day = sorted(
        [
            item
            for item in activities
            if item.get("day") == activity.get("day")
            and item.get("status") != "cancelled"
        ],
        key=lambda item: datetime.fromisoformat(item["start"]),
    )

    position = next(
        (
            index
            for index, item in enumerate(same_day)
            if item.get("id") == activity.get("id")
        ),
        None,
    )

    if position is None:
        return False

    travel_activities = []

    if position > 0:
        travel_activities.append(same_day[position - 1])

    travel_activities.append(replacement)

    if position + 1 < len(same_day):
        travel_activities.append(same_day[position + 1])

    if len(travel_activities) > 1:
        travel_result = check_travel_time(
            travel_activities,
            mode=mode,
            max_travel_min=max_travel,
            trip_id=trip_id,
            version=version,
        )

        if not travel_result.passed:
            return False

    return True


def find_backups(
    plan: dict,
    search=None,
    radius_min: int = 20,
) -> list[dict]:
    """Find one validated replacement for each important activity.

    Returns an explicit unavailable result when no suitable backup exists.
    """

    if radius_min <= 0:
        raise ValueError("radius_min must be positive")

    if search is None:
        search = MockPlaceSearch()

    preferences = _get_preferences(plan)
    activities = _get_activities(plan)

    trip_id = str(plan.get("trip_id", "unknown"))
    version = plan.get("version", 0)
    mode = preferences.get("mode", "walking")

    results = []

    for activity in activities:
        if not _is_important(activity):
            continue

        if activity.get("status") == "cancelled":
            continue

        activity_id = activity.get("id")
        original = activity.get("place") or {}
        purpose = _purpose_tags(activity)

        result = {
            "activity_id": activity_id,
            "purpose_tags": purpose,
            "backup": None,
            "reason": "No verified backup available.",
        }

        if not purpose:
            result["reason"] = "Activity purpose is unknown."
            results.append(result)
            continue

        if original.get("lat") is None or original.get("lng") is None:
            result["reason"] = "Original place coordinates are missing."
            results.append(result)
            continue

        try:
            candidates = search.search_places(
                query="",
                near=LatLng(
                    lat=original["lat"],
                    lng=original["lng"],
                ),
                categories=purpose,
                radius_min=radius_min,
                mode=mode,
                limit=20,
            )
        except (ValueError, TypeError, RuntimeError):
            result["reason"] = "Place search could not be completed."
            results.append(result)
            continue

        valid_candidates = []

        for candidate in candidates:
            place = _as_dict(candidate)

            if _check_candidate(
                activity,
                place,
                activities,
                preferences,
                trip_id,
                version,
                radius_min,
            ):
                distance = distance_km(
                    LatLng(
                        lat=original["lat"],
                        lng=original["lng"],
                    ),
                    place["lat"],
                    place["lng"],
                )

                valid_candidates.append(
                    (
                        -len(
                            set(purpose).intersection(
                                set(place.get("experience_types", []))
                            )
                        ),
                        rough_minutes(distance, mode),
                        _candidate_cost(place) or 0,
                        place,
                    )
                )

        if valid_candidates:
            valid_candidates.sort(key=lambda item: item[:3])
            selected = valid_candidates[0][3]

            result["backup"] = selected
            result["reason"] = (
                "Verified alternative with matching purpose, "
                "opening hours, budget, and travel constraints."
            )

        results.append(result)

    return results
