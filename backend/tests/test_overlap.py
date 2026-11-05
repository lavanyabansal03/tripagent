
from app.models.validation_result import ValidationResult
from app.validation.overlap import check_overlap, find_overlaps


def make_activity(activity_id, start, end, status="planned"):
    return {
        "id": activity_id,
        "start": start,
        "end": end,
        "status": status,
    }


def test_no_overlap():
    activities = [
        make_activity(
            "A",
            "2026-11-10T09:00:00",
            "2026-11-10T10:00:00",
        ),
        make_activity(
            "B",
            "2026-11-10T10:00:00",
            "2026-11-10T11:00:00",
        ),
    ]

    result = check_overlap(activities)

    assert isinstance(result, ValidationResult)
    assert result.rule == "overlap"
    assert result.passed is True
    assert result.severity == "soft"
    assert result.activity_ids == []


def test_overlap_detected():
    activities = [
        make_activity(
            "A",
            "2026-11-10T09:00:00",
            "2026-11-10T11:00:00",
        ),
        make_activity(
            "B",
            "2026-11-10T10:00:00",
            "2026-11-10T12:00:00",
        ),
    ]

    result = check_overlap(activities)

    assert result.passed is False
    assert result.severity == "hard"
    assert result.activity_ids == ["A", "B"]
    assert "1 overlapping activity pairs" in result.message


def test_cancelled_activity_ignored():
    activities = [
        make_activity(
            "A",
            "2026-11-10T09:00:00",
            "2026-11-10T11:00:00",
            "cancelled",
        ),
        make_activity(
            "B",
            "2026-11-10T10:00:00",
            "2026-11-10T12:00:00",
        ),
    ]

    result = check_overlap(activities)

    assert result.passed is True


def test_find_overlapping_activity_ids():
    activities = [
        make_activity(
            "A",
            "2026-11-10T09:00:00",
            "2026-11-10T11:00:00",
        ),
        make_activity(
            "B",
            "2026-11-10T10:00:00",
            "2026-11-10T12:00:00",
        ),
    ]

    conflicts = find_overlaps(activities)

    assert len(conflicts) == 1
    assert isinstance(conflicts[0], ValidationResult)
    assert conflicts[0].activity_ids == ["A", "B"]
    assert conflicts[0].passed is False
    assert conflicts[0].severity == "hard"


def test_multiple_overlaps():
    activities = [
        make_activity(
            "A",
            "2026-11-10T09:00:00",
            "2026-11-10T12:00:00",
        ),
        make_activity(
            "B",
            "2026-11-10T10:00:00",
            "2026-11-10T11:00:00",
        ),
        make_activity(
            "C",
            "2026-11-10T10:30:00",
            "2026-11-10T13:00:00",
        ),
    ]

    conflicts = find_overlaps(activities)
    result = check_overlap(activities)

    assert len(conflicts) == 3
    assert result.passed is False
    assert result.activity_ids == ["A", "B", "C"]


def test_trip_identifiers():
    result = check_overlap(
        [],
        trip_id="T001",
        version=2,
    )

    assert result.trip_id == "T001"
    assert result.version == 2
