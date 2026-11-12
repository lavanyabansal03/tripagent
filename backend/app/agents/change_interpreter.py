"""A5 Change Interpreter: turn "I'm 90 minutes late" into a checked, typed change.

The LLM proposes a change (type + details); code checks every field against the
real plan (the place id must exist on that day, the delay must be in range, ...).
When the change is unclear, A5 asks ONE question instead of guessing (NEEDS_USER).
Quick buttons send a typed change and skip the LLM. Without an LLM answer, simple
word rules are used, so changes still work when both LLMs are down.

Supported: time (running late), budget, closure, transport, preference (avoid).
Not supported yet: adding new stops ("coffee on the way") and weather.
"""

import re
from dataclasses import dataclass, field
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.agents.llm import ask_json
from app.config import MAX_DELAY_MINUTES

ChangeType = Literal["time", "budget", "closure", "transport", "preference", "unknown"]
Mode = Literal["walking", "transit", "driving", "cycling"]
MODES = ("walking", "transit", "driving", "cycling")
PROTECTED_STATUSES = {"done", "locked", "cancelled"}

# docs/06 "adjust.needsClarification"
GENERIC_QUESTION = (
    "We didn't catch what changed. Try something like \"I'm 1 hour late\" or \"skip museums\"."
)
NOT_SUPPORTED_ADD = "Adding new stops on the way isn't supported yet."


class ChangeShape(BaseModel):
    type: ChangeType = Field(description="What changed. Use 'unknown' if you are not sure.")
    minutes: int | None = Field(None, description="time: how many minutes late.")
    budget: float | None = Field(None, description="budget: the new total budget in dollars.")
    activity_id: str | None = Field(None, description="closure: the id of the closed stop.")
    mode: Mode | None = Field(None, description="transport: the new way of getting around.")
    avoid: list[str] = Field(default_factory=list, description="preference: things to skip.")
    question: str | None = Field(None, description="One short question when unsure.")
    trigger: str = Field("", description="The change in the traveller's words, short.")


@dataclass
class Interpretation:
    status: Literal["ok", "needs_clarification"]
    type: ChangeType
    payload: dict[str, Any] = field(default_factory=dict)
    trigger: str = ""
    question: str | None = None
    source: Literal["llm", "rules", "typed"] = "rules"


def day_activities(itinerary: dict[str, Any], day: int) -> list[dict[str, Any]]:
    """Activities on `day` that still count (not cancelled)."""
    for plan_day in itinerary.get("days", []):
        if plan_day.get("day") == day:
            return [a for a in plan_day["activities"] if a.get("status") != "cancelled"]
    return []


def _ask(question: str, change_type: ChangeType = "unknown", source="rules") -> Interpretation:
    return Interpretation("needs_clarification", change_type, question=question, source=source)


# --- code checks every proposed change -------------------------------------------


def validate(
    shape: ChangeShape, itinerary: dict[str, Any], day: int, source="llm"
) -> Interpretation:
    """Keep only a change that fits the real plan; otherwise ask one question."""
    stops = day_activities(itinerary, day)
    if shape.type == "time":
        if shape.minutes is None or not 1 <= shape.minutes <= MAX_DELAY_MINUTES:
            return _ask("How many minutes late are you?", "time", source)
        trigger = shape.trigger or f"you're running {shape.minutes} minutes late"
        return Interpretation(
            "ok", "time", {"minutes": shape.minutes, "day": day}, trigger, source=source
        )
    if shape.type == "budget":
        if shape.budget is None or shape.budget < 0:
            return _ask("What is your new budget?", "budget", source)
        trigger = shape.trigger or f"your budget is now ${shape.budget:g}"
        return Interpretation("ok", "budget", {"budget": shape.budget}, trigger, source=source)
    if shape.type == "closure":
        match = next((a for a in stops if a.get("id") == shape.activity_id), None)
        if match is None:
            return _ask(_which_place_question(stops), "closure", source)
        if match.get("status") in PROTECTED_STATUSES:
            name = match["place"].get("name")
            return _ask(f"{name} is locked or done. Unlock it first if you want it changed.",
                        "closure", source)
        name = match["place"].get("name")
        trigger = shape.trigger or f"{name} is closed today"
        payload = {"activity_id": match["id"], "day": day}
        return Interpretation("ok", "closure", payload, trigger, source=source)
    if shape.type == "transport":
        if shape.mode not in MODES:
            return _ask("How will you get around: walking, transit, driving or cycling?",
                        "transport", source)
        trigger = shape.trigger or f"you switched to {shape.mode}"
        return Interpretation("ok", "transport", {"mode": shape.mode}, trigger, source=source)
    if shape.type == "preference":
        avoid = [a.strip().lower() for a in shape.avoid if a and a.strip()]
        if not avoid:
            return _ask("What would you like to skip?", "preference", source)
        trigger = shape.trigger or f"you want to skip {', '.join(avoid)}"
        return Interpretation("ok", "preference", {"avoid": avoid}, trigger, source=source)
    return _ask(shape.question or GENERIC_QUESTION, "unknown", source)


def _which_place_question(stops: list[dict[str, Any]]) -> str:
    names = [a["place"].get("name") for a in stops if a.get("status") not in PROTECTED_STATUSES]
    if not names:
        return "Which place is closed? We couldn't find it in today's plan."
    return "Which place is closed: " + " or ".join(names[:4]) + "?"


# --- quick buttons: typed changes, no LLM ------------------------------------------


