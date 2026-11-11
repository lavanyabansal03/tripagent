"""Repair fixes only the broken part (SRS US-09, FR-14, FR-16, FR-42; docs/03 5.3)."""

from app.agents import planner
from app.agents.planner import build_plan_with_repairs, plan_and_validate
from app.agents.repair import repair_itinerary, violation_score

MONDAY_OPEN = [{"day": "monday", "open": "08:00", "close": "21:00"}]
SUNDAY_ONLY = [{"day": "sunday", "open": "08:00", "close": "21:00"}]


def place(place_id, lat=47.610, lng=-122.330, *, hours=MONDAY_OPEN, cost=0, kind="culture"):
    return {
        "id": place_id,
        "name": place_id.title(),
        "categories": [kind],
        "experience_types": [kind],
        "lat": lat,
        "lng": lng,
        "est_cost_low": cost,
        "est_cost_high": cost,
        "cost_basis": "known",
        "hours": hours,
    }


def activity(activity_id, where, start, end, *, status="planned", backups=None):
    return {
        "id": activity_id,
        "trip_id": "trip-1",
        "version": 1,
        "day": 1,
        "place_id": where["id"],
        "start": f"2026-11-09T{start}:00-08:00",
        "end": f"2026-11-09T{end}:00-08:00",
        "est_cost": where["est_cost_low"],
        "cost_basis": "known",
        "priority": "medium",
        "purpose_tags": list(where["experience_types"]),
        "status": status,
        "place": where,
        "backups": backups or [],
    }


def trip(**overrides):
    return {
        "trip_id": "trip-1",
        "destination": "Seattle",
        "start_date": "2026-11-09",
        "end_date": "2026-11-09",
        "mode": "walking",
        "max_travel_min": 60,
        "daily_start": "09:00",
        "daily_end": "20:00",
        "budget": None,
        "budget_strictness": "strict",
        "avoid": [],
        **overrides,
    }


def plan_of(*activities):
    return {"trip_id": "trip-1", "version": 1, "days": [{"day": 1, "activities": list(activities)}]}


def snapshot(activity_):
    return (activity_["id"], activity_["place_id"], activity_["start"], activity_["end"])


# --- Only the broken activity changes --------------------------------------


def test_closed_place_is_replaced_and_nothing_else_moves():
    a = activity("a", place("museum-a"), "09:00", "10:00")
    closed = activity("b", place("closed", 47.611, hours=SUNDAY_ONLY), "10:30", "11:30")
    c = activity("c", place("museum-c", 47.612), "12:00", "13:00")
    itinerary = plan_of(a, closed, c)
    before_a, before_c = snapshot(a), snapshot(c)
    spare = place("spare", 47.6111)

    changes = repair_itinerary(trip(), itinerary, [spare])

    assert snapshot(a) == before_a and snapshot(c) == before_c
    assert closed["id"] == "b"  # same activity, same time slot
    assert closed["place_id"] == "spare"
    assert closed["start"] == "2026-11-09T10:30:00-08:00"
    assert closed["end"] == "2026-11-09T11:30:00-08:00"
    assert closed["change_type"] == "replaced"
    assert "Closed" in closed["reason"]
    assert changes == [
        {
            "activity_id": "b",
            "day": 1,
            "change": "replaced",
            "rule": "opening_hours",
            "reason": "It is closed then.",
            "old_place_id": "closed",
            "old_place": "Closed",
            "new_place": "Spare",
        }
    ]


def test_full_loop_keeps_the_unaffected_activities_exactly(monkeypatch):
    """The old loop rebuilt the plan, which gave every activity a new id and time."""
    places = [
        place("open-1", 47.6100),
        place("closed", 47.6101, hours=SUNDAY_ONLY),
        place("open-2", 47.6102),
        place("spare", 47.6103),
    ]
    first_plan = {}

    def remember_first_plan(*args, **kwargs):
        itinerary, checks = plan_and_validate(*args, **kwargs)
        first_plan["kept"] = {
            a["id"]: snapshot(a)
            for a in itinerary["days"][0]["activities"]
            if a["place_id"] != "closed"
        }
        return itinerary, checks

    monkeypatch.setattr(planner, "plan_and_validate", remember_first_plan)

    itinerary, checks, repairs, terminal, _ = build_plan_with_repairs(trip(), places)
    after = {a["id"]: snapshot(a) for a in itinerary["days"][0]["activities"]}

    assert terminal == "PASS" and repairs == 1
    assert first_plan["kept"]
    # Each untouched activity has the same id, place and time as in the first plan.
    for activity_id, before in first_plan["kept"].items():
        assert after[activity_id] == before
    assert itinerary["repairs"][0]["change"] == "replaced"


def test_activity_that_cannot_be_replaced_is_removed_and_recorded():
    a = activity("a", place("museum-a"), "09:00", "10:00")
    closed = activity("b", place("closed", 47.611, hours=SUNDAY_ONLY), "10:30", "11:30")
    itinerary = plan_of(a, closed)

    changes = repair_itinerary(trip(), itinerary, [])

    assert [x["id"] for x in itinerary["days"][0]["activities"]] == ["a"]
    assert changes[0]["change"] == "removed"
    assert changes[0]["new_place"] is None


