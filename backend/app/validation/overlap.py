from datetime import datetime


def find_overlaps(activities):
    """Return the IDs of activities with overlapping times."""

    active = [
        activity
        for activity in activities
        if activity.get("status") != "cancelled"
    ]

    # Convert timestamps and sort activities by start time
    active = sorted(
        active,
        key=lambda activity: datetime.fromisoformat(
            activity["start"]
        ),
    )

    conflicts = []

    for i, first in enumerate(active):
        first_end = datetime.fromisoformat(first["end"])

        for second in active[i + 1:]:
            second_start = datetime.fromisoformat(
                second["start"]
            )

            if second_start >= first_end:
                break

            conflicts.append({
                "activity_ids": [
                    first.get("id"),
                    second.get("id"),
                ],
                "message": "Activities overlap",
                "severity": "error",
                "passed": False,
            })

    return conflicts


def check_overlap(activities):
    """Return True when no activities overlap."""

    return len(find_overlaps(activities)) == 0
