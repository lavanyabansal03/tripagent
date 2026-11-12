"""Applying a checked change (plain code)."""

import copy

import pytest

from app.agents.apply_change import ChangeError, apply_change


def activity(activity_id, day, start, end, status="planned", backups=None):
    return {
        "id": activity_id, "day": day, "status": status,
        "start": f"2026-11-2{day}T{start}:00-08:00", "end": f"2026-11-2{day}T{end}:00-08:00",
        "place_id": f"p-{activity_id}", "place": {"id": f"p-{activity_id}", "name": activity_id},
        "backups": backups or [],
    }


def plan():
    backup_place = {"id": "b1", "name": "Backup Cafe", "est_cost_low": 4, "cost_basis": "known"}
    stored = [{"place_id": "b1", "place": backup_place}]
    return {
        "trip_id": "t", "version": 1,
        "days": [
            {"day": 1, "activities": [
                activity("a", 1, "09:00", "10:00"),
                activity("locked", 1, "11:00", "12:00", status="locked"),
                activity("c", 1, "13:00", "14:00", backups=stored),
            ]},
            {"day": 2, "activities": [activity("d", 2, "09:00", "10:00")]},
        ],
    }


REQS = {"budget": 500, "mode": "transit", "avoid": ["Bars"]}


def test_late_moves_only_that_day_and_never_locked_stops():
    before = plan()
    original = copy.deepcopy(before)

    _, after, touched = apply_change("time", {"minutes": 90, "day": 1}, REQS, before)

    day1 = {a["id"]: a for a in after["days"][0]["activities"]}
    assert day1["a"]["start"] == "2026-11-21T10:30:00-08:00"
    assert day1["c"]["end"] == "2026-11-21T15:30:00-08:00"
    assert day1["locked"]["start"] == "2026-11-21T11:00:00-08:00"  # never moved
    assert after["days"][1]["activities"][0]["start"] == "2026-11-22T09:00:00-08:00"
    assert touched == ["a", "c"]
    assert day1["a"]["change_type"] == "moved"
    assert before == original  # the current version is not modified


def test_budget_transport_and_preference_change_the_requirements_only():
    reqs, itinerary, _ = apply_change("budget", {"budget": 300}, REQS, plan())
    assert reqs["budget"] == 300 and itinerary == plan()

    reqs, _, _ = apply_change("transport", {"mode": "walking"}, REQS, plan())
    assert reqs["mode"] == "walking"

    reqs, _, _ = apply_change("preference", {"avoid": ["bars", "museums"]}, REQS, plan())
    assert reqs["avoid"] == ["Bars", "museums"]  # no duplicate, any case
    assert REQS["avoid"] == ["Bars"]  # the original is not modified


def test_closure_marks_the_stop_closed():
    _, after, touched = apply_change("closure", {"activity_id": "c"}, REQS, plan())

    assert after["days"][0]["activities"][2]["unavailable"] is True
    assert touched == ["c"]


def test_swap_uses_a_stored_backup():
    _, after, touched = apply_change("swap", {"activity_id": "c", "backup_id": "b1"}, REQS, plan())

    swapped = after["days"][0]["activities"][2]
    assert swapped["place_id"] == "b1" and swapped["est_cost"] == 4
    assert swapped["change_type"] == "replaced"
    assert swapped["start"] == "2026-11-21T13:00:00-08:00"  # same time slot
    assert touched == ["c"]


@pytest.mark.parametrize(
    "change, payload",
    [
        ("swap", {"activity_id": "c", "backup_id": "not-stored"}),
        ("swap", {"activity_id": "locked", "backup_id": "b1"}),
        ("closure", {"activity_id": "locked"}),
        ("closure", {"activity_id": "nope"}),
        ("weather", {}),
    ],
)
def test_invalid_changes_are_refused(change, payload):
    with pytest.raises(ChangeError):
        apply_change(change, payload, REQS, plan())


def test_swap_between_two_branches_of_one_chain_is_told_apart():
    itinerary = plan()
    target = itinerary["days"][0]["activities"][2]
    target["place"]["name"] = "Starbucks"
    target["backups"] = [{"place_id": "b2", "place": {
        "id": "b2", "name": "Starbucks", "address": "1st & Pike",
    }}]

    _, after, _ = apply_change("swap", {"activity_id": "c", "backup_id": "b2"}, REQS, itinerary)

    reason = after["days"][0]["activities"][2]["reason"]
    assert reason == "You picked a different Starbucks (1st & Pike)."