def test_replacement_keeps_the_purpose():
    closed = activity("b", place("closed", hours=SUNDAY_ONLY, kind="food"), "10:30", "11:30")
    itinerary = plan_of(closed)
    park = place("park", 47.6101, kind="nature")  # nearer, but a different purpose
    cafe = place("cafe", 47.6150, kind="food")

    repair_itinerary(trip(), itinerary, [park, cafe])

    assert closed["place_id"] == "cafe"


def test_stored_backup_is_tried_before_the_search_results():
    backup_place = place("backup", 47.6200)
    closed = activity(
        "b",
        place("closed", hours=SUNDAY_ONLY),
        "10:30",
        "11:30",
        backups=[{"place_id": "backup", "rank": 1, "place": backup_place}],
    )
    itinerary = plan_of(closed)

    repair_itinerary(trip(), itinerary, [place("nearer", 47.6101)])

    assert closed["place_id"] == "backup"


# --- Never touch done or locked activities ---------------------------------


def test_locked_and_done_activities_are_never_changed():
    closed_1 = place("closed-1", hours=SUNDAY_ONLY)
    closed_2 = place("closed-2", 47.611, hours=SUNDAY_ONLY)
    locked = activity("l", closed_1, "09:00", "10:00", status="locked")
    done = activity("d", closed_2, "10:30", "11:30", status="done")
    itinerary = plan_of(locked, done)
    before = [snapshot(locked), snapshot(done)]

    changes = repair_itinerary(trip(), itinerary, [place("spare", 47.6105)])

    assert changes == []
    assert [snapshot(locked), snapshot(done)] == before


def test_budget_repair_skips_a_locked_expensive_activity():
    locked = activity("l", place("pricey", cost=90), "09:00", "10:00", status="locked")
    other = activity("o", place("mid", 47.611, cost=40), "10:30", "11:30")
    itinerary = plan_of(locked, other)

    repair_itinerary(trip(budget=100), itinerary, [place("free", 47.6111, cost=0)])

    assert locked["place_id"] == "pricey"
    assert other["place_id"] == "free"


# --- Overlap and travel ----------------------------------------------------


def test_overlap_moves_the_later_activity_after_the_earlier_one():
    a = activity("a", place("museum-a"), "09:00", "10:30")
    b = activity("b", place("museum-b", 47.6101), "10:00", "11:00")
    itinerary = plan_of(a, b)

    changes = repair_itinerary(trip(), itinerary, [])

    assert (b["start"], b["end"]) == ("2026-11-09T10:45:00-08:00", "2026-11-09T11:45:00-08:00")
    assert b["change_type"] == "moved"
    assert changes[0]["change"] == "moved"
    assert a["start"] == "2026-11-09T09:00:00-08:00"


def test_stop_too_far_to_reach_in_time_is_replaced_with_a_nearer_one():
    a = activity("a", place("museum-a"), "09:00", "10:00")
    far = activity("b", place("far", 47.700), "10:05", "11:00")  # ~10 km walk in 5 minutes
    itinerary = plan_of(a, far)

    repair_itinerary(trip(max_travel_min=180), itinerary, [place("near", 47.6102)])

    assert far["place_id"] == "near"


# --- Loop rules ------------------------------------------------------------


def test_soft_problems_do_not_trigger_a_repair():
    # Two stops ~3.5 km apart: reachable in time (not hard), but over a 10-minute limit (soft).
    places = [place("a", 47.610), place("b", 47.642)]

    itinerary, checks, repairs, terminal, _ = build_plan_with_repairs(
        trip(max_travel_min=10), places
    )

    travel = next(c for c in checks if c["rule"] == "travel_time")
    assert travel["passed"] is False and travel["severity"] == "soft"
    assert repairs == 0
    assert terminal == "PASS"
    assert itinerary["repairs"] == []


def test_a_place_that_failed_is_never_tried_again():
    closed = activity("b", place("closed", hours=SUNDAY_ONLY), "10:30", "11:30")
    itinerary = plan_of(closed)
    itinerary["repairs"] = [{"old_place_id": "spare"}]  # "spare" failed in an earlier try

    repair_itinerary(trip(), itinerary, [place("spare", 47.6101), place("other", 47.6120)])

    assert closed["place_id"] == "other"


def test_loop_stops_when_nothing_can_be_fixed():
    places = [place(f"closed-{i}", 47.61 + i * 0.0001, hours=SUNDAY_ONLY) for i in range(3)]

    itinerary, checks, repairs, terminal, explanation = build_plan_with_repairs(trip(), places)

    assert terminal == "INFEASIBLE"
    assert 1 <= repairs <= 3
    assert "infeasible" in explanation.lower()
    assert itinerary["validation"] == checks


def test_violation_score_counts_hard_as_100_and_soft_as_1():
    checks = [
        {"passed": False, "severity": "hard"},
        {"passed": False, "severity": "soft"},
        {"passed": False, "severity": "data-gap"},
        {"passed": True, "severity": "soft"},
    ]

    assert violation_score(checks) == 101
