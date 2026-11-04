from datetime import datetime

from app.models.validation_result import ValidationResult
from app.tools.base import LatLng, Mode
from app.tools.mock_places import distance_km, rough_minutes


def check_travel_time(
    activities: list[dict],
    mode: Mode = "walking",
    max_travel_min: int | None = None,
    trip_id: str = "unknown",
    version: int = 0,
) -> ValidationResult:
    """Check travel feasibility and the user's travel limit."""

    if max_travel_min is not None and max_travel_min < 0:
        raise ValueError("max_travel_min cannot be negative")

    if mode not in ("walking", "cycling", "transit", "driving"):
        raise ValueError("Invalid travel mode")

    active = [
        activity
        for activity in activities
        if activity.get("status") != "cancelled"
    ]

    active.sort(
        key=lambda activity: datetime.fromisoformat(activity["start"])
    )

    hard_issues = []
    soft_issues = []
    data_gaps = []
    hard_ids = []
    soft_ids = []
    gap_ids = []

    for first, second in zip(active, active[1:]):
        first_id = first.get("id")
        second_id = second.get("id")
        pair_ids = [
            activity_id
            for activity_id in (first_id, second_id)
            if activity_id is not None
        ]

        first_place = first.get("place") or {}
        second_place = second.get("place") or {}

        if not all(
            place.get(key) is not None
            for place in (first_place, second_place)
            for key in ("lat", "lng")
        ):
            data_gaps.append(
                f"Coordinates missing between "
                f"{first_id or 'unknown'} and "
                f"{second_id or 'unknown'}."
            )
            gap_ids.extend(pair_ids)
            continue

        first_end = datetime.fromisoformat(first["end"])
        second_start = datetime.fromisoformat(second["start"])

        available_minutes = (
            second_start - first_end
        ).total_seconds() / 60

        distance = distance_km(
            LatLng(
                lat=first_place["lat"],
                lng=first_place["lng"],
            ),
            second_place["lat"],
            second_place["lng"],
        )

        estimated_minutes = rough_minutes(distance, mode)

        if estimated_minutes > available_minutes:
            hard_issues.append(
                f"{first_id or 'unknown'} to "
                f"{second_id or 'unknown'}: "
                f"{estimated_minutes:.1f} minutes estimated, "
                f"but only {available_minutes:.1f} "
                "minutes available."
            )
            hard_ids.extend(pair_ids)

        if (
            max_travel_min is not None
            and estimated_minutes > max_travel_min
        ):
            soft_issues.append(
                f"{first_id or 'unknown'} to "
                f"{second_id or 'unknown'}: "
                f"{estimated_minutes:.1f} minutes estimated, "
                f"exceeding the user's "
                f"{max_travel_min}-minute travel limit."
            )
            soft_ids.extend(pair_ids)

    if hard_issues or soft_issues:
        severity = "hard" if hard_issues else "soft"
        message = " ".join(hard_issues + soft_issues + data_gaps)
        activity_ids = list(
            dict.fromkeys(hard_ids + soft_ids + gap_ids)
        )
        passed = False

    elif data_gaps:
        severity = "data-gap"
        message = " ".join(data_gaps)
        activity_ids = list(dict.fromkeys(gap_ids))
        passed = False

    else:
        severity = "soft"
        message = "Travel-time validation passed."
        activity_ids = []
        passed = True

    return ValidationResult(
        id="travel-time-check",
        trip_id=trip_id,
        version=version,
        rule="travel_time",
        passed=passed,
        severity=severity,
        message=message,
        activity_ids=activity_ids,
    )
