
import pytest

from app.models.validation_result import ValidationResult
from app.validation.travel_time import check_travel_time


def make_activity(
    activity_id,
    start,
    end,
    lat,
    lng,
    status="planned",
):
    return {
        "id": activity_id,
        "status": status,
        "start": start,
        "end": end,
        "place": {"lat": lat, "lng": lng},
    }


def sample_activities(gap_minutes=60):
    from datetime import datetime, timedelta

    first_end = datetime.fromisoformat(
        "2026-11-10T10:00:00"
    )
    second_start = first_end + timedelta(
        minutes=gap_minutes
    )

    return [
        make_activity(
            "A",
            "2026-11-10T09:00:00",
            "2026-11-10T10:00:00",
            47.6205,
            -122.3493,
        ),
        make_activity(
            "B",
            second_start.isoformat(),
            "2026-11-10T12:00:00",
            47.6097,
            -122.3331,
        ),
    ]


def test_enough_travel_time():
    result = check_travel_time(
        sample_activities(), "walking"
    )

    assert isinstance(result, ValidationResult)
    assert result.rule == "travel_time"
    assert result.passed is True
    assert result.activity_ids == []


def test_insufficient_travel_time():
    result = check_travel_time(
        sample_activities(gap_minutes=1),
        "walking",
    )

    assert result.passed is False
    assert result.severity == "hard"
    assert result.activity_ids == ["A", "B"]
    assert "only 1.0 minutes available" in result.message


def test_missing_coordinates():
    activities = sample_activities()
    activities[1]["place"]["lat"] = None

    result = check_travel_time(activities)

    assert result.passed is False
    assert result.severity == "data-gap"
    assert result.activity_ids == ["A", "B"]
    assert "Coordinates missing" in result.message


def test_cancelled_activity_ignored():
    activities = sample_activities(gap_minutes=1)
    activities[1]["status"] = "cancelled"

    result = check_travel_time(activities)

    assert result.passed is True


def test_same_location():
    activities = sample_activities(gap_minutes=0)
    activities[1]["place"] = activities[0]["place"].copy()

    result = check_travel_time(
        activities,
        "walking",
        max_travel_min=30,
    )

    assert result.passed is True


def test_user_travel_limit_exceeded():
    result = check_travel_time(
        sample_activities(gap_minutes=60),
        "walking",
        max_travel_min=10,
    )

    assert result.passed is False
    assert result.severity == "soft"
    assert result.activity_ids == ["A", "B"]
    assert "10-minute travel limit" in result.message


def test_user_travel_limit_passed():
    result = check_travel_time(
        sample_activities(gap_minutes=60),
        "walking",
        max_travel_min=30,
    )

    assert result.passed is True


def test_hard_issue_takes_priority():
    result = check_travel_time(
        sample_activities(gap_minutes=1),
        "walking",
        max_travel_min=10,
    )

    assert result.passed is False
    assert result.severity == "hard"
    assert "travel limit" in result.message


def test_invalid_travel_limit():
    with pytest.raises(ValueError):
        check_travel_time(
            [],
            max_travel_min=-1,
        )


def test_invalid_mode():
    with pytest.raises(ValueError):
        check_travel_time([], mode="flying")


def test_trip_identifiers():
    result = check_travel_time(
        sample_activities(),
        trip_id="T001",
        version=2,
    )

    assert result.trip_id == "T001"
    assert result.version == 2


def test_empty_activities():
    result = check_travel_time([])

    assert result.passed is True


def test_activities_sorted_by_start():
    activities = sample_activities()
    activities.reverse()

    result = check_travel_time(
        activities,
        "walking",
        max_travel_min=30,
    )

    assert result.passed is True


def test_missing_location_with_known_violation():
    activities = sample_activities(gap_minutes=1)
    activities.append(
        make_activity(
            "C",
            "2026-11-10T13:00:00",
            "2026-11-10T14:00:00",
            None,
            None,
        )
    )

    result = check_travel_time(activities)

    assert result.passed is False
    assert result.severity == "hard"
    assert "Coordinates missing" in result.message


def test_message_names_the_places_not_their_ids():
    # Seen on the live site: "9d9121f2-... to 56d0dc51-...: 33.0 minutes estimated".
    activities = sample_activities(gap_minutes=60)
    activities[0]["place"]["name"] = "Central Park"
    activities[1]["place"]["name"] = "The Metropolitan Museum of Art"

    result = check_travel_time(activities, "walking", max_travel_min=10)

    assert result.message.startswith("Central Park to The Metropolitan Museum of Art: ")
    assert result.activity_ids == ["A", "B"]  # the ids are still there for the app


def test_overnight_is_not_a_trip_between_stops():
    # Seen live: "Takahachi Bakery to Queens Botanical Garden: 62.2 minutes estimated" for
    # the last stop of day 1 and the first stop of day 2.
    last_of_day_1 = make_activity("A", "2026-11-14T16:30:00", "2026-11-14T18:00:00", 40.71, -74.0)
    first_of_day_2 = make_activity("B", "2026-11-15T09:00:00", "2026-11-15T10:15:00", 40.75, -73.83)

    result = check_travel_time([last_of_day_1, first_of_day_2], "walking", max_travel_min=45)

    assert result.passed is True
