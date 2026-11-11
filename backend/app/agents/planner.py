"""Deterministic itinerary scheduling and validation for the Planner agent."""

from collections.abc import Callable
from datetime import UTC, date, datetime, time, timedelta
from typing import Any
from uuid import uuid4
from zoneinfo import ZoneInfo

from app.agents.repair import hard_failures, repair_itinerary, violation_score
from app.config import MAX_REPAIR_ITERATIONS
from app.models.validation_result import ValidationResult
from app.tools.base import LatLng, Mode
from app.tools.mock_places import distance_km, rough_minutes
from app.validation.avoid import check_avoid_list
from app.validation.budget import check_budget
from app.validation.opening_hours import check_plan_opening_hours
from app.validation.overlap import check_overlap
from app.validation.travel_time import check_travel_time
from app.validation.variety import check_variety

_DESTINATION_TIMEZONES = {
    "seattle": "America/Los_Angeles",
    "portland": "America/Los_Angeles",
    "san francisco": "America/Los_Angeles",
    "los angeles": "America/Los_Angeles",
    "vancouver": "America/Vancouver",
    "new york": "America/New_York",
    "boston": "America/New_York",
    "chicago": "America/Chicago",
    "denver": "America/Denver",
    "phoenix": "America/Phoenix",
    "honolulu": "Pacific/Honolulu",
    "london": "Europe/London",
    "lisbon": "Europe/Lisbon",
    "paris": "Europe/Paris",
    "rome": "Europe/Rome",
    "oslo": "Europe/Oslo",
    "tokyo": "Asia/Tokyo",
    "sydney": "Australia/Sydney",
}


def _destination_timezone(destination: str) -> ZoneInfo:
    normalized = destination.strip().lower()
    timezone_name = next(
        (zone for city, zone in _DESTINATION_TIMEZONES.items() if city in normalized),
        "UTC",
    )
    return ZoneInfo(timezone_name)


def _duration(place: dict[str, Any]) -> int:
    types = place.get("experience_types", [])
    if "food" in types or "nightlife" in types:
        return 90
    if "culture" in types or "nature" in types:
        return 75
    return 60