def from_typed(typed: dict[str, Any], itinerary: dict[str, Any], day: int) -> Interpretation:
    payload = typed.get("payload") or {}
    change_type = typed.get("type")
    if change_type == "preference" and (payload.get("interests") or payload.get("along_route")):
        return _ask(NOT_SUPPORTED_ADD, "preference", "typed")
    shape = ChangeShape(
        type=change_type if change_type in ("time", "budget", "closure", "transport",
                                            "preference") else "unknown",
        minutes=payload.get("minutes"),
        budget=payload.get("budget"),
        activity_id=payload.get("activity_id"),
        mode=payload.get("mode") if payload.get("mode") in MODES else None,
        avoid=list(payload.get("avoid") or []),
    )
    return validate(shape, itinerary, day, source="typed")


# --- simple word rules (fallback when no LLM answers) ------------------------------

_LATE = re.compile(r"\b(late|delay|delayed|behind|running behind)\b")
_DURATION = re.compile(r"(\d+(?:\.\d+)?)\s*(minutes?|mins?|hours?|hrs?|h)\b")
_NUMBER = re.compile(r"\$?\s?(\d{2,6}(?:\.\d{1,2})?)")


def rule_based(text: str, itinerary: dict[str, Any], day: int) -> ChangeShape:
    lower = text.lower()
    stops = day_activities(itinerary, day)

    if re.search(r"\b(closed|closes|shut|shuts|not open)\b", lower):
        return ChangeShape(type="closure", activity_id=_find_stop(lower, stops))

    if _LATE.search(lower):
        minutes = None
        duration = _DURATION.search(lower)
        if duration:
            value = float(duration.group(1))
            minutes = int(value * 60) if duration.group(2).startswith("h") else int(value)
        elif re.search(r"\ban hour\b", lower):
            minutes = 60
        elif re.search(r"\bhalf an hour\b", lower):
            minutes = 30
        return ChangeShape(type="time", minutes=minutes)

    if re.search(r"\b(budget|cheaper|money|spend)\b|\$", lower):
        number = _NUMBER.search(lower)
        return ChangeShape(type="budget", budget=float(number.group(1)) if number else None)

    for pattern, mode in (
        (r"\bwalk", "walking"),
        (r"\b(transit|bus|train|metro|subway|tram)\b", "transit"),
        (r"\b(drive|driving|car|taxi|uber)\b", "driving"),
        (r"\b(bike|cycling|cycle|bicycle)\b", "cycling"),
    ):
        if re.search(pattern, lower):
            return ChangeShape(type="transport", mode=mode)

    skip = re.search(r"\b(?:skip|avoid|no more|no)\s+([a-z][a-z ]{2,30})", lower)
    if skip:
        return ChangeShape(type="preference", avoid=[skip.group(1).strip().split(" and ")[0]])

    return ChangeShape(type="unknown")


def _find_stop(lower: str, stops: list[dict[str, Any]]) -> str | None:
    """The one stop the text names (by a name word or its kind); None if 0 or 2+ match."""
    words = set(re.findall(r"[a-z]{4,}", lower))
    matches = []
    for activity in stops:
        place = activity["place"]
        labels = set(re.findall(r"[a-z]{4,}", (place.get("name") or "").lower()))
        kinds = {str(k).lower() for k in (place.get("categories") or [])}
        kinds |= {str(k).lower() for k in (place.get("experience_types") or [])}
        kinds |= {k.rstrip("s") for k in kinds}
        if words & labels or {w.rstrip("s") for w in words} & kinds:
            matches.append(activity)
    return matches[0]["id"] if len(matches) == 1 else None


# --- the LLM path --------------------------------------------------------------------


def build_prompt(
    text: str, itinerary: dict[str, Any], requirements: dict[str, Any], day: int
) -> str:
    lines = "\n".join(
        f"- id {a['id']} | {a['place'].get('name')} | {a['start'][11:16]}-{a['end'][11:16]}"
        f" | {', '.join(a.get('purpose_tags') or []) or 'unknown'}"
        f"{' | LOCKED' if a.get('status') in PROTECTED_STATUSES else ''}"
        for a in day_activities(itinerary, day)
    )
    return f"""A traveller says what changed during their trip. Turn it into one change.

Traveller's message: "{text}"

Today's stops (day {day}):
{lines or "- (none)"}

Current budget: {requirements.get("budget")}; getting around by: {requirements.get("mode")}.

Change types:
- time: they are late; give minutes (hours x 60).
- budget: a new total budget in dollars.
- closure: one stop above is closed; give its exact id from the list.
- transport: walking, transit, driving or cycling.
- preference: things they want to skip (short words).
- unknown: anything else, or when you are not sure. Then write ONE short question.

Use only ids from the list. Do not invent places, numbers or details.
"trigger" repeats the change in a few of the traveller's words."""


def interpret(
    *,
    text: str | None,
    typed: dict[str, Any] | None,
    itinerary: dict[str, Any],
    requirements: dict[str, Any],
    day: int,
) -> Interpretation:
    """A typed change (quick button) or free text -> a checked change, or one question."""
    if typed:
        return from_typed(typed, itinerary, day)
    text = (text or "").strip()
    if not text:
        return _ask(GENERIC_QUESTION)
    if re.search(r"\b(on the way|add (a|an|some)|stop for)\b", text.lower()):
        return _ask(NOT_SUPPORTED_ADD, "preference")

    shape = ask_json(build_prompt(text, itinerary, requirements, day), ChangeShape)
    if shape is not None:
        result = validate(shape, itinerary, day, source="llm")
        if result.status == "ok":
            return result
        llm_question = result
    else:
        llm_question = None

    # No usable LLM answer: try the word rules before asking.
    ruled = validate(rule_based(text, itinerary, day), itinerary, day, source="rules")
    if ruled.status == "ok":
        return ruled
    return llm_question or ruled
