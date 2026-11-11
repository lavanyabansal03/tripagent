from app.models.place import OpeningPeriod
from app.tools.osm_hours import parse_osm_hours


def days(periods: list[dict]) -> list[str]:
    return [period["day"] for period in periods]


def test_weekday_range():
    periods = parse_osm_hours("Mo-Fr 07:00-18:00")
    assert days(periods) == ["monday", "tuesday", "wednesday", "thursday", "friday"]
    assert periods[0] == {
        "day": "monday", "open": "07:00", "close": "18:00", "closes_next_day": False,
    }


def test_two_rules_with_semicolon_or_comma():
    semicolon = parse_osm_hours("Mo-Fr 06:00-17:00; Sa-Su 07:00-13:00")
    comma = parse_osm_hours("Mo-Fr 06:00-17:00, Sa-Su 07:00-13:00")  # real Geoapify text
    assert semicolon == comma
    assert len(comma) == 7
    assert comma[-1]["open"] == "07:00"


def test_day_list_and_split_shift():
    periods = parse_osm_hours("Mo,We 09:00-12:00,13:00-17:00")
    assert days(periods) == ["monday", "monday", "wednesday", "wednesday"]


def test_later_rule_wins_and_off_means_closed():
    periods = parse_osm_hours("Mo-Su 10:00-20:00; Su off")
    assert "sunday" not in days(periods)
    assert len(periods) == 6


def test_late_night_and_midnight():
    bar = parse_osm_hours("Fr-Sa 18:00-02:00")
    assert bar[0]["closes_next_day"] is True
    assert parse_osm_hours("Mo 08:00-24:00")[0]["close"] == "23:59"


def test_always_open():
    assert len(parse_osm_hours("24/7")) == 7


def test_unclear_hours_stay_unknown():
    # Never guess: anything we cannot fully read is None ("unknown"), not "closed".
    for text in [None, "", "Mo-Fr 07:00+", "sunrise-sunset", "Mo-Fr 08:00-17:00; Jan off"]:
        assert parse_osm_hours(text) is None


def test_public_holiday_rules_are_skipped():
    assert days(parse_osm_hours("Mo 09:00-17:00; PH off")) == ["monday"]


def test_output_fits_the_shared_model():
    for period in parse_osm_hours("Mo-Fr 07:00-18:00; Sa 22:00-03:00"):
        OpeningPeriod.model_validate(period)
