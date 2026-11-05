
import pytest

from app.models.validation_result import ValidationResult
from app.validation.variety import check_variety


def make_activity(activity_id, start, activity_type, status="planned"):
    return {
        "id": activity_id,
        "start": start,
        "status": status,
        "place": {
            "experience_types": [activity_type] if activity_type else [],
        },
    }


def test_three_consecutive_same_type():
    activities = [
        make_activity("A", "2026-11-10T09:00:00", "culture"),
        make_activity("B", "2026-11-10T11:00:00", "culture"),
        make_activity("C", "2026-11-10T13:00:00", "culture"),
    ]

    result = check_variety(activities)

    assert isinstance(result, ValidationResult)
    assert result.rule == "variety"
    assert result.passed is False
    assert result.severity == "soft"
    assert result.activity_ids == ["A", "B", "C"]


def test_different_activity_types():
    activities = [
        make_activity("A", "2026-11-10T09:00:00", "culture"),
        make_activity("B", "2026-11-10T11:00:00", "nature"),
        make_activity("C", "2026-11-10T13:00:00", "food"),
    ]

    result = check_variety(activities)

    assert result.passed is True
    assert result.severity == "soft"
    assert result.activity_ids == []


def test_two_consecutive_allowed():
    activities = [
        make_activity("A", "2026-11-10T09:00:00", "culture"),
        make_activity("B", "2026-11-10T11:00:00", "culture"),
    ]

    result = check_variety(activities)

    assert result.passed is True


def test_cancelled_activity_ignored():
    activities = [
        make_activity("A", "2026-11-10T09:00:00", "culture"),
        make_activity(
            "B",
            "2026-11-10T10:00:00",
            "nature",
            status="cancelled",
        ),
        make_activity("C", "2026-11-10T11:00:00", "culture"),
        make_activity("D", "2026-11-10T12:00:00", "culture"),
    ]

    result = check_variety(activities)

    assert result.passed is False
    assert result.activity_ids == ["A", "C", "D"]


def test_unknown_category():
    activities = [
        make_activity("A", "2026-11-10T09:00:00", "culture"),
        make_activity("B", "2026-11-10T11:00:00", None),
        make_activity("C", "2026-11-10T13:00:00", "culture"),
    ]

    result = check_variety(activities)

    assert result.passed is False
    assert result.severity == "data-gap"
    assert result.activity_ids == ["B"]


def test_invalid_max_consecutive():
    with pytest.raises(ValueError):
        check_variety([], max_consecutive=0)


def test_four_consecutive_same_type():
    activities = [
        make_activity("A", "2026-11-10T09:00:00", "culture"),
        make_activity("B", "2026-11-10T10:00:00", "culture"),
        make_activity("C", "2026-11-10T11:00:00", "culture"),
        make_activity("D", "2026-11-10T12:00:00", "culture"),
    ]

    result = check_variety(activities)

    assert result.passed is False
    assert result.activity_ids == ["A", "B", "C", "D"]


def test_custom_max_consecutive():
    activities = [
        make_activity("A", "2026-11-10T09:00:00", "culture"),
        make_activity("B", "2026-11-10T10:00:00", "culture"),
        make_activity("C", "2026-11-10T11:00:00", "culture"),
    ]

    result = check_variety(activities, max_consecutive=3)

    assert result.passed is True


def test_case_insensitive_types():
    activities = [
        make_activity("A", "2026-11-10T09:00:00", "Culture"),
        make_activity("B", "2026-11-10T10:00:00", "CULTURE"),
        make_activity("C", "2026-11-10T11:00:00", "culture"),
    ]

    result = check_variety(activities)

    assert result.passed is False
    assert result.activity_ids == ["A", "B", "C"]


def test_trip_identifiers():
    result = check_variety(
        [],
        trip_id="T001",
        version=2,
    )

    assert result.trip_id == "T001"
    assert result.version == 2


def test_missing_type_with_known_violation():
    activities = [
        make_activity("A", "2026-11-10T09:00:00", "culture"),
        make_activity("B", "2026-11-10T10:00:00", "culture"),
        make_activity("C", "2026-11-10T11:00:00", "culture"),
        make_activity("D", "2026-11-10T12:00:00", None),
    ]

    result = check_variety(activities)

    assert result.passed is False
    assert result.severity == "soft"
    assert result.activity_ids == ["A", "B", "C"]


def make_multi_type_activity(activity_id, start, types):
    return {
        "id": activity_id,
        "start": start,
        "status": "planned",
        "place": {"experience_types": types},
    }


def test_sorted_by_real_time_not_text():
    # By text, X (08:00) comes first and gives three "culture" in a row.
    # By real time, X is 16:00 UTC, so the order is Y, Z, F, X: no problem.
    activities = [
        make_activity("X", "2026-11-10T08:00:00-08:00", "culture"),
        make_activity("Y", "2026-11-10T09:00:00+00:00", "culture"),
        make_activity("Z", "2026-11-10T10:00:00+00:00", "culture"),
        make_activity("F", "2026-11-10T12:00:00+00:00", "food"),
    ]

    assert check_variety(activities).passed is True


def test_all_types_are_used():
    activities = [
        make_multi_type_activity("A", "2026-11-10T09:00:00", ["food", "nightlife"]),
        make_multi_type_activity("B", "2026-11-10T11:00:00", ["nightlife"]),
        make_multi_type_activity("C", "2026-11-10T13:00:00", ["music", "nightlife"]),
    ]

    result = check_variety(activities)

    assert result.passed is False
    assert result.activity_ids == ["A", "B", "C"]


def test_run_needs_one_type_shared_by_all():
    # A and B share "food", B and C share "nightlife", but no type is in all three.
    activities = [
        make_multi_type_activity("A", "2026-11-10T09:00:00", ["food"]),
        make_multi_type_activity("B", "2026-11-10T11:00:00", ["food", "nightlife"]),
        make_multi_type_activity("C", "2026-11-10T13:00:00", ["nightlife"]),
    ]

    assert check_variety(activities).passed is True
