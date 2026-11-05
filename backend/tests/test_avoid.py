
from app.models.validation_result import ValidationResult
from app.validation.avoid import check_avoid_list


def make_activity(
    activity_id,
    name,
    categories=None,
    experience_types=None,
    status="planned",
):
    return {
        "id": activity_id,
        "status": status,
        "place": {
            "name": name,
            "categories": categories or [],
            "experience_types": experience_types or [],
        },
    }


def test_avoid_museum():
    activities = [
        make_activity("A001", "Art Museum", ["museum"])
    ]

    result = check_avoid_list(activities, ["museum"])

    assert isinstance(result, ValidationResult)
    assert result.rule == "avoid"
    assert result.passed is False
    assert result.severity == "hard"
    assert result.activity_ids == ["A001"]


def test_no_avoid_conflict():
    activities = [
        make_activity("A002", "City Park", ["park"])
    ]

    result = check_avoid_list(activities, ["museum"])

    assert result.passed is True
    assert result.activity_ids == []


def test_empty_avoid_list():
    activities = [
        make_activity("A003", "Art Museum")
    ]

    result = check_avoid_list(activities, [])

    assert result.passed is True


def test_cancelled_activity_ignored():
    activities = [
        make_activity(
            "A004",
            "Art Museum",
            status="cancelled",
        )
    ]

    result = check_avoid_list(activities, ["museum"])

    assert result.passed is True


def test_missing_categories():
    activities = [
        make_activity("A005", "Coffee Shop")
    ]

    result = check_avoid_list(activities, ["museum"])

    assert result.passed is True


def test_case_insensitive_matching():
    activities = [
        make_activity(
            "A006",
            "Seattle Aquarium",
            ["AQUARIUM"],
        )
    ]

    result = check_avoid_list(activities, ["Aquarium"])

    assert result.passed is False
    assert result.severity == "hard"


def test_plural_avoid_preference():
    activities = [
        make_activity("A007", "Art Museum", ["museum"])
    ]

    result = check_avoid_list(activities, ["museums"])

    assert result.passed is False
    assert result.activity_ids == ["A007"]


def test_bar_does_not_match_barnes():
    activities = [
        make_activity("A008", "Barnes & Noble")
    ]

    result = check_avoid_list(activities, ["bar"])

    assert result.passed is True


def test_bar_matches_whole_word():
    activities = [
        make_activity("A009", "Rooftop Bar")
    ]

    result = check_avoid_list(activities, ["bar"])

    assert result.passed is False
    assert result.activity_ids == ["A009"]


def test_coffee_shop_phrase():
    activities = [
        make_activity("A010", "Downtown Coffee Shop")
    ]

    result = check_avoid_list(activities, ["coffee shop"])

    assert result.passed is False


def test_phrase_must_be_consecutive():
    activities = [
        make_activity("A011", "Coffee Roastery and Gift Shop")
    ]

    result = check_avoid_list(activities, ["coffee shop"])

    assert result.passed is True


def test_multiple_conflicts():
    activities = [
        make_activity("A012", "Art Museum"),
        make_activity("A013", "Rooftop Bar"),
    ]

    result = check_avoid_list(
        activities,
        ["museum", "bar"],
    )

    assert result.passed is False
    assert result.severity == "hard"
    assert result.activity_ids == ["A012", "A013"]


def test_missing_place_information():
    activities = [
        {
            "id": "A014",
            "status": "planned",
            "place": None,
        }
    ]

    result = check_avoid_list(activities, ["museum"])

    assert result.passed is False
    assert result.severity == "data-gap"
    assert result.activity_ids == ["A014"]


def test_trip_identifiers():
    result = check_avoid_list(
        [],
        ["museum"],
        trip_id="T001",
        version=2,
    )

    assert result.trip_id == "T001"
    assert result.version == 2
