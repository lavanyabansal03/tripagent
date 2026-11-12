"""The variety warning should read like one clear sentence, not the same one 3 times."""

from app.agents.planner import _variety_message
from app.validation.variety import check_variety


def cafe(activity_id: str, hour: int, day: str = "2026-11-18") -> dict:
    return {
        "id": activity_id,
        "start": f"{day}T{hour:02d}:00:00",
        "status": "planned",
        "place": {"experience_types": ["cafe"]},
    }


def three_cafe_day(day_number: int) -> dict:
    date = f"2026-11-{17 + day_number}"
    return {
        "day": day_number,
        "activities": [cafe(f"d{day_number}-{h}", h, date) for h in (9, 11, 13)],
    }


def test_single_sequence_uses_singular():
    result = check_variety([cafe("a", 9), cafe("b", 11), cafe("c", 13)])
    assert result.message.startswith("Found 1 sequence with")


def test_three_bad_days_give_one_sentence():
    days = [three_cafe_day(1), three_cafe_day(2), three_cafe_day(3)]
    results = [check_variety(day["activities"]) for day in days]
    message = _variety_message(days, results)
    assert message == "Days 1, 2 and 3 have too many activities of the same kind in a row."


def test_one_bad_day():
    days = [three_cafe_day(1), {"day": 2, "activities": []}]
    results = [check_variety(day["activities"]) for day in days]
    assert _variety_message(days, results) == (
        "Day 1 has too many activities of the same kind in a row."
    )


def test_data_gap_sentence_is_not_repeated():
    unknown = {"id": "x", "start": "2026-11-18T09:00:00", "place": {"experience_types": []}}
    days = [
        {"day": 1, "activities": [unknown]},
        {"day": 2, "activities": [dict(unknown, id="y", start="2026-11-19T09:00:00")]},
    ]
    results = [check_variety(day["activities"]) for day in days]
    message = _variety_message(days, results)
    assert message.count("Cannot fully check activity variety") == 1
