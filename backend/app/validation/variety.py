def check_variety(activities, max_consecutive=2):
    """
    Detect too many consecutive activities of the same type.

    Returns warnings containing the affected activity IDs.
    """
    if max_consecutive < 1:
        raise ValueError("max_consecutive must be at least 1")

    active = [
        activity
        for activity in activities
        if activity.get("status") != "cancelled"
    ]

    # Arrange activities chronologically.
    active.sort(key=lambda activity: activity["start"])

    warnings = []
    previous_type = None
    consecutive = []

    for activity in active:
        place = activity.get("place") or {}
        types = place.get("experience_types") or []

        # Unknown categories cannot be checked reliably.
        current_type = types[0].lower() if types else None

        if current_type is None:
            previous_type = None
            consecutive = []
            continue

        if current_type == previous_type:
            consecutive.append(activity)
        else:
            consecutive = [activity]

        previous_type = current_type

        if len(consecutive) == max_consecutive + 1:
            warnings.append({
                "passed": False,
                "severity": "warning",
                "activity_ids": [
                    item.get("id") for item in consecutive
                ],
                "message": (
                    f"More than {max_consecutive} consecutive "
                    f"activities have type '{current_type}'"
                ),
            })

    return warnings
