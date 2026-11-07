"""Integration tests for Backup Agent with Nitin's MockPlaceSearch."""

from app.agents.backup import find_backups
from app.tools.base import LatLng
from app.tools.mock_places import MockPlaceSearch


def make_plan():
    """Create a small plan using an actual Seattle seed place."""

    search = MockPlaceSearch()

    cafes = search.search_places(
        categories=["cafe"],
        limit=20,
    )

    assert len(cafes) >= 2

    original = cafes[0].model_dump(mode="json")

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
                        "place_id": original["id"],
                        "start": "2026-11-10T10:00:00-08:00",
                        "end": "2026-11-10T11:00:00-08:00",
                        "priority": "high",
                        "status": "planned",
                        "est_cost": 15,
                        "place": original,
                        "purpose_tags": ["cafe"],
                    }
                ],
            }
        ],
    }


def test_mock_search_finds_real_seed_candidates():
    """Verify that Nitin's real search implementation works."""

    search = MockPlaceSearch()

    candidates = search.search_places(
        query="coffee",
        categories=["cafe"],
        near=LatLng(
            lat=47.6096,
            lng=-122.3416,
        ),
        radius_min=30,
        mode="walking",
        limit=20,
    )

    assert len(candidates) > 0

    for candidate in candidates:
        assert "cafe" in candidate.categories
        assert candidate.lat is not None
        assert candidate.lng is not None


def test_real_seed_data_has_unknown_hours():
    """Confirm that demo data does not invent opening hours."""

    search = MockPlaceSearch()

    candidates = search.search_places(
        categories=["cafe"],
    )

    assert len(candidates) > 0

    for candidate in candidates:
        assert candidate.hours is None


def test_backup_does_not_invent_opening_hours():
    """The Backup Agent must reject unverifiable candidates."""

    plan = make_plan()

    results = find_backups(
        plan,
        search=MockPlaceSearch(),
    )

    assert len(results) == 1

    assert results[0]["activity_id"] == "A001"
    assert results[0]["backup"] is None
    assert results[0]["reason"]


def test_backup_does_not_invent_prices():
    """Verify that unknown prices remain unknown."""

    search = MockPlaceSearch()

    candidates = search.search_places(
        categories=["cafe"],
    )

    assert len(candidates) > 0

    for candidate in candidates:
        assert candidate.est_cost_low is None
        assert candidate.est_cost_high is None


class EnrichedPlaceSearch:
    """Use real search results with explicitly supplied test data.

    The opening hours and prices below are test fixtures,
    not claims about actual businesses.
    """

    def __init__(self):
        self.search = MockPlaceSearch()

    def search_places(
        self,
        query="",
        near=None,
        categories=None,
        radius_min=None,
        mode="walking",
        limit=20,
    ):
        candidates = self.search.search_places(
            query=query,
            near=near,
            categories=categories,
            radius_min=radius_min,
            mode=mode,
            limit=limit,
        )

        enriched = []

        for candidate in candidates:
            place = candidate.model_dump(mode="json")

            place["hours"] = [
                {
                    "day": "tuesday",
                    "open": "08:00",
                    "close": "20:00",
                }
            ]

            place["est_cost_low"] = 10
            place["est_cost_high"] = 15

            enriched.append(place)

        return enriched


def test_backup_with_complete_candidate_information():
    """Verify selection when search data contains all required fields."""

    plan = make_plan()

    results = find_backups(
        plan,
        search=EnrichedPlaceSearch(),
    )

    assert len(results) == 1

    backup = results[0]["backup"]

    assert backup is not None

    assert backup["id"] != (
        plan["days"][0]["activities"][0]["place"]["id"]
    )

    assert "cafe" in backup["experience_types"]

    assert backup["est_cost_high"] <= 100

    assert isinstance(backup["hours"], list)


def test_replacement_respects_avoid_preferences():
    """Verify that avoid preferences are checked on real search results."""

    plan = make_plan()

    plan["requirements"]["avoid"] = ["cafe"]

    results = find_backups(
        plan,
        search=EnrichedPlaceSearch(),
    )

    assert len(results) == 1
    assert results[0]["backup"] is None
