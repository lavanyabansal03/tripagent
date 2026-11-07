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
    """Predictable search results without API calls."""

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
        "backup1",
        "Alternative Coffee Shop",
        ["cafe"],
        10,
        lat=47.6206,
    )

    results = find_backups(
        make_plan(),
        FakePlaceSearch([candidate]),
    )

    assert len(results) == 1
    assert results[0]["backup"]["id"] == "backup1"


def test_rejects_original_place():
    original = make_place(
        "original",
        "Original Coffee Shop",
        ["cafe"],
    )

    results = find_backups(
        make_plan(),
        FakePlaceSearch([original]),
    )

    assert results[0]["backup"] is None


def test_rejects_wrong_purpose():
    candidate = make_place(
        "museum1",
        "Art Museum",
        ["culture"],
    )

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
        "expensive1",
        "Expensive Coffee Shop",
        ["cafe"],
        cost=200,
    )

    results = find_backups(
        make_plan(),
        FakePlaceSearch([candidate]),
    )

    assert results[0]["backup"] is None


def test_rejects_avoid_list_conflict():
    candidate = make_place(
        "bar1",
        "Coffee Bar",
        ["cafe"],
    )

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

    assert len(results) == 1
    assert results[0]["backup"] is None
    assert "No verified backup" in results[0]["reason"]


def test_only_important_activities():
    candidate = make_place(
        "backup1",
        "Alternative Coffee Shop",
        ["cafe"],
    )

    results = find_backups(
        make_plan(priority="low"),
        FakePlaceSearch([candidate]),
    )

    assert results == []


def test_rejects_missing_opening_hours():
    candidate = make_place(
        "backup1",
        "Alternative Coffee Shop",
        ["cafe"],
    )

    candidate["hours"] = None

    results = find_backups(
        make_plan(),
        FakePlaceSearch([candidate]),
    )

    assert results[0]["backup"] is None


def test_selects_closest_valid_backup():
    far = make_place(
        "far",
        "Far Coffee Shop",
        ["cafe"],
        lat=47.6300,
    )

    near = make_place(
        "near",
        "Nearby Coffee Shop",
        ["cafe"],
        lat=47.6206,
    )

    results = find_backups(
        make_plan(),
        FakePlaceSearch([far, near]),
    )

    assert results[0]["backup"]["id"] == "near"
