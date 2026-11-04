
import pytest

from app.models.validation_result import ValidationResult
from app.validation.budget import check_budget


def test_strict_budget_within_limit():
    activities = [{"est_cost": 100}, {"est_cost": 150}]
    result = check_budget(activities, 500, "strict")

    assert isinstance(result, ValidationResult)
    assert result.rule == "budget"
    assert result.passed is True
    assert result.severity == "soft"


def test_strict_budget_exceeded():
    result = check_budget([{"est_cost": 600}], 500, "strict")

    assert result.passed is False
    assert result.severity == "hard"
    assert "600" in result.message


def test_flexible_budget():
    result = check_budget([{"est_cost": 600}], 500, "flexible")

    assert result.passed is False
    assert result.severity == "soft"


def test_splurge_excluded():
    activities = [
        {"est_cost": 200, "splurge": False},
        {"est_cost": 400, "splurge": True},
    ]
    result = check_budget(activities, 500, "strict")

    assert result.passed is True
    assert "200" in result.message
    assert "400" in result.message
    assert "600" in result.message


def test_unknown_cost():
    result = check_budget([{"est_cost": None}], 500, "strict")

    assert result.passed is False
    assert result.severity == "data-gap"
    assert "unknown costs" in result.message


def test_negative_cost():
    with pytest.raises(ValueError):
        check_budget([{"est_cost": -50}], 500, "strict")


def test_budget_passed():
    result = check_budget([{"est_cost": 200}], 500, "strict")
    assert result.passed is True


def test_budget_uncertain():
    activities = [
        {"est_cost": 200},
        {"est_cost": None},
    ]
    result = check_budget(activities, 500, "strict")

    assert result.passed is False
    assert result.severity == "data-gap"


def test_budget_failed_even_with_unknown_costs():
    activities = [
        {"est_cost": 600},
        {"est_cost": None},
    ]
    result = check_budget(activities, 500, "strict")

    assert result.passed is False
    assert result.severity == "hard"
    assert "unknown costs" in result.message


def test_cancelled_activity_ignored():
    activities = [
        {"est_cost": 100},
        {"est_cost": 1000, "status": "cancelled"},
    ]
    result = check_budget(activities, 500, "strict")

    assert result.passed is True


def test_trip_identifiers():
    result = check_budget(
        [{"est_cost": 100}],
        500,
        "strict",
        trip_id="T001",
        version=2,
    )

    assert result.trip_id == "T001"
    assert result.version == 2


def test_invalid_strictness():
    with pytest.raises(ValueError):
        check_budget([], 500, "invalid")
