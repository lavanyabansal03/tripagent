def check_avoid_list(activities, avoid):
    """
    Check whether scheduled activities conflict
    with the traveler's avoid list.

    Returns a list of conflicts.
    """

    conflicts = []

    # Convert avoid preferences to lowercase
    avoid_terms = [
        term.strip().lower()
        for term in avoid
        if term.strip()
    ]

    for activity in activities:
        # Ignore cancelled activities
        if activity.get("status") == "cancelled":
            continue

        place = activity.get("place") or {}

        name = str(place.get("name") or "").lower()
        categories = [
            str(category).lower()
            for category in place.get("categories", [])
        ]

        experience_types = [
            str(category).lower()
            for category in place.get("experience_types", [])
        ]

        # Match against place name and categories
        searchable = [name] + categories + experience_types

        for term in avoid_terms:
            if any(term in value for value in searchable):
                conflicts.append({
                    "passed": False,
                    "severity": "error",
                    "activity_ids": [activity.get("id")],
                    "message": f"Activity conflicts with avoid preference: {term}",
                })
                break

    return conflicts
