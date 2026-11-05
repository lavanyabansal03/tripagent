"""Deterministic itinerary scheduling and validation for the Planner agent."""

from datetime import UTC, date, datetime, time, timedelta
from typing import Any
from uuid import uuid4

from app.models.validation_result import ValidationResult
from app.tools.base import LatLng, Mode
from app.tools.mock_places import distance_km, rough_minutes
from app.validation.avoid import check_avoid_list
from app.validation.budget import check_budget
from app.validation.opening_hours import check_opening_hours
from app.validation.overlap import check_overlap
from app.validation.travel_time import check_travel_time
from app.validation.variety import check_variety


def _duration(place: dict[str, Any]) -> int:
    types = place.get("experience_types", [])
    if "food" in types or "nightlife" in types:
        return 90
    if "culture" in types or "nature" in types:
        return 75
    return 60


def _schedule_days(places: list[dict[str, Any]], day_count: int) -> list[list[dict[str, Any]]]:
    """Spread candidates over dates and order each day by nearest neighbour."""
    buckets: list[list[dict[str, Any]]] = [[] for _ in range(day_count)]
    # Keep a manageable, varied plan rather than scheduling every search result.
    candidates = places[: day_count * 3]
    for index, place in enumerate(candidates):
        buckets[index % day_count].append(place)

    for bucket in buckets:
        missing_coordinates = any(
            place.get("lat") is None or place.get("lng") is None for place in bucket
        )
        if len(bucket) < 2 or missing_coordinates:
            continue
        ordered = [bucket.pop(0)]
        while bucket:
            current = ordered[-1]
            current_point = LatLng(lat=current["lat"], lng=current["lng"])
            next_place = min(
                bucket,
                key=lambda place: distance_km(current_point, place["lat"], place["lng"]),
            )
            bucket.remove(next_place)
            ordered.append(next_place)
        bucket.extend(ordered)
    return buckets


def _as_time(value: str, fallback: time) -> time:
    try:
        return time.fromisoformat(value)
    except (TypeError, ValueError):
        return fallback


def plan_and_validate(
    trip: dict[str, Any], places: list[dict[str, Any]], *, version: int = 1
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Build a dated itinerary from searched places and run deterministic validators."""
    start_date = date.fromisoformat(trip["start_date"])
    end_date = date.fromisoformat(trip["end_date"])
    if end_date < start_date:
        raise ValueError("End date cannot be before start date")

    trip_id = str(trip.get("trip_id", trip.get("id", "unknown")))
    places = [
        {
            **place,
            "id": place.get("id") or f"place-{index + 1}",
            "name": place.get("name") or f"Place {index + 1}",
            "experience_types": place.get("experience_types", []),
        }
        for index, place in enumerate(places)
    ]
    day_count = (end_date - start_date).days + 1
    daily_start = _as_time(trip.get("daily_start", "09:00"), time(9, 0))
    daily_end = _as_time(trip.get("daily_end", "20:00"), time(20, 0))
    mode: Mode = trip.get("mode", "walking")
    buckets = _schedule_days(places, day_count)
    days: list[dict[str, Any]] = []
    all_activities: list[dict[str, Any]] = []
    unscheduled_places: list[str] = []

    for day_index, (day_date, bucket) in enumerate(
        zip((start_date + timedelta(days=i) for i in range(day_count)), buckets), start=1
    ):
        activities: list[dict[str, Any]] = []
        cursor = datetime.combine(day_date, daily_start, tzinfo=UTC)
        previous: dict[str, Any] | None = None
        for place in bucket:
            travel_min = 0
            if previous is not None:
                if all(
                    item.get(key) is not None
                    for item in (previous, place)
                    for key in ("lat", "lng")
                ):
                    distance = distance_km(
                        LatLng(lat=previous["lat"], lng=previous["lng"]),
                        place["lat"],
                        place["lng"],
                    )
                    travel_min = int(rough_minutes(distance, mode)) + 10
            duration = _duration(place)
            activity_start = cursor + timedelta(minutes=travel_min)
            activity_end = activity_start + timedelta(minutes=duration)
            if activity_end.time().replace(tzinfo=None) > daily_end:
                unscheduled_places.append(place["name"])
                continue
            activity = {
                "id": str(uuid4()),
                "trip_id": trip_id,
                "version": version,
                "day": day_index,
                "place_id": place["id"],
                "start": activity_start.isoformat(),
                "end": activity_end.isoformat(),
                "est_cost": place.get("est_cost_low"),
                "cost_basis": place.get("cost_basis", "unknown"),
                "priority": "medium",
                "purpose_tags": list(place.get("experience_types", [])),
                "status": "planned",
                "place": place,
            }
            activities.append(activity)
            all_activities.append(activity)
            cursor = activity_end + timedelta(minutes=15)
            previous = place

        days.append(
            {
                "day": day_index,
                "date": day_date.isoformat(),
                "activities": activities,
                "legs": [],
                "warnings": [],
            }
        )

    validation: list[ValidationResult] = [
        check_overlap(all_activities, trip_id, version),
        check_budget(
            all_activities,
            trip.get("budget"),
            trip.get("budget_strictness", "strict"),
            trip_id,
            version,
        ),
        check_travel_time(
            all_activities,
            mode,
            trip.get("max_travel_min"),
            trip_id,
            version,
        ),
        check_avoid_list(all_activities, trip.get("avoid", []), trip_id, version),
        check_variety(all_activities, trip_id=trip_id, version=version),
    ]
    if unscheduled_places:
        validation.append(
            ValidationResult(
                id="daily-schedule-check",
                trip_id=trip_id,
                version=version,
                rule="daily_schedule",
                passed=False,
                severity="hard",
                message=(
                    "Daily time limits prevented scheduling: "
                    + ", ".join(unscheduled_places)
                    + "."
                ),
                activity_ids=[],
            )
        )

    for activity in all_activities:
        hours = activity["place"].get("hours")
        if isinstance(hours, list):
            validation.append(
                check_opening_hours(
                    activity["start"], activity["end"], hours, trip_id, version, activity["id"]
                )
            )

    itinerary = {
        "trip_id": trip_id,
        "version": version,
        "days": days,
        "validation": [result.model_dump() for result in validation],
        "score": 1.0 if all(result.passed for result in validation) else 0.5,
        "created_at": datetime.now(UTC).isoformat(),
    }
    return itinerary, [result.model_dump() for result in validation]
