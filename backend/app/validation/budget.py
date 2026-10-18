def check_budget(activities, budget_max, budget_strictness):
    """
    Validate the estimated cost of a trip.

    Splurges are excluded from the regular budget.
    Unknown costs are reported separately.
    """

    regular_total = 0
    splurge_total = 0
    unknown_costs = 0

    for activity in activities:

        # Ignore cancelled activities
        if activity.get("status") == "cancelled":
            continue

        cost = activity.get("est_cost")

        # Handle unknown costs
        if cost is None:
            unknown_costs += 1
            continue

        # Reject negative costs
        if cost < 0:
            raise ValueError("Activity cost cannot be negative")

        # Separate splurge and regular spending
        if activity.get("splurge", False):
            splurge_total += cost
        else:
            regular_total += cost

    overall_total = regular_total + splurge_total

    valid = True
    warnings = []

    # Check budget restrictions
    if budget_max is not None and budget_strictness != "none":

        if regular_total > budget_max:

            if budget_strictness == "strict":
                valid = False
                warnings.append("Trip exceeds strict budget")

            elif budget_strictness == "flexible":
                warnings.append("Trip exceeds preferred budget")

    # Report missing cost information
    if unknown_costs > 0:
        warnings.append(
            f"{unknown_costs} activities have unknown costs"
        )

    return {
        "valid": valid,
        "regular_total": regular_total,
        "splurge_total": splurge_total,
        "overall_total": overall_total,
        "unknown_costs": unknown_costs,
        "warnings": warnings,
    }
