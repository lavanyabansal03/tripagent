import pytest
from pydantic import ValidationError

from app.models.place import Place


def valid_place():
    return {
        "id": "place_001",
        "sources": ["mapbox"],
        "provider_ids": {"mapbox": "12345"},
        "name": "Space Needle",
        "categories": ["landmark"],
        "experience_types": ["landmark"],
        "lat": 47.6205,
        "lng": -122.3493,
        "address": "Seattle, WA",
        "field_provenance": {},
        "retrieved_at": "2026-10-18T12:00:00Z",
    }


def test_valid_place():
    place = Place(**valid_place())
    assert place.name == "Space Needle"


def test_invalid_cost_range():
    data = valid_place()
    data["est_cost_low"] = 100
    data["est_cost_high"] = 50

    with pytest.raises(ValidationError):
        Place(**data)


def test_invalid_coordinates():
    data = valid_place()
    data["lat"] = 100

    with pytest.raises(ValidationError):
        Place(**data)


def test_unknown_information():
    place = Place(**valid_place())

    assert place.hours is None
    assert place.dietary_options is None
    assert place.kid_friendly is None
    assert place.accessibility_status == "unknown"


def test_structured_opening_hours():
    data = valid_place()
    data["hours"] = [
        {
            "day": "monday",
            "open": "09:00",
            "close": "17:00",
            "closes_next_day": False,
        }
    ]

    place = Place(**data)
    assert place.hours[0].day == "monday"
