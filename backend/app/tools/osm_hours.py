"""Turn OpenStreetMap opening hours text into the structured hours our Place model uses.

OpenStreetMap writes hours like "Mo-Fr 07:00-18:00; Sa,Su 08:00-17:00". Our validators
want a list of {day, open, close, closes_next_day}. We only read the common, simple forms.
If the text has anything we do not understand, we return None ("unknown") instead of guessing.
"""

import re

WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
_SHORT = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]

_DAY = r"(?:Mo|Tu|We|Th|Fr|Sa|Su)"
_SPAN = r"\d{1,2}:\d\d-\d{1,2}:\d\d"
# One rule: some days, then "off" or one or more time spans.
# Examples: "Mo-Fr 07:00-18:00", "Sa,Su 08:00-12:00,13:00-17:00", "Su off"
_RULE = re.compile(
    rf"^({_DAY}(?:\s*[-,]\s*{_DAY})*)\s+(off|closed|{_SPAN}(?:\s*,\s*{_SPAN})*)$"
)
# Rules are split by ";". Some data uses ", " between a time and the next day group
# ("Mo-Fr 06:00-17:00, Sa-Su 07:00-13:00"), so split there too, but not inside "Mo,We".
_RULE_SPLIT = re.compile(rf";|(?<=\d),\s*(?={_DAY}\b|PH\b)")


def _expand_days(text: str) -> list[int]:
    """'Mo-We,Sa' -> [0, 1, 2, 5]. Ranges may wrap around the week ('Sa-Mo')."""
    days: list[int] = []
    for part in text.replace(" ", "").split(","):
        if "-" in part:
            first, last = (_SHORT.index(day) for day in part.split("-"))
            length = (last - first) % 7 + 1
            days.extend((first + step) % 7 for step in range(length))
        else:
            days.append(_SHORT.index(part))
    return days


def _clock(text: str) -> str:
    """'7:00' -> '07:00'. Our time type has no 24:00, so midnight closing becomes 23:59."""
    hour, minute = text.split(":")
    if hour == "24" and minute == "00":
        return "23:59"
    return f"{int(hour):02d}:{minute}"


def parse_osm_hours(text: str | None) -> list[dict] | None:
    """Return a list of opening periods, or None when the hours are missing or unclear."""
    if not text or not text.strip():
        return None
    text = text.strip()
    if text == "24/7":
        return [{"day": day, "open": "00:00", "close": "23:59"} for day in WEEKDAYS]

    by_day: dict[int, list[dict]] = {}
    for rule in _RULE_SPLIT.split(text):
        rule = rule.strip()
        if not rule or rule.startswith("PH"):  # public holidays: skip, not needed for a plan
            continue
        match = _RULE.match(rule)
        if match is None:
            return None  # a form we do not understand: say "unknown", never guess
        days, times = match.groups()
        for day in _expand_days(days):
            # In OpenStreetMap a later rule replaces an earlier one for the same day.
            by_day[day] = []
            if times in ("off", "closed"):
                continue
            for span in times.split(","):
                opens, closes = (_clock(part) for part in span.strip().split("-"))
                by_day[day].append(
                    {
                        "day": WEEKDAYS[day],
                        "open": opens,
                        "close": closes,
                        "closes_next_day": closes < opens,  # e.g. a bar open 18:00-02:00
                    }
                )

    periods = [period for day in sorted(by_day) for period in by_day[day]]
    return periods or None
