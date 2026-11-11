"""Tests for the combined TripAgent validation runner."""

from app.models.validation_result import ValidationResult
from app.validation.run_all_checks import run_all_checks


def make_activity(activity_id, start, end, cost):
    return {
        "id": activity_id,
        "trip_id": "T001",
        "version": 1,
        "day": 1,
        "start": start,
        "end": end,
        "est_cost": cost,
        "status": "planned",
        "place": {
            "id": f"place-{activity_id}",
            "name": "Museum",
            "categories": ["museum"],
            "experience_types": ["culture"],
            "lat": 47.6205,
            "lng": -122.3493,
            "hours": [
                {
                    "day": "tuesday",
                    "open": "08:00",
                    "close": "20:00",
                }
            ],
        },
    }


def sample_plan():
    return {
        "trip_id": "T001",
        "version": 1,
        "trip": {
            "budget_max": 200,
            "budget_strictness": "strict",
            "avoid": [],
            "mode": "walking",
            "max_travel_min": 30,
        },
        "days": [
            {
                "day": 1,
                "date": "2026-11-10",
                "activities": [
                    make_activity(
                        "A001",
                        "2026-11-10T09:00:00-08:00",
                        "2026-11-10T11:00:00-08:00",
                        150,
                    ),
                    make_activity(
                        "A002",
                        "2026-11-10T10:00:00-08:00",
                        "2026-11-10T12:00:00-08:00",
                        200,
                    ),
                ],
            }
        ],
    }


def test_returns_validation_results():
    results = run_all_checks(sample_plan())

    assert isinstance(results, list)
    assert all(
        isinstance(result, ValidationResult)
        for result in results
    )


def test_all_six_checks_run():
    results = run_all_checks(sample_plan())

    rules = {result.rule for result in results}

    assert "overlap" in rules
    assert "budget" in rules
    assert "opening_hours" in rules
    assert "travel_time" in rules
    assert "avoid" in rules
    assert "variety" in rules


def test_overlap_and_budget_both_detected():
    """Lavanya's requested integration scenario."""

    results = run_all_checks(sample_plan())

    failures = {
        result.rule: result
        for result in results
        if not result.passed
    }

    assert "overlap" in failures
    assert "budget" in failures

    assert failures["overlap"].severity == "hard"
    assert failures["budget"].severity == "hard"

    assert failures["overlap"].activity_ids == [
        "A001",
        "A002",
    ]


def test_trip_identifiers():
    results = run_all_checks(sample_plan())

    for result in results:
        assert result.trip_id == "T001"
        assert result.version == 1


def test_opening_hours_checked_per_activity():
    results = run_all_checks(sample_plan())

    opening_results = [
        result
        for result in results
        if result.rule == "opening_hours"
    ]

    assert len(opening_results) == 2


def test_missing_budget_reports_data_gap():
    plan = sample_plan()
    plan["trip"].pop("budget_max")

    results = run_all_checks(plan)

    budget_result = next(
        result
        for result in results
        if result.rule == "budget"
    )

    assert budget_result.passed is False
    assert budget_result.severity == "data-gap"


def test_no_avoid_conflict():
    results = run_all_checks(sample_plan())

    avoid_result = next(
        result
        for result in results
        if result.rule == "avoid"
    )

    assert avoid_result.passed is True


def test_missing_opening_hours_reports_data_gap():
    plan = sample_plan()

    plan["days"][0]["activities"][0]["place"]["hours"] = None

    results = run_all_checks(plan)

    opening_results = [
        result
        for result in results
        if result.rule == "opening_hours"
    ]

    assert any(
        result.severity == "data-gap"
        for result in opening_results
    )
