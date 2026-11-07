"""Backup Agent (A4): find alternatives for important activities."""

from datetime import datetime
from typing import Any

from app.tools.base import LatLng
from app.tools.mock_places import MockPlaceSearch, distance_km, rough_minutes
from app.validation.avoid import check_avoid_list
from app.validation.budget import check_budget
from app.validation.opening_hours import check_opening_hours
from app.validation.travel_time import check_travel_time


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
    """Recognize high priority and the user's must-do places."""

    if activity.get("priority") == "high":
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


def _check_candidate(
    activity: dict,
    candidate: dict,
    activities: list[dict],
    preferences: dict,
    trip_id: str,
    version: int,
    radius_min: int,
) -> bool:
    original = activity.get("place") or {}

    if candidate.get("id") == original.get("id"):
        return False

    if not candidate.get("id"):
        return False

    if any(
        place.get(key) is None
        for place in (original, candidate)
        for key in ("lat", "lng")
    ):
        return False

    purpose = set(_purpose_tags(activity))

    candidate_types = {
        str(tag).strip().lower()
        for tag in (candidate.get("experience_types") or [])
    }

    if not purpose or not purpose.intersection(candidate_types):
        return False

    mode = preferences.get("mode", "walking")
    max_travel = preferences.get("max_travel_min")

    effective_limit = radius_min

    if max_travel is not None:
        effective_limit = min(radius_min, max_travel)

    distance = distance_km(
        LatLng(lat=original["lat"], lng=original["lng"]),
        candidate["lat"],
        candidate["lng"],
    )

    if rough_minutes(distance, mode) > effective_limit:
        return False

    replacement = {
        **activity,
        "place_id": candidate["id"],
        "place": candidate,
        "est_cost": _candidate_cost(candidate),
    }

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

    avoid_result = check_avoid_list(
        [replacement],
        preferences.get("avoid", []),
        trip_id=trip_id,
        version=version,
    )

    if not avoid_result.passed:
        return False

    budget_max = preferences.get("budget_max")

    if budget_max is None:
        budget_max = preferences.get("budget")

    if budget_max is not None:
        if replacement["est_cost"] is None:
            return False

        updated = [
            replacement
            if item.get("id") == activity.get("id")
            else item
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
    """Find one suitable backup per important activity."""

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
        if activity.get("status") == "cancelled":
            continue

        if not _is_important(activity, preferences):
            continue

        original = activity.get("place") or {}
        purpose = _purpose_tags(activity)

        result = {
            "activity_id": activity.get("id"),
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

            if not _check_candidate(
                activity,
                place,
                activities,
                preferences,
                trip_id,
                version,
                radius_min,
            ):
                continue

            distance = distance_km(
                LatLng(
                    lat=original["lat"],
                    lng=original["lng"],
                ),
                place["lat"],
                place["lng"],
            )

            matching_types = {
                str(tag).strip().lower()
                for tag in (place.get("experience_types") or [])
            }

            valid_candidates.append(
                (
                    -len(set(purpose).intersection(matching_types)),
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
                "Alternative passed the available opening-hours, "
                "budget, avoid-list, and estimated travel checks."
            )

        results.append(result)

    return results
