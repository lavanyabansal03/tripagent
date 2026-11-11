
from datetime import datetime

from app.models.validation_result import ValidationResult


def check_variety(
    activities,
    max_consecutive=2,
    trip_id="unknown",
    version=0,
):
    """Check consecutive activities for repetitive experience types."""

    if max_consecutive < 1:
        raise ValueError("max_consecutive must be at least 1")

    active = [
        activity
        for activity in activities
        if activity.get("status") != "cancelled"
    ]

    # Sort by real time, not text, so different UTC offsets order correctly.
    active.sort(
        key=lambda activity: datetime.fromisoformat(activity["start"])
    )

    # Types shared by every activity in the current run of activities.
    shared_types = set()
    consecutive = []
    conflicting_ids = []
    missing_ids = []
    conflict_count = 0

    for activity in active:
        place = activity.get("place") or {}
        # Use every type a place has ("food, nightlife"), not just the first.
        current_types = {
            str(experience_type).strip().lower()
            for experience_type in place.get("experience_types") or []
            if experience_type is not None and str(experience_type).strip()
        }

        if not current_types:
            activity_id = activity.get("id")

            if activity_id is not None:
                missing_ids.append(activity_id)

            shared_types = set()
            consecutive = []
            continue

        if shared_types & current_types:
            shared_types &= current_types
            consecutive.append(activity)
        else:
            shared_types = current_types
            consecutive = [activity]

        if len(consecutive) == max_consecutive + 1:
            conflict_count += 1

            for item in consecutive:
                activity_id = item.get("id")

                if (
                    activity_id is not None
                    and activity_id not in conflicting_ids
                ):
                    conflicting_ids.append(activity_id)

        elif len(consecutive) > max_consecutive + 1:
            activity_id = activity.get("id")

            if (
                activity_id is not None
                and activity_id not in conflicting_ids
            ):
                conflicting_ids.append(activity_id)

    if conflict_count:
        return ValidationResult(
            id="variety-check",
            trip_id=trip_id,
            version=version,
            rule="variety",
            passed=False,
            severity="soft",
            message=(
                f"Found {conflict_count} "
                f"{'sequence' if conflict_count == 1 else 'sequences'} with more than "
                f"{max_consecutive} consecutive activities "
                "of the same experience type."
            ),
            activity_ids=conflicting_ids,
        )

    if missing_ids:
        return ValidationResult(
            id="variety-check",
            trip_id=trip_id,
            version=version,
            rule="variety",
            passed=False,
            severity="data-gap",
            message=(
                "Cannot fully check activity variety because "
                "some activities have no experience type."
            ),
            activity_ids=list(dict.fromkeys(missing_ids)),
        )

    return ValidationResult(
        id="variety-check",
        trip_id=trip_id,
        version=version,
        rule="variety",
        passed=True,
        severity="soft",
        message="Activity variety check passed.",
        activity_ids=[],
    )
