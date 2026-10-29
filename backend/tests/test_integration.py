from app.models.activity import Activity
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

    # Convert Pydantic objects into dictionaries
    activities = [
        first.model_dump(mode="json"),
        second.model_dump(mode="json"),
    ]

    overlap_result = check_overlap(activities)
    budget_result = check_budget(activities, 200, "strict")

    assert overlap_result is True
    assert budget_result["valid"] is True
    assert budget_result["regular_total"] == 100
    assert budget_result["splurge_total"] == 400
    assert budget_result["overall_total"] == 500
