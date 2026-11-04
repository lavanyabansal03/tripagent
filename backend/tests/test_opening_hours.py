
import pytest

from app.models.validation_result import ValidationResult
from app.validation.opening_hours import check_opening_hours


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


def test_empty_hours_means_closed():
    result = check_opening_hours(
        "2026-11-09T10:00:00-08:00",
        "2026-11-09T12:00:00-08:00",
        [],
    )

    assert result.passed is False
    assert result.severity == "hard"


def test_activity_exactly_within_hours():
    result = check_opening_hours(
        "2026-11-09T09:00:00-08:00",
        "2026-11-09T17:00:00-08:00",
        monday_hours(),
    )

    assert result.passed is True
