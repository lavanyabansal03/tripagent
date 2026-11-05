
from app.models.validation_result import ValidationResult


def check_budget(
    activities,
    budget_max,
    budget_strictness,
    trip_id="unknown",
    version=0,
):
    """Validate trip costs using the shared ValidationResult format."""

    if budget_strictness not in ("strict", "flexible", "none"):
        raise ValueError("Invalid budget strictness")

    regular_total = 0
    splurge_total = 0
    unknown_costs = 0

    for activity in activities:
        if activity.get("status") == "cancelled":
            continue

        cost = activity.get("est_cost")

        if cost is None:
            unknown_costs += 1
            continue

        if cost < 0:
            raise ValueError("Activity cost cannot be negative")

        if activity.get("splurge", False):
            splurge_total += cost
        else:
            regular_total += cost

    overall_total = regular_total + splurge_total

    passed = True
    severity = "soft"
    message = (
        f"Budget check passed. Regular cost: ${regular_total}; "
        f"splurges: ${splurge_total}; total: ${overall_total}."
    )

    if budget_max is not None and budget_strictness != "none":
        if regular_total > budget_max:
            if budget_strictness == "strict":
                passed = False
                severity = "hard"
                message = (
                    f"Regular cost ${regular_total} exceeds "
                    f"strict budget ${budget_max}."
                )
            else:
                passed = False
                severity = "soft"
                message = (
                    f"Regular cost ${regular_total} exceeds "
                    f"preferred budget ${budget_max}."
                )

    if unknown_costs > 0:
        message += f" {unknown_costs} activities have unknown costs."

        if passed:
            passed = False
            severity = "data-gap"

    return ValidationResult(
        id="budget-check",
        trip_id=trip_id,
        version=version,
        rule="budget",
        passed=passed,
        severity=severity,
        message=message,
        activity_ids=[],
    )
