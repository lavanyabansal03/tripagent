"""L4 change pipeline: apply -> repair only what broke -> diff -> explain -> version N+1."""

import copy

from app.agents.planner import plan_and_validate
from app.agents.replan import diff, replan

MONDAY_OPEN = [{"day": "monday", "open": "08:00", "close": "21:00"}]


def place(place_id, lat, kind="culture"):
    return {
        "id": place_id, "name": place_id.title(), "categories": [kind],
        "experience_types": [kind], "lat": lat, "lng": -122.330,
        "est_cost_low": 0, "est_cost_high": 0, "cost_basis": "known", "hours": MONDAY_OPEN,
    }


TRIP = {
    "trip_id": "t1", "destination": "Seattle", "start_date": "2026-11-09",
    "end_date": "2026-11-09", "mode": "walking", "max_travel_min": 60,
    "daily_start": "09:00", "daily_end": "20:00", "budget": None,
    "budget_strictness": "strict", "avoid": [],
}
PLANNED = [place("museum-a", 47.6100), place("museum-b", 47.6102), place("museum-c", 47.6104)]
SPARE = [place("spare", 47.6106)]


def first_plan():
    itinerary, _ = plan_and_validate(TRIP, PLANNED)
    return itinerary


def run(change_type, payload, itinerary=None, trigger="something changed"):
    itinerary = itinerary or first_plan()
    return itinerary, replan(
        change_type=change_type, payload=payload, trigger=trigger, trigger_id="c1",
        trip_id="t1", requirements=TRIP, itinerary=itinerary, places=PLANNED + SPARE,
        versions=[1],
    )


def snapshot(a):
    return (a["id"], a["place_id"], a["start"], a["end"])


def activities(itinerary):
    return [a for day in itinerary["days"] for a in day["activities"]]


def test_closure_replaces_only_that_stop_and_saves_a_new_version():
    before = first_plan()
    original = copy.deepcopy(before)
    closed = activities(before)[1]

    _, result = run("closure", {"activity_id": closed["id"], "day": 1}, before, "it closed")

    after = {a["id"]: a for a in activities(result.itinerary)}
    assert result.itinerary["version"] == 2 and result.event["to_version"] == 2
    assert after[closed["id"]]["place_id"] == "spare"  # replaced in the same slot
    assert after[closed["id"]]["start"] == closed["start"]
    for other in (activities(before)[0], activities(before)[2]):
        assert snapshot(after[other["id"]]) == snapshot(other)  # untouched
    assert result.event["diff"]["changed"] == [closed["id"]]
    assert closed["id"] in result.event["reasons"]
    assert result.terminal == "PASS"
    assert before == original  # version 1 is never modified


def test_late_moves_the_day_and_removes_what_no_longer_fits():
    before = first_plan()
    last = activities(before)[-1]["id"]

    _, result = run("time", {"minutes": 420, "day": 1}, before, "you're running late")

    changes = result.event["diff"]
    assert changes["removed"] == [last]  # only the last stop now ends after 20:00
    assert len(changes["moved"]) == 2 and not changes["changed"]
    assert result.event["reasons"][last] == "It no longer fits in the day."
    assert result.terminal == "PASS"


def test_delay_that_empties_the_day_is_reported_as_infeasible():
    _, result = run("time", {"minutes": 600, "day": 1}, trigger="you're running late")

    assert len(result.event["diff"]["removed"]) == 3
    assert result.terminal == "INFEASIBLE"
    assert "infeasible" in result.explanation.lower()


def test_small_delay_only_moves_activities():
    before = first_plan()

    _, result = run("time", {"minutes": 30, "day": 1}, before)

    assert result.event["diff"]["moved"] == [a["id"] for a in activities(before)]
    assert not result.event["diff"]["removed"]


def test_budget_change_keeps_the_plan_when_it_still_fits():
    _, result = run("budget", {"budget": 300})

    assert result.requirements["budget"] == 300
    assert result.event["diff"]["preserved"] and not result.event["diff"]["changed"]


def test_locked_activities_never_change():
    before = first_plan()
    activities(before)[0]["status"] = "locked"
    locked = copy.deepcopy(activities(before)[0])

    _, result = run("time", {"minutes": 90, "day": 1}, before)

    assert snapshot(activities(result.itinerary)[0]) == snapshot(locked)


def test_swap_uses_the_stored_backup():
    before = first_plan()
    target = activities(before)[2]
    target["backups"] = [{"place_id": "spare", "place": SPARE[0]}]

    _, result = run("swap", {"activity_id": target["id"], "backup_id": "spare"}, before)

    swapped = next(a for a in activities(result.itinerary) if a["id"] == target["id"])
    assert swapped["place_id"] == "spare"
    assert result.event["diff"]["changed"] == [target["id"]]


def test_version_number_is_one_more_than_the_highest():
    before = first_plan()

    result = replan(
        change_type="budget", payload={"budget": 100}, trigger="b", trigger_id="c",
        trip_id="t1", requirements=TRIP, itinerary=before, places=PLANNED, versions=[1, 2, 3],
    )

    assert result.itinerary["version"] == 4  # after an Undo to 1, the next change is 4


def test_diff_lists_added_and_removed():
    before = {"days": [{"activities": [{"id": "a", "place_id": "p", "start": "1"}]}]}
    after = {"days": [{"activities": [{"id": "b", "place_id": "q", "start": "1"}]}]}

    assert diff(before, after) == {
        "changed": [], "moved": [], "preserved": [], "added": ["b"], "removed": ["a"]
    }
