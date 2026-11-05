
import re

from app.models.validation_result import ValidationResult


def normalize_word(word):
    """Normalize simple singular and plural words."""
    word = word.lower()

    if word.endswith("ies") and len(word) > 3:
        return word[:-3] + "y"

    if word.endswith("s") and not word.endswith("ss"):
        return word[:-1]

    return word


def tokenize(value):
    """Split text into complete, normalized words."""
    words = re.findall(r"\b\w+\b", str(value).lower())
    return [normalize_word(word) for word in words]


def matches_avoid_term(value, term):
    """Match complete words or consecutive-word phrases."""
    value_words = tokenize(value)
    term_words = tokenize(term)

    if not term_words:
        return False

    length = len(term_words)

    return any(
        value_words[i:i + length] == term_words
        for i in range(len(value_words) - length + 1)
    )


def check_avoid_list(
    activities,
    avoid,
    trip_id="unknown",
    version=0,
):
    """Check activities against the traveler's avoid preferences."""
    avoid_terms = [
        term.strip()
        for term in (avoid or [])
        if isinstance(term, str) and term.strip()
    ]

    conflicting_ids = []
    matched_terms = set()
    missing_ids = []

    for activity in activities:
        if activity.get("status") == "cancelled":
            continue

        place = activity.get("place") or {}

        searchable = [
            place.get("name") or "",
            *(place.get("categories") or []),
            *(place.get("experience_types") or []),
        ]

        if not any(str(value).strip() for value in searchable):
            if avoid_terms:
                activity_id = activity.get("id")
                if activity_id is not None:
                    missing_ids.append(activity_id)
            continue

        for term in avoid_terms:
            if any(
                matches_avoid_term(value, term)
                for value in searchable
            ):
                activity_id = activity.get("id")

                if activity_id is not None:
                    conflicting_ids.append(activity_id)

                matched_terms.add(term)

    if matched_terms:
        return ValidationResult(
            id="avoid-check",
            trip_id=trip_id,
            version=version,
            rule="avoid",
            passed=False,
            severity="hard",
            message=(
                "Activities conflict with avoid preferences: "
                + ", ".join(sorted(matched_terms))
                + "."
            ),
            activity_ids=list(dict.fromkeys(conflicting_ids)),
        )

    if missing_ids:
        return ValidationResult(
            id="avoid-check",
            trip_id=trip_id,
            version=version,
            rule="avoid",
            passed=False,
            severity="data-gap",
            message=(
                "Cannot verify avoid preferences because "
                "some activities have no place information."
            ),
            activity_ids=list(dict.fromkeys(missing_ids)),
        )

    return ValidationResult(
        id="avoid-check",
        trip_id=trip_id,
        version=version,
        rule="avoid",
        passed=True,
        severity="soft",
        message="No avoid-list conflicts found.",
        activity_ids=[],
    )
