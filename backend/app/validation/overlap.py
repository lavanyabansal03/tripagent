from datetime import datetime


def check_overlap(activities):
    """
    Check whether scheduled activities overlap.
    Returns True if no overlaps are found.
    """

    active = [
        activity
        for activity in activities
        if activity["status"] != "cancelled"
    ]

    # Sort activities by their starting times
    active.sort(
        key=lambda activity: datetime.fromisoformat(activity["start"])
    )

    for i in range(len(active) - 1):
        first = active[i]
        second = active[i + 1]

        first_end = datetime.fromisoformat(first["end"])
        second_start = datetime.fromisoformat(second["start"])

        if second_start < first_end:
            return False

    return True
