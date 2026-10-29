import pytest

from app.validation.variety import check_variety


def make_activity(activity_id, start, activity_type, status="planned"):
    return {
        "id": activity_id,
        "start": start,
        "status": status,
        "place": {
            "experience_types": [activity_type] if activity_type else []
        },
    }


def test_three_consecutive_same_type():
    activities = [
        make_activity("A", "2026-11-10T09:00:00", "culture"),
        make_activity("B", "2026-11-10T11:00:00", "culture"),
        make_activity("C", "2026-11-10T13:00:00", "culture"),
    ]

    warnings = check_variety(activities)

    assert len(warnings) == 1
    assert warnings[0]["severity"] == "warning"
    assert warnings[0]["activity_ids"] == ["A", "B", "C"]


def test_different_activity_types():
    activities = [
        make_activity("A", "2026-11-10T09:00:00", "culture"),
        make_activity("B", "2026-11-10T11:00:00", "nature"),
        make_activity("C", "2026-11-10T13:00:00", "food"),
    ]

    assert check_variety(activities) == []


def test_two_consecutive_allowed():
    activities = [
        make_activity("A", "2026-11-10T09:00:00", "culture"),
        make_activity("B", "2026-11-10T11:00:00", "culture"),
    ]

    assert check_variety(activities) == []


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

    warnings = check_variety(activities)

    assert len(warnings) == 1
    assert warnings[0]["activity_ids"] == ["A", "C", "D"]


def test_unknown_category():
    activities = [
        make_activity("A", "2026-11-10T09:00:00", "culture"),
        make_activity("B", "2026-11-10T11:00:00", None),
        make_activity("C", "2026-11-10T13:00:00", "culture"),
    ]

    assert check_variety(activities) == []


def test_invalid_max_consecutive():
    with pytest.raises(ValueError):
        check_variety([], max_consecutive=0)
