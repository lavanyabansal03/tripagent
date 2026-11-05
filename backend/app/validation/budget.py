def check_budget(activities, budget_max, budget_strictness):
    """Check trip costs, splurges, and budget limits."""

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

    valid = True
    budget_status = "passed"
    warnings = []

    if budget_strictness not in ("strict", "flexible", "none"):
        raise ValueError("Invalid budget strictness")

    if budget_max is not None and budget_strictness != "none":
        if regular_total > budget_max:
            if budget_strictness == "strict":
                valid = False
                budget_status = "failed"
                warnings.append("Trip exceeds strict budget")
            else:
                budget_status = "warning"
                warnings.append("Trip exceeds preferred budget")

    if unknown_costs > 0:
        warnings.append(
            f"{unknown_costs} activities have unknown costs"
        )

        if budget_status == "passed":
            budget_status = "uncertain"

    return {
        "valid": valid,
        "budget_status": budget_status,
        "regular_total": regular_total,
        "splurge_total": splurge_total,
        "overall_total": overall_total,
        "unknown_costs": unknown_costs,
        "warnings": warnings,
    }
