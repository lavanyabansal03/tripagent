from app.validation.travel_time import check_travel_time


def make_activity(activity_id, start, end, lat, lng):
    return {
        "id": activity_id,
        "status": "planned",
        "start": start,
        "end": end,
        "place": {"lat": lat, "lng": lng},
    }


def test_enough_travel_time():
    activities = [
        make_activity(
            "A", "2026-11-10T09:00:00", "2026-11-10T10:00:00",
            47.6205, -122.3493,
        ),
        make_activity(
            "B", "2026-11-10T11:00:00", "2026-11-10T12:00:00",
            47.6097, -122.3331,
        ),
    ]

    assert check_travel_time(activities, "walking") == []


def test_insufficient_travel_time():
    activities = [
        make_activity(
            "A", "2026-11-10T09:00:00", "2026-11-10T10:00:00",
            47.6205, -122.3493,
        ),
        make_activity(
            "B", "2026-11-10T10:01:00", "2026-11-10T11:00:00",
            47.6097, -122.3331,
        ),
    ]

    warnings = check_travel_time(activities, "walking")

    assert len(warnings) == 1
    assert warnings[0]["severity"] == "warning"
    assert warnings[0]["activity_ids"] == ["A", "B"]


def test_missing_coordinates():
    activities = [
        make_activity(
            "A", "2026-11-10T09:00:00", "2026-11-10T10:00:00",
            47.6205, -122.3493,
        ),
        make_activity(
            "B", "2026-11-10T11:00:00", "2026-11-10T12:00:00",
            None, None,
        ),
    ]

    warnings = check_travel_time(activities)

    assert len(warnings) == 1
    assert "coordinates missing" in warnings[0]["message"]


def test_cancelled_activity_ignored():
    activities = [
        make_activity(
            "A", "2026-11-10T09:00:00", "2026-11-10T10:00:00",
            47.6205, -122.3493,
        ),
        {
            **make_activity(
                "B", "2026-11-10T10:01:00", "2026-11-10T11:00:00",
                47.6097, -122.3331,
            ),
            "status": "cancelled",
        },
    ]

    assert check_travel_time(activities) == []


def test_same_location():
    activities = [
        make_activity(
            "A", "2026-11-10T09:00:00", "2026-11-10T10:00:00",
            47.6205, -122.3493,
        ),
        make_activity(
            "B", "2026-11-10T10:00:00", "2026-11-10T11:00:00",
            47.6205, -122.3493,
        ),
    ]

    assert check_travel_time(activities) == []
