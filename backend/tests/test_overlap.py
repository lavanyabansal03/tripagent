from app.validation.overlap import check_overlap


def test_no_overlap():
    activities = [
        {
            "start": "2026-11-10T09:00:00",
            "end": "2026-11-10T10:00:00",
            "status": "scheduled",
        },
        {
            "start": "2026-11-10T10:00:00",
            "end": "2026-11-10T11:00:00",
            "status": "scheduled",
        },
    ]

    assert check_overlap(activities) is True


def test_overlap_detected():
    activities = [
        {
            "start": "2026-11-10T09:00:00",
            "end": "2026-11-10T11:00:00",
            "status": "scheduled",
        },
        {
            "start": "2026-11-10T10:00:00",
            "end": "2026-11-10T12:00:00",
            "status": "scheduled",
        },
    ]

    assert check_overlap(activities) is False


def test_cancelled_activity_ignored():
    activities = [
        {
            "start": "2026-11-10T09:00:00",
            "end": "2026-11-10T11:00:00",
            "status": "cancelled",
        },
        {
            "start": "2026-11-10T10:00:00",
            "end": "2026-11-10T12:00:00",
            "status": "scheduled",
        },
    ]

    assert check_overlap(activities) is True
