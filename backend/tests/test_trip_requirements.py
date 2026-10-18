import pytest
from app.models.trip_requirements import TripRequirements
from pydantic import ValidationError

# Sample valid trip information
def valid_trip():
    return {
        "trip_id": "trip_001",
        "version": 1,
        "destination": "Seattle",
        "start_date": "2026-11-10",
        "end_date": "2026-11-13",
        "budget_min": 200,
        "budget_max": 500,
        "budget_strictness": "strict",
        "mode": "walking",
        "pace": "relaxed",
        "interests": ["nature", "food"],
        "avoid": ["museums"],
        "tourist_local_ratio": 50,
        "max_travel_min": 30,
        "daily_start": "09:00",
        "daily_end": "18:00",
        "free_text": "I want a relaxing trip.",
        "provenance": {},
    }


# Test 1: Valid trip
def test_valid_trip():
    trip = TripRequirements(**valid_trip())
    assert trip.destination == "Seattle"


# Test 2: Invalid budget range
def test_invalid_budget():
    data = valid_trip()
    data["budget_min"] = 600
    data["budget_max"] = 400

    with pytest.raises(ValidationError):
        TripRequirements(**data)


# Test 3: Invalid dates
def test_invalid_dates():
    data = valid_trip()
    data["start_date"] = "2026-11-15"
    data["end_date"] = "2026-11-10"

    with pytest.raises(ValidationError):
        TripRequirements(**data)


# Test 4: Negative budget
def test_negative_budget():
    data = valid_trip()
    data["budget_max"] = -100

    with pytest.raises(ValidationError):
        TripRequirements(**data)