def _schedule_days(
    places: list[dict[str, Any]], day_count: int, repair_iteration: int = 0
) -> list[list[dict[str, Any]]]:
    """Cluster places by geographic proximity, then nearest-neighbour order each day."""
    buckets: list[list[dict[str, Any]]] = [[] for _ in range(day_count)]
    candidates = places[: day_count * 3]
    if not candidates:
        return buckets

    def has_coordinates(place: dict[str, Any]) -> bool:
        return place.get("lat") is not None and place.get("lng") is not None

    def distance(first: dict[str, Any], second: dict[str, Any]) -> float:
        if not has_coordinates(first) or not has_coordinates(second):
            return float("inf")
        return distance_km(
            LatLng(lat=first["lat"], lng=first["lng"]), second["lat"], second["lng"]
        )

    located = [place for place in candidates if has_coordinates(place)]
    unlocated = [place for place in candidates if not has_coordinates(place)]
    centers: list[dict[str, Any]] = []
    remaining = list(located)
    if remaining:
        centers.append(remaining.pop(repair_iteration % len(remaining)))
    while remaining and len(centers) < day_count:
        seed = max(
            remaining,
            key=lambda place: min(distance(place, center) for center in centers),
        )
        centers.append(seed)
        remaining.remove(seed)

    for day_index, center in enumerate(centers):
        buckets[day_index].append(center)
    capacity = max(1, (len(candidates) + day_count - 1) // day_count)
    for place in remaining:
        eligible = [i for i, bucket in enumerate(buckets) if len(bucket) < capacity]
        if not eligible:
            eligible = list(range(day_count))
        day_index = min(eligible, key=lambda i: distance(place, centers[i]))
        buckets[day_index].append(place)
    for place in unlocated:
        eligible = [i for i, bucket in enumerate(buckets) if len(bucket) < capacity]
        buckets[(eligible or list(range(day_count)))[0]].append(place)

    for day_index, bucket in enumerate(buckets):
        if len(bucket) < 2 or any(not has_coordinates(place) for place in bucket):
            continue
        center = centers[day_index] if day_index < len(centers) else bucket[0]
        first = min(bucket, key=lambda place: distance(place, center))
        bucket.remove(first)
        ordered = [first]
        while bucket:
            current = ordered[-1]
            nearest = min(bucket, key=lambda place: distance(current, place))
            bucket.remove(nearest)
            ordered.append(nearest)
        buckets[day_index] = ordered
    return buckets


def _as_time(value: str, fallback: time) -> time:
    try:
        return time.fromisoformat(value)
    except (TypeError, ValueError):
        return fallback


def _fit_opening_hours(
    place: dict[str, Any], day_date: date, earliest: datetime, duration: int
) -> datetime:
    """Move an activity to the first known opening window that can fit it."""
    hours = place.get("hours")
    if not isinstance(hours, list) or not hours:
        return earliest
    for period in hours:
        if str(period.get("day", "")).lower() != day_date.strftime("%A").lower():
            continue
        try:
            opening_time = time.fromisoformat(str(period["open"]))
            closing_time = time.fromisoformat(str(period["close"]))
        except (KeyError, TypeError, ValueError):
            continue
        opening = datetime.combine(day_date, opening_time, tzinfo=earliest.tzinfo)
        closing = datetime.combine(day_date, closing_time, tzinfo=earliest.tzinfo)
        if period.get("closes_next_day"):
            closing += timedelta(days=1)
        candidate = max(earliest, opening)
        if candidate + timedelta(minutes=duration) <= closing:
            return candidate
    # Keep it in the plan so check_plan_opening_hours reports the hard violation.
    return earliest


def check_itinerary(
    trip: dict[str, Any], days: list[dict[str, Any]], *, trip_id: str, version: int
) -> list[ValidationResult]:
    """Run the deterministic checks on a day-by-day plan (used again after each repair)."""
    mode: Mode = trip.get("mode", "walking")
    activities = [
        activity
        for day in days
        for activity in day["activities"]
        if activity.get("status") != "cancelled"
    ]
    daily_variety = [
        check_variety(
            day["activities"],
            trip_id=trip_id,
            version=version,
        )
        for day in days
    ]
    variety_failures = [result for result in daily_variety if not result.passed]
    variety_result = (
        ValidationResult(
            id="variety-check",
            trip_id=trip_id,
            version=version,
            rule="variety",
            passed=False,
            severity=variety_failures[0].severity,
            message=" ".join(result.message for result in variety_failures),
            activity_ids=list(
                dict.fromkeys(
                    activity_id
                    for result in variety_failures
                    for activity_id in result.activity_ids
                )
            ),
        )
        if variety_failures
        else check_variety([], trip_id=trip_id, version=version)
    )
    validation: list[ValidationResult] = [
        check_overlap(activities, trip_id, version),
        check_budget(
            activities,
            trip.get("budget"),
            trip.get("budget_strictness", "strict"),
            trip_id,
            version,
        ),
        check_travel_time(
            activities,
            mode,
            trip.get("max_travel_min"),
            trip_id,
            version,
        ),
        check_avoid_list(activities, trip.get("avoid", []), trip_id, version),
        variety_result,
        check_plan_opening_hours(activities, trip_id=trip_id, version=version),
    ]
    if not activities:
        validation.append(
            ValidationResult(
                id="plan-content-check",
                trip_id=trip_id,
                version=version,
                rule="plan_content",
                passed=False,
                severity="hard",
                message="No activities could be scheduled for this trip.",
                activity_ids=[],
            )
        )
    return validation


def plan_and_validate(
    trip: dict[str, Any],
    places: list[dict[str, Any]],
    *,
    version: int = 1,
    repair_iteration: int = 0,
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
            "name": place["name"],
            "experience_types": place.get("experience_types", []),
            "hours": place.get("hours") if isinstance(place.get("hours"), list) else None,
        }
        for index, place in enumerate(places)
        if place.get("name")  # never invent a name (CLAUDE.md "Never invent data")
    ]
    day_count = (end_date - start_date).days + 1
    daily_start = _as_time(trip.get("daily_start", "09:00"), time(9, 0))
    daily_end = _as_time(trip.get("daily_end", "20:00"), time(20, 0))
    destination_timezone = _destination_timezone(str(trip.get("destination", "")))
    mode: Mode = trip.get("mode", "walking")
    buckets = _schedule_days(places, day_count, repair_iteration)
    days: list[dict[str, Any]] = []
    all_activities: list[dict[str, Any]] = []
    unscheduled_places: list[str] = []

    for day_index, (day_date, bucket) in enumerate(
        zip((start_date + timedelta(days=i) for i in range(day_count)), buckets), start=1
    ):
        activities: list[dict[str, Any]] = []
        cursor = datetime.combine(day_date, daily_start, tzinfo=destination_timezone)
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
            activity_start = _fit_opening_hours(
                place, day_date, activity_start, duration
            )
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

    validation = check_itinerary(trip, days, trip_id=trip_id, version=version)
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

    itinerary = {
        "trip_id": trip_id,
        "version": version,
        "days": days,
        "validation": [result.model_dump() for result in validation],
        "score": 1.0 if all(result.passed for result in validation) else 0.5,
        "created_at": datetime.now(UTC).isoformat(),
    }
    return itinerary, [result.model_dump() for result in validation]


