"""Run all six TripAgent validation checks on an itinerary."""

from typing import Any

from app.models.validation_result import ValidationResult
from app.validation.avoid import check_avoid_list
from app.validation.budget import check_budget
from app.validation.opening_hours import check_opening_hours
from app.validation.overlap import check_overlap
from app.validation.travel_time import check_travel_time
from app.validation.variety import check_variety


def run_all_checks(plan: dict[str, Any]) -> list[ValidationResult]:
    """Run every validator and return standardized results.

    Expected input:
        {
            "trip_id": "T001",
            "version": 1,
            "days": [
                {"day": 1, "activities": [...]}
            ],
            "trip": {
                "budget_max": 500,
                "budget_strictness": "strict",
                "avoid": ["bars"],
                "mode": "walking",
                "max_travel_min": 30,
            },
        }

    Trip preferences may also be supplied under "requirements"
    or directly in the plan.
    """

    trip_id = str(plan.get("trip_id", "unknown"))
    version = plan.get("version", 0)

    preferences = plan.get("trip")

    if preferences is None:
        preferences = plan.get("requirements")

    if preferences is None:
        preferences = plan

    if hasattr(preferences, "model_dump"):
        preferences = preferences.model_dump(mode="json")

    if not isinstance(preferences, dict):
        raise ValueError("Trip preferences must be a dictionary")

    activities = []

    for day in plan.get("days", []):
        activities.extend(day.get("activities", []))

    # Also support plans containing a flat activity list.
    if not plan.get("days"):
        activities = plan.get("activities", [])

    # Support the approved budget range and legacy budget field.
    budget_max = preferences.get("budget_max")

    if budget_max is None:
        budget_max = preferences.get("budget")

    budget_strictness = preferences.get(
        "budget_strictness", "flexible"
    )

    mode = preferences.get("mode", "walking")
    max_travel_min = preferences.get("max_travel_min")
    avoid = preferences.get("avoid", [])

    results = []

    # 1. Overlap validation
    results.append(
        check_overlap(
            activities,
            trip_id=trip_id,
            version=version,
        )
    )

    # 2. Budget validation
    budget_result = check_budget(
        activities,
        budget_max,
        budget_strictness,
        trip_id=trip_id,
        version=version,
    )

    if budget_max is None and budget_strictness != "none":
        budget_result = ValidationResult(
            id="budget-check",
            trip_id=trip_id,
            version=version,
            rule="budget",
            passed=False,
            severity="data-gap",
            message="Budget limit is unavailable.",
            activity_ids=[],
        )

    results.append(budget_result)

    # 3. Opening-hours validation
    for activity in activities:
        if activity.get("status") == "cancelled":
            continue

        place = activity.get("place") or {}

        hours = place.get("hours")

        if hours is None:
            hours = place.get("opening_hours")

        results.append(
            check_opening_hours(
                activity["start"],
                activity["end"],
                hours,
                trip_id=trip_id,
                version=version,
                activity_id=activity.get("id"),
            )
        )

    # 4. Travel-time validation
    results.append(
        check_travel_time(
            activities,
            mode=mode,
            max_travel_min=max_travel_min,
            trip_id=trip_id,
            version=version,
        )
    )

    # 5. Avoid-list validation
    results.append(
        check_avoid_list(
            activities,
            avoid,
            trip_id=trip_id,
            version=version,
        )
    )

    # 6. Activity-variety validation
    results.append(
        check_variety(
            activities,
            trip_id=trip_id,
            version=version,
        )
    )

    return results
