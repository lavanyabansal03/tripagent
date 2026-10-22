from app.validation.avoid import check_avoid_list


def test_avoid_museum():
    activities = [
        {
            "id": "activity_001",
            "status": "planned",
            "place": {
                "name": "Art Museum",
                "categories": ["museum"],
                "experience_types": ["culture"],
            },
        }
    ]

    conflicts = check_avoid_list(activities, ["museum"])

    assert len(conflicts) == 1
    assert conflicts[0]["passed"] is False
    assert conflicts[0]["activity_ids"] == ["activity_001"]


def test_no_avoid_conflict():
    activities = [
        {
            "id": "activity_002",
            "status": "planned",
            "place": {
                "name": "City Park",
                "categories": ["park"],
                "experience_types": ["nature"],
            },
        }
    ]

    conflicts = check_avoid_list(activities, ["museum"])

    assert conflicts == []


def test_empty_avoid_list():
    activities = [
        {
            "id": "activity_003",
            "status": "planned",
            "place": {"name": "Art Museum"},
        }
    ]

    assert check_avoid_list(activities, []) == []


def test_cancelled_activity_ignored():
    activities = [
        {
            "id": "activity_004",
            "status": "cancelled",
            "place": {"name": "Art Museum"},
        }
    ]

    assert check_avoid_list(activities, ["museum"]) == []


def test_missing_categories():
    activities = [
        {
            "id": "activity_005",
            "status": "planned",
            "place": {"name": "Coffee Shop"},
        }
    ]

    assert check_avoid_list(activities, ["museum"]) == []


def test_case_insensitive_matching():
    activities = [
        {
            "id": "activity_006",
            "status": "planned",
            "place": {
                "name": "Seattle Aquarium",
                "categories": ["AQUARIUM"],
            },
        }
    ]

    conflicts = check_avoid_list(activities, ["Aquarium"])

    assert len(conflicts) == 1
