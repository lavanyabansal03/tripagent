
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

    active.sort(key=lambda activity: activity["start"])

    previous_type = None
    consecutive = []
    conflicting_ids = []
    missing_ids = []
    conflict_count = 0

    for activity in active:
        place = activity.get("place") or {}
        types = place.get("experience_types") or []

        current_type = (
            str(types[0]).strip().lower()
            if types and types[0] is not None
            else None
        )

        if not current_type:
            activity_id = activity.get("id")

            if activity_id is not None:
                missing_ids.append(activity_id)

            previous_type = None
            consecutive = []
            continue

        if current_type == previous_type:
            consecutive.append(activity)
        else:
            consecutive = [activity]

        previous_type = current_type

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
                f"Found {conflict_count} sequences with more than "
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
