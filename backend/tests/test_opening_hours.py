import pytest

from app.validation.opening_hours import check_opening_hours


def test_place_open():
    hours = [
        {
            "day": "monday",
            "open": "09:00",
            "close": "17:00",
        }
    ]

    result = check_opening_hours(
        "2026-11-09T10:00:00-08:00",
        "2026-11-09T12:00:00-08:00",
        hours,
    )

    assert result == "passed"


def test_place_closed():
    hours = [
        {
            "day": "monday",
            "open": "09:00",
            "close": "17:00",
        }
    ]

    result = check_opening_hours(
        "2026-11-09T16:00:00-08:00",
        "2026-11-09T18:00:00-08:00",
        hours,
    )

    assert result == "failed"


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

    assert result == "passed"


def test_unknown_hours():
    result = check_opening_hours(
        "2026-11-09T10:00:00-08:00",
        "2026-11-09T12:00:00-08:00",
        None,
    )

    assert result == "unknown"


def test_invalid_activity_time():
    with pytest.raises(ValueError):
        check_opening_hours(
            "2026-11-09T12:00:00-08:00",
            "2026-11-09T10:00:00-08:00",
            [],
        )
