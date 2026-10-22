from datetime import datetime, timedelta

from app.tools.base import LatLng, Mode
from app.tools.mock_places import distance_km, rough_minutes


def check_travel_time(activities: list[dict], mode: Mode = "walking"):
    """Check whether enough time exists between consecutive activities."""

    active = [
        activity
        for activity in activities
        if activity.get("status") != "cancelled"
    ]

    active.sort(key=lambda activity: datetime.fromisoformat(activity["start"]))

    warnings = []

    for first, second in zip(active, active[1:]):
        first_place = first.get("place") or {}
        second_place = second.get("place") or {}

        # We cannot calculate travel time without coordinates.
        if not all(
            key in place and place[key] is not None
            for place in (first_place, second_place)
            for key in ("lat", "lng")
        ):
            warnings.append({
                "passed": False,
                "severity": "warning",
                "activity_ids": [first.get("id"), second.get("id")],
                "message": "Travel time unknown: location coordinates missing",
            })
            continue

        first_end = datetime.fromisoformat(first["end"])
        second_start = datetime.fromisoformat(second["start"])

        available_minutes = (second_start - first_end).total_seconds() / 60

        distance = distance_km(
            LatLng(lat=first_place["lat"], lng=first_place["lng"]),
            second_place["lat"],
            second_place["lng"],
        )

        estimated_minutes = rough_minutes(distance, mode)

        if available_minutes < estimated_minutes:
            warnings.append({
                "passed": False,
                "severity": "warning",
                "activity_ids": [first.get("id"), second.get("id")],
                "message": (
                    f"Only {available_minutes:.1f} minutes available; "
                    f"rough travel estimate is {estimated_minutes:.1f} minutes"
                ),
            })

    return warnings
