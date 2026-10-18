import pytest
from pydantic import ValidationError

from app.models.activity import Activity


def valid_activity():
    return {
        "id": "activity_001",
        "trip_id": "trip_001",
        "version": 1,
        "day": 1,
        "place_id": "place_001",
        "start": "2026-11-10T09:00:00-08:00",
        "end": "2026-11-10T11:00:00-08:00",
        "est_cost": 50,
        "cost_basis": "price_level",
        "priority": "medium",
        "place": {"id": "place_001", "name": "Space Needle"},
    }


def test_valid_activity():
    activity = Activity(**valid_activity())
    assert activity.id == "activity_001"


def test_end_before_start():
    data = valid_activity()
    data["end"] = "2026-11-10T08:00:00-08:00"

    with pytest.raises(ValidationError):
        Activity(**data)


def test_negative_cost():
    data = valid_activity()
    data["est_cost"] = -50

    with pytest.raises(ValidationError):
        Activity(**data)


def test_missing_timezone():
    data = valid_activity()
    data["start"] = "2026-11-10T09:00:00"

    with pytest.raises(ValidationError):
        Activity(**data)


def test_splurge_priority():
    data = valid_activity()
    data["splurge"] = True
    data["priority"] = "medium"

    with pytest.raises(ValidationError):
        Activity(**data)
