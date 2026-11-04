from datetime import datetime, timedelta

from app.models.place import OpeningPeriod


def check_opening_hours(start, end, hours):
    """
    Check whether an activity is scheduled during opening hours.

    Returns:
        "passed"  - Place is open for the entire activity.
        "failed"  - Activity is outside opening hours.
        "unknown" - Opening hours are unavailable.
    """

    if hours is None:
        return "unknown"

    start = datetime.fromisoformat(start) if isinstance(start, str) else start
    end = datetime.fromisoformat(end) if isinstance(end, str) else end

    if start >= end:
        raise ValueError("Activity must end after it starts")

    # Convert opening-hour records into OpeningPeriod objects
    periods = [
        period if isinstance(period, OpeningPeriod)
        else OpeningPeriod.model_validate(period)
        for period in hours
    ]

    # Check both the activity's date and the previous date
    # to support places that stay open past midnight.
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

    # Sort opening intervals and check continuous coverage.
    intervals.sort(key=lambda interval: interval[0])
    covered_until = start

    for opening, closing in intervals:
        if opening > covered_until:
            break

        if closing > covered_until:
            covered_until = closing

        if covered_until >= end:
            return "passed"

    return "failed"
