import pytest

from app.validation.budget import check_budget


def test_strict_budget_within_limit():
    activities = [
        {"est_cost": 100},
        {"est_cost": 150},
    ]

    result = check_budget(activities, 500, "strict")

    assert result["valid"] is True
    assert result["regular_total"] == 250


def test_strict_budget_exceeded():
    activities = [{"est_cost": 600}]

    result = check_budget(activities, 500, "strict")

    assert result["valid"] is False


def test_flexible_budget():
    activities = [{"est_cost": 600}]

    result = check_budget(activities, 500, "flexible")

    assert result["valid"] is True
    assert len(result["warnings"]) > 0


def test_splurge_excluded():
    activities = [
        {"est_cost": 200, "splurge": False},
        {"est_cost": 400, "splurge": True},
    ]

    result = check_budget(activities, 500, "strict")

    assert result["valid"] is True
    assert result["regular_total"] == 200
    assert result["splurge_total"] == 400
    assert result["overall_total"] == 600


def test_unknown_cost():
    activities = [{"est_cost": None}]

    result = check_budget(activities, 500, "strict")

    assert result["unknown_costs"] == 1
    assert len(result["warnings"]) > 0


def test_negative_cost():
    activities = [{"est_cost": -50}]

    with pytest.raises(ValueError):
        check_budget(activities, 500, "strict")
