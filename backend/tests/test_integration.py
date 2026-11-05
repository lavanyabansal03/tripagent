
from app.models.activity import Activity
from app.models.validation_result import ValidationResult
from app.validation.budget import check_budget
from app.validation.overlap import check_overlap


def make_activity(activity_id, start, end, cost, splurge=False):
    return Activity(
        id=activity_id,
        trip_id="trip_001",
        version=1,
        day=1,
        place_id="place_001",
        start=start,
        end=end,
        est_cost=cost,
        cost_basis="price_level",
        place={"id": "place_001", "name": "Space Needle"},
        splurge=splurge,
    )


def test_models_work_with_validators():
    first = make_activity(
        "activity_001",
        "2026-11-10T09:00:00-08:00",
        "2026-11-10T10:00:00-08:00",
        100,
    )

    second = make_activity(
        "activity_002",
        "2026-11-10T10:00:00-08:00",
        "2026-11-10T12:00:00-08:00",
        400,
        splurge=True,
    )

    activities = [
        first.model_dump(mode="json"),
        second.model_dump(mode="json"),
    ]

    overlap_result = check_overlap(
        activities,
        trip_id="trip_001",
        version=1,
    )

    budget_result = check_budget(
        activities,
        200,
        "strict",
        trip_id="trip_001",
        version=1,
    )

    assert isinstance(overlap_result, ValidationResult)
    assert overlap_result.rule == "overlap"
    assert overlap_result.passed is True
    assert overlap_result.severity == "soft"

    assert isinstance(budget_result, ValidationResult)
    assert budget_result.rule == "budget"
    assert budget_result.passed is True
    assert budget_result.severity == "soft"

    assert "Regular cost: $100" in budget_result.message
    assert "splurges: $400" in budget_result.message
    assert "total: $500" in budget_result.message
