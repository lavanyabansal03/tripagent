
from datetime import datetime

from app.models.validation_result import ValidationResult


def find_overlaps(activities, trip_id="unknown", version=0):
    """Return a list of ValidationResult objects for overlaps."""
    active = [
        activity
        for activity in activities
        if activity.get("status") != "cancelled"
    ]

    active.sort(
        key=lambda activity: datetime.fromisoformat(activity["start"])
    )

    conflicts = []

    for i, first in enumerate(active):
        first_end = datetime.fromisoformat(first["end"])

        for second in active[i + 1:]:
            second_start = datetime.fromisoformat(second["start"])

            if second_start >= first_end:
                break

            first_id = first.get("id")
            second_id = second.get("id")
            ids = [
                activity_id
                for activity_id in (first_id, second_id)
                if activity_id is not None
            ]

            conflicts.append(
                ValidationResult(
                    id=f"overlap-{i}-{len(conflicts)}",
                    trip_id=trip_id,
                    version=version,
                    rule="overlap",
                    passed=False,
                    severity="hard",
                    message=(
                        f"Activities {first_id or 'unknown'} "
                        f"and {second_id or 'unknown'} overlap."
                    ),
                    activity_ids=ids,
                )
            )

    return conflicts


def check_overlap(activities, trip_id="unknown", version=0):
    """Return one standardized result for the overlap check."""
    conflicts = find_overlaps(activities, trip_id, version)

    if not conflicts:
        return ValidationResult(
            id="overlap-check",
            trip_id=trip_id,
            version=version,
            rule="overlap",
            passed=True,
            severity="soft",
            message="No overlapping activities found.",
            activity_ids=[],
        )

    all_ids = list(
        dict.fromkeys(
            activity_id
            for conflict in conflicts
            for activity_id in conflict.activity_ids
        )
    )

    return ValidationResult(
        id="overlap-check",
        trip_id=trip_id,
        version=version,
        rule="overlap",
        passed=False,
        severity="hard",
        message=f"Found {len(conflicts)} overlapping activity pairs.",
        activity_ids=all_ids,
    )
