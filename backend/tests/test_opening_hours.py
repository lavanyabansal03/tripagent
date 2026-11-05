
import pytest

from app.models.validation_result import ValidationResult
from app.validation.opening_hours import check_opening_hours, check_plan_opening_hours


def monday_hours():
    return [
        {
            "day": "monday",
            "open": "09:00",
            "close": "17:00",
        }
    ]


def test_place_open():
    result = check_opening_hours(
        "2026-11-09T10:00:00-08:00",
        "2026-11-09T12:00:00-08:00",
        monday_hours(),
    )

    assert isinstance(result, ValidationResult)
    assert result.rule == "opening_hours"
    assert result.passed is True
    assert result.severity == "soft"


def test_place_closed():
    result = check_opening_hours(
        "2026-11-09T16:00:00-08:00",
        "2026-11-09T18:00:00-08:00",
        monday_hours(),
    )

    assert result.passed is False
    assert result.severity == "hard"
    assert "outside" in result.message


def test_overnight_opening_hours():
    hours = [
        {
            "day": "monday",
            "open": "18:00",
            "close": "02:00",
            "closes_next_day": True,
        }
    ]

    result = check_opening_hours(
        "2026-11-09T23:00:00-08:00",
        "2026-11-10T01:00:00-08:00",
        hours,
    )

    assert result.passed is True


def test_unknown_hours():
    result = check_opening_hours(
        "2026-11-09T10:00:00-08:00",
        "2026-11-09T12:00:00-08:00",
        None,
    )

    assert result.passed is False
    assert result.severity == "data-gap"


def test_invalid_activity_time():
    with pytest.raises(ValueError):
        check_opening_hours(
            "2026-11-09T12:00:00-08:00",
            "2026-11-09T10:00:00-08:00",
            [],
        )


def test_activity_identifiers():
    result = check_opening_hours(
        "2026-11-09T10:00:00-08:00",
        "2026-11-09T12:00:00-08:00",
        monday_hours(),
        trip_id="T001",
        version=2,
        activity_id="A001",
    )

    assert result.trip_id == "T001"
    assert result.version == 2
    assert result.activity_ids == ["A001"]


def test_empty_hours_means_unknown():
    # docs/contracts.md 5.2: an empty list does not prove a place is closed.
    result = check_opening_hours(
        "2026-11-09T10:00:00-08:00",
        "2026-11-09T12:00:00-08:00",
        [],
    )

    assert result.passed is False
    assert result.severity == "data-gap"


def test_activity_exactly_within_hours():
    result = check_opening_hours(
        "2026-11-09T09:00:00-08:00",
        "2026-11-09T17:00:00-08:00",
        monday_hours(),
    )

    assert result.passed is True


def make_plan_activity(activity_id, start, end, hours, status="planned"):
    return {
        "id": activity_id,
        "status": status,
        "start": start,
        "end": end,
        "place": {"hours": hours},
    }


def test_plan_all_open():
    activities = [
        make_plan_activity(
            "A", "2026-11-09T10:00:00-08:00", "2026-11-09T11:00:00-08:00", monday_hours()
        ),
        make_plan_activity(
            "B", "2026-11-09T13:00:00-08:00", "2026-11-09T14:00:00-08:00", monday_hours()
        ),
    ]

    result = check_plan_opening_hours(activities, trip_id="T001", version=1)

    assert result.rule == "opening_hours"
    assert result.passed is True
    assert result.trip_id == "T001"


def test_plan_closed_beats_unknown():
    activities = [
        make_plan_activity(
            "A", "2026-11-09T18:00:00-08:00", "2026-11-09T19:00:00-08:00", monday_hours()
        ),
        make_plan_activity(
            "B", "2026-11-09T10:00:00-08:00", "2026-11-09T11:00:00-08:00", None
        ),
    ]

    result = check_plan_opening_hours(activities)

    assert result.passed is False
    assert result.severity == "hard"
    assert result.activity_ids == ["A"]


def test_plan_unknown_hours():
    activities = [
        make_plan_activity(
            "A", "2026-11-09T10:00:00-08:00", "2026-11-09T11:00:00-08:00", []
        ),
    ]

    result = check_plan_opening_hours(activities)

    assert result.passed is False
    assert result.severity == "data-gap"
    assert result.activity_ids == ["A"]


def test_plan_ignores_cancelled():
    activities = [
        make_plan_activity(
            "A",
            "2026-11-09T18:00:00-08:00",
            "2026-11-09T19:00:00-08:00",
            monday_hours(),
            status="cancelled",
        ),
    ]

    assert check_plan_opening_hours(activities).passed is True