def _with_daily_schedule(
    checks: list[dict[str, Any]], first_checks: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Repairs do not change which places did not fit in the day; keep that result."""
    return checks + [c for c in first_checks if c["rule"] == "daily_schedule"]


def _attach_day_warnings(itinerary: dict[str, Any], checks: list[dict[str, Any]]) -> None:
    """Give each day the failed checks about its own activities (contracts: ItineraryDay).

    Checks that name no activity (for example "no activities") stay plan-wide in
    itinerary["validation"]; the screen shows those too.
    """
    for day in itinerary["days"]:
        ids = {activity["id"] for activity in day["activities"]}
        day["warnings"] = [
            check for check in checks if not check["passed"] and ids & set(check["activity_ids"])
        ]


def build_plan_with_repairs(
    trip: dict[str, Any],
    places: list[dict[str, Any]],
    *,
    version: int = 1,
    add_backups: Callable[[dict[str, Any], set[str] | None], int] | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]], int, str, str | None]:
    """L3 loop (docs/03 5.3): Planner -> Backup -> Validator -> Repair.

    Plan once, store backups (so Repair can try them first), then patch only the
    broken activities. Exits: PASS when no hard problem is left; INFEASIBLE after
    MAX_REPAIR_ITERATIONS tries, when a try changes nothing, or when the violation
    score stops improving twice in a row.
    """
    itinerary, first_checks = plan_and_validate(trip, places, version=version)
    if add_backups is not None:
        add_backups(itinerary, None)  # every activity
    checks = first_checks
    itinerary["repairs"] = []
    best_score = violation_score(checks)
    stalls = 0
    iterations = 0

    while hard_failures(checks) and iterations < MAX_REPAIR_ITERATIONS:
        iterations += 1
        changes = repair_itinerary(trip, itinerary, places)
        for change in changes:
            change["iteration"] = iterations
        itinerary["repairs"].extend(changes)
        results = check_itinerary(
            trip, itinerary["days"], trip_id=itinerary["trip_id"], version=version
        )
        checks = _with_daily_schedule([r.model_dump() for r in results], first_checks)
        if not changes:
            break  # nothing more this repair can do
        score = violation_score(checks)
        if score < best_score:
            best_score, stalls = score, 0
        else:
            stalls += 1
            if stalls >= 2:
                break  # not getting better (thrashing guard)

    if add_backups is not None:
        # Only activities that got a new place or time need new backups.
        changed = {
            change["activity_id"]
            for change in itinerary["repairs"]
            if change["change"] in ("replaced", "moved")
        }
        if changed:
            add_backups(itinerary, changed)
    itinerary["validation"] = checks
    itinerary["score"] = 1.0 if all(c["passed"] for c in checks) else 0.5
    _attach_day_warnings(itinerary, checks)
    if not hard_failures(checks):
        return itinerary, checks, iterations, "PASS", None
    explanation = (
        f"Plan remains infeasible after {iterations} repair attempt(s): "
        + " ".join(c["message"] for c in hard_failures(checks))
    )
    return itinerary, checks, iterations, "INFEASIBLE", explanation
