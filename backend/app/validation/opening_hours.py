
from datetime import datetime, timedelta

from app.models.place import OpeningPeriod
from app.models.validation_result import ValidationResult


def check_opening_hours(
    start,
    end,
    hours,
    trip_id="unknown",
    version=0,
    activity_id=None,
):
    """Check an activity against a place's opening hours."""

    start = datetime.fromisoformat(start) if isinstance(start, str) else start
    end = datetime.fromisoformat(end) if isinstance(end, str) else end

    if start >= end:
        raise ValueError("Activity must end after it starts")

    activity_ids = [activity_id] if activity_id is not None else []

    def make_result(passed, severity, message):
        return ValidationResult(
            id="opening-hours-check",
            trip_id=trip_id,
            version=version,
            rule="opening_hours",
            passed=passed,
            severity=severity,
            message=message,
            activity_ids=activity_ids,
        )

    # No hours (None or an empty list) means we don't know, not "closed".
    if not hours or not isinstance(hours, list):
        return make_result(
            False,
            "data-gap",
            "Opening hours are unavailable.",
        )

    periods = [
        period
        if isinstance(period, OpeningPeriod)
        else OpeningPeriod.model_validate(period)
        for period in hours
    ]

    current_date = start.date() - timedelta(days=1)
    last_date = end.date()
    intervals = []

    while current_date <= last_date:
        for period in periods:
            if current_date.strftime("%A").lower() != period.day:
                continue

            opening = datetime.combine(
                current_date,
                period.open,
                tzinfo=start.tzinfo,
            )

            closing = datetime.combine(
                current_date,
                period.close,
                tzinfo=start.tzinfo,
            )

            if period.closes_next_day:
                closing += timedelta(days=1)

            if closing > opening:
                intervals.append((opening, closing))

        current_date += timedelta(days=1)

    intervals.sort(key=lambda interval: interval[0])
    covered_until = start

    for opening, closing in intervals:
        if opening > covered_until:
            break

        if closing > covered_until:
            covered_until = closing

        if covered_until >= end:
            return make_result(
                True,
                "soft",
                "Place is open for the entire activity.",
            )

    return make_result(
        False,
        "hard",
        "Activity is scheduled outside the place's opening hours.",
    )


def check_plan_opening_hours(activities, trip_id="unknown", version=0):
    """Check every activity in a plan against its place's opening hours."""
    closed = []
    unknown = []

    for activity in activities:
        if activity.get("status") == "cancelled":
            continue

        place = activity.get("place") or {}
        result = check_opening_hours(
            activity["start"],
            activity["end"],
            place.get("hours"),
            trip_id=trip_id,
            version=version,
            activity_id=activity.get("id"),
        )

        if result.severity == "hard":
            closed.append(result)
        elif result.severity == "data-gap":
            unknown.append(result)

    def make_result(passed, severity, message, results=()):
        activity_ids = [aid for result in results for aid in result.activity_ids]
        return ValidationResult(
            id="opening-hours-check",
            trip_id=trip_id,
            version=version,
            rule="opening_hours",
            passed=passed,
            severity=severity,
            message=message,
            activity_ids=activity_ids,
        )

    if closed:
        return make_result(
            False,
            "hard",
            f"{len(closed)} activities are scheduled outside opening hours.",
            closed,
        )

    if unknown:
        return make_result(
            False,
            "data-gap",
            f"Opening hours are unavailable for {len(unknown)} activities.",
            unknown,
        )

    return make_result(True, "soft", "All places are open for their activities.")
