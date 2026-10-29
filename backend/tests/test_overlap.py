from app.validation.overlap import check_overlap, find_overlaps


# Test 1: Activities do not overlap
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


# Test 2: Activities overlap
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


# Test 3: Cancelled activities are ignored
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


# Test 4: Identify which activities overlap
def test_find_overlapping_activity_ids():
    activities = [
        {
            "id": "A",
            "start": "2026-11-10T09:00:00",
            "end": "2026-11-10T11:00:00",
            "status": "planned",
        },
        {
            "id": "B",
            "start": "2026-11-10T10:00:00",
            "end": "2026-11-10T12:00:00",
            "status": "planned",
        },
    ]

    conflicts = find_overlaps(activities)

    assert len(conflicts) == 1
    assert conflicts[0]["activity_ids"] == ["A", "B"]
    assert conflicts[0]["passed"] is False
