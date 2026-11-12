from app.agents.planner import _schedule_days, build_plan_with_repairs, plan_and_validate


def make_place(place_id, name, lat, lng, *, cost=0, hours=None, experience="nature"):
    return {
        "id": place_id,
        "name": name,
        "sources": ["seed"],
        "categories": [experience],
        "experience_types": [experience],
        "lat": lat,
        "lng": lng,
        "address": name,
        "est_cost_low": cost,
        "est_cost_high": cost,
        "cost_basis": "known",
        "hours": hours,
        "retrieved_at": "2026-10-13T00:00:00Z",
    }


def make_trip(**overrides):
    return {
        "trip_id": "trip-1",
        "destination": "Seattle",
        "start_date": "2026-11-09",
        "end_date": "2026-11-09",
        "mode": "walking",
        "max_travel_min": 180,
        "daily_start": "09:00",
        "daily_end": "20:00",
        "budget": None,
        "budget_strictness": "strict",
        "avoid": [],
        **overrides,
    }


def test_seattle_schedule_uses_local_timezone_and_checks_opening_hours():
    place = make_place(
        "museum",
        "Museum",
        47.61,
        -122.33,
        hours=[{"day": "monday", "open": "10:00", "close": "17:00"}],
        experience="culture",
    )

    itinerary, checks = plan_and_validate(make_trip(), [place])
    activity = itinerary["days"][0]["activities"][0]

    assert activity["start"] == "2026-11-09T10:00:00-08:00"
    opening_check = next(check for check in checks if check["rule"] == "opening_hours")
    assert opening_check["passed"] is True


def test_missing_hours_are_reported_for_scheduled_activity():
    place = make_place("park", "Park", 47.61, -122.33, hours=None)
    itinerary, checks = plan_and_validate(make_trip(), [place])

    opening_check = next(check for check in checks if check["rule"] == "opening_hours")
    activity_id = itinerary["days"][0]["activities"][0]["id"]
    assert opening_check["passed"] is False
    assert opening_check["severity"] == "data-gap"
    assert opening_check["activity_ids"] == [activity_id]


def test_places_are_clustered_by_geographic_area():
    places = [
        make_place("a1", "A1", 47.60, -122.33),
        make_place("b1", "B1", 47.68, -122.38),
        make_place("a2", "A2", 47.601, -122.331),
        make_place("b2", "B2", 47.681, -122.381),
        make_place("a3", "A3", 47.602, -122.332),
        make_place("b3", "B3", 47.682, -122.382),
    ]

    buckets = _schedule_days(places, day_count=2)
    first_day_lats = [place["lat"] for place in buckets[0]]
    second_day_lats = [place["lat"] for place in buckets[1]]

    assert len(buckets[0]) == len(buckets[1]) == 3
    assert max(first_day_lats) - min(first_day_lats) < 0.01
    assert max(second_day_lats) - min(second_day_lats) < 0.01


def many_places(count):
    # Close together, so every stop can fit in the 09:00-20:00 day.
    return [
        make_place(f"p{i}", f"Place {i}", 47.60 + i * 0.001, -122.33, experience=kind)
        for i, kind in zip(range(count), ["nature", "culture", "food"] * count, strict=False)
    ]


def test_pace_decides_how_many_stops_a_day_gets():
    # Before, every day had at most 3 stops whatever the pace (seen live: days ending at 2 PM).
    trip = make_trip(end_date="2026-11-10")  # two days
    counts = {}
    for pace in ("relaxed", "moderate", "packed"):
        itinerary, _ = plan_and_validate({**trip, "pace": pace}, many_places(20))
        counts[pace] = [len(day["activities"]) for day in itinerary["days"]]

    assert counts == {"relaxed": [3, 3], "moderate": [4, 4], "packed": [6, 6]}


def test_stops_that_do_not_fit_the_day_do_not_fail_the_trip():
    # Seen live: a packed San Antonio trip ended INFEASIBLE because 6 places were far apart.
    far_apart = [
        make_place(f"p{i}", f"Place {i}", 47.60 + i * 0.05, -122.33, experience=kind)
        for i, kind in zip(range(6), ["nature", "culture", "food"] * 2, strict=True)
    ]
    trip = make_trip(pace="packed", daily_end="13:00")

    itinerary, checks, _, terminal, _ = build_plan_with_repairs(trip, far_apart)

    assert terminal == "PASS"
    assert 0 < len(itinerary["days"][0]["activities"]) < 6
    left_out = next(c for c in checks if c["rule"] == "daily_schedule")
    assert left_out["severity"] == "soft"
    assert left_out["message"].startswith("Not enough time in the day for: ")


def test_unknown_pace_uses_moderate():
    itinerary, _ = plan_and_validate(make_trip(pace=None), many_places(10))

    assert len(itinerary["days"][0]["activities"]) == 4


def test_plan_repair_swaps_closed_place_for_available_candidate():
    closed_monday = [{"day": "sunday", "open": "12:00", "close": "13:00"}]
    places = [
        make_place("closed", "Closed Museum", 47.61, -122.33, hours=closed_monday),
        make_place(
            "open", "Open Park", 47.611, -122.331,
            hours=[{"day": "monday", "open": "09:00", "close": "20:00"}],
        ),
    ]

    itinerary, checks, repairs, terminal, explanation = build_plan_with_repairs(
        make_trip(), places
    )

    assert repairs == 1
    assert terminal == "PASS"
    assert explanation is None
    assert itinerary["days"][0]["activities"][0]["place_id"] == "open"
    assert next(check for check in checks if check["rule"] == "opening_hours")["passed"]


def test_plan_repair_replaces_expensive_stops_until_budget_passes():
    places = [
        make_place("paid-1", "Paid 1", 47.610, -122.330, cost=25),
        make_place("paid-2", "Paid 2", 47.611, -122.331, cost=20),
        make_place("paid-3", "Paid 3", 47.612, -122.332, cost=15),
        make_place("free", "Free Park", 47.613, -122.333, cost=0),
    ]

    itinerary, checks, repairs, terminal, explanation = build_plan_with_repairs(
        make_trip(budget=0), places
    )

    assert terminal == "PASS"
    assert repairs > 0
    assert explanation is None
    assert [
        activity["place_id"]
        for day in itinerary["days"]
        for activity in day["activities"]
    ] == ["free"]
    assert next(check for check in checks if check["rule"] == "budget")["passed"]


def test_l3_stops_after_three_repair_attempts_and_explains_infeasible():
    places = [
        make_place(
            f"closed-{index}",
            f"Closed {index}",
            47.61 + index * 0.0001,
            -122.33,
            hours=[{"day": "sunday", "open": "09:00", "close": "20:00"}],
        )
        for index in range(6)
    ]

    itinerary, checks, repairs, terminal, explanation = build_plan_with_repairs(
        make_trip(), places
    )

    assert repairs <= 3
    assert terminal == "INFEASIBLE"
    assert "infeasible" in explanation.lower()
    assert itinerary["validation"]
    assert any(
        check["severity"] == "hard" and not check["passed"]
        for check in checks
    )
