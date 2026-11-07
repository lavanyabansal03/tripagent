"""Tests for the Backup Agent."""

from app.agents.backup import find_backups


def make_place(
    place_id,
    name,
    experience_types=None,
    cost=10,
    lat=47.6205,
    lng=-122.3493,
    hours=None,
):
    if hours is None:
        hours = [
            {
                "day": "tuesday",
                "open": "08:00",
                "close": "20:00",
            }
        ]

    return {
        "id": place_id,
        "name": name,
        "categories": experience_types or [],
        "experience_types": experience_types or [],
        "lat": lat,
        "lng": lng,
        "est_cost_low": cost,
        "est_cost_high": cost,
        "hours": hours,
    }


def make_plan(priority="high"):
    original = make_place(
        "original",
        "Original Coffee Shop",
        ["cafe"],
        15,
    )

    return {
        "trip_id": "T001",
        "version": 1,
        "requirements": {
            "budget_max": 100,
            "budget_strictness": "strict",
            "avoid": [],
            "must_do": [],
            "mode": "walking",
            "max_travel_min": 30,
        },
        "days": [
            {
                "day": 1,
                "activities": [
                    {
                        "id": "A001",
                        "day": 1,
                        "place_id": "original",
                        "start": "2026-11-10T10:00:00-08:00",
                        "end": "2026-11-10T11:00:00-08:00",
                        "priority": priority,
                        "status": "planned",
                        "est_cost": 15,
                        "place": original,
                        "purpose_tags": ["cafe"],
                    }
                ],
            }
        ],
    }


class FakePlaceSearch:
    def __init__(self, places):
        self.places = places

    def search_places(
        self,
        query="",
        near=None,
        categories=None,
        radius_min=None,
        mode="walking",
        limit=20,
    ):
        return self.places[:limit]


def test_finds_valid_backup():
    candidate = make_place(
        "backup1", "Alternative Coffee Shop", ["cafe"], 10
    )

    results = find_backups(
        make_plan(),
        FakePlaceSearch([candidate]),
    )

    assert results[0]["backup"]["id"] == "backup1"


def test_rejects_original_place():
    candidate = make_place(
        "original", "Original Coffee Shop", ["cafe"]
    )

    results = find_backups(
        make_plan(),
        FakePlaceSearch([candidate]),
    )

    assert results[0]["backup"] is None


def test_rejects_wrong_purpose():
    candidate = make_place("museum1", "Art Museum", ["culture"])

    results = find_backups(
        make_plan(),
        FakePlaceSearch([candidate]),
    )

    assert results[0]["backup"] is None


def test_rejects_closed_place():
    candidate = make_place(
        "closed1",
        "Closed Coffee Shop",
        ["cafe"],
        hours=[
            {
                "day": "tuesday",
                "open": "12:00",
                "close": "18:00",
            }
        ],
    )

    results = find_backups(
        make_plan(),
        FakePlaceSearch([candidate]),
    )

    assert results[0]["backup"] is None


def test_rejects_expensive_backup():
    candidate = make_place(
        "expensive1", "Expensive Coffee Shop", ["cafe"], 200
    )

    results = find_backups(
        make_plan(),
        FakePlaceSearch([candidate]),
    )

    assert results[0]["backup"] is None


def test_rejects_avoid_conflict():
    candidate = make_place("bar1", "Coffee Bar", ["cafe"])

    plan = make_plan()
    plan["requirements"]["avoid"] = ["bar"]

    results = find_backups(
        plan,
        FakePlaceSearch([candidate]),
    )

    assert results[0]["backup"] is None


def test_no_candidates():
    results = find_backups(
        make_plan(),
        FakePlaceSearch([]),
    )

    assert results[0]["backup"] is None
    assert "No verified backup" in results[0]["reason"]


def test_low_priority_not_selected():
    plan = make_plan(priority="low")
    candidate = make_place("backup1", "Coffee Shop", ["cafe"])

    results = find_backups(
        plan,
        FakePlaceSearch([candidate]),
    )

    assert results == []


def test_medium_priority_not_selected_automatically():
    plan = make_plan(priority="medium")
    candidate = make_place("backup1", "Coffee Shop", ["cafe"])

    results = find_backups(
        plan,
        FakePlaceSearch([candidate]),
    )

    assert results == []


def test_medium_priority_with_must_do_place_id():
    plan = make_plan(priority="medium")

    plan["requirements"]["must_do"] = [
        {
            "text": "Original Coffee Shop",
            "place_id": "original",
            "splurge": False,
        }
    ]

    candidate = make_place(
        "backup1",
        "Alternative Coffee Shop",
        ["cafe"],
    )

    results = find_backups(
        plan,
        FakePlaceSearch([candidate]),
    )

    assert len(results) == 1
    assert results[0]["backup"]["id"] == "backup1"


def test_medium_priority_with_must_do_name():
    plan = make_plan(priority="medium")

    plan["requirements"]["must_do"] = [
        {
            "text": "Original Coffee Shop",
            "place_id": None,
            "splurge": False,
        }
    ]

    candidate = make_place(
        "backup1",
        "Alternative Coffee Shop",
        ["cafe"],
    )

    results = find_backups(
        plan,
        FakePlaceSearch([candidate]),
    )

    assert results[0]["backup"]["id"] == "backup1"


def test_unrelated_must_do_not_selected():
    plan = make_plan(priority="medium")

    plan["requirements"]["must_do"] = [
        {
            "text": "Space Needle",
            "place_id": "space-needle",
        }
    ]

    candidate = make_place("backup1", "Coffee Shop", ["cafe"])

    results = find_backups(
        plan,
        FakePlaceSearch([candidate]),
    )

    assert results == []


def test_rejects_missing_hours():
    candidate = make_place("backup1", "Coffee Shop", ["cafe"])
    candidate["hours"] = None

    results = find_backups(
        make_plan(),
        FakePlaceSearch([candidate]),
    )

    assert results[0]["backup"] is None


def test_selects_closest_backup():
    far = make_place(
        "far", "Far Coffee Shop", ["cafe"], lat=47.6300
    )
    near = make_place(
        "near", "Nearby Coffee Shop", ["cafe"], lat=47.6206
    )

    results = find_backups(
        make_plan(),
        FakePlaceSearch([far, near]),
    )

    assert results[0]["backup"]["id"] == "near"


def test_cancelled_activity_ignored():
    plan = make_plan()
    plan["days"][0]["activities"][0]["status"] = "cancelled"

    candidate = make_place("backup1", "Coffee Shop", ["cafe"])

    results = find_backups(
        plan,
        FakePlaceSearch([candidate]),
    )

    assert results == []
