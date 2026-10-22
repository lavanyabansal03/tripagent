def normalize_word(word):
    """Normalize simple singular and plural words."""
    word = word.strip().lower()

    if word.endswith("ies") and len(word) > 3:
        return word[:-3] + "y"

    if word.endswith("s") and not word.endswith("ss"):
        return word[:-1]

    return word


def check_avoid_list(activities, avoid):
    """Return activities that conflict with the traveler's avoid list."""

    conflicts = []

    avoid_terms = [
        normalize_word(term)
        for term in avoid
        if term.strip()
    ]

    for activity in activities:
        if activity.get("status") == "cancelled":
            continue

        place = activity.get("place") or {}

        searchable = [
            place.get("name") or "",
            *(place.get("categories") or []),
            *(place.get("experience_types") or []),
        ]

        for term in avoid_terms:
            for value in searchable:
                words = [
                    normalize_word(word)
                    for word in str(value).split()
                ]

                if term in words or term in normalize_word(str(value)):
                    conflicts.append({
                        "passed": False,
                        "severity": "error",
                        "activity_ids": [activity.get("id")],
                        "message": (
                            f"Activity conflicts with avoid preference: {term}"
                        ),
                    })
                    break
            else:
                continue
            break

    return conflicts
