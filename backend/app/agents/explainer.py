"""A7 Explainer: say what changed and why, using only the real list of changes.

The input is structured: which activities were replaced, moved or removed, their
old and new places and times, and the reason code gave. The LLM turns that into
one short, friendly sentence per activity. Code then keeps only sentences for
activities that really changed, cuts long ones, and drops any sentence that names a
place from elsewhere in the plan. Missing sentences come from plain code, so the
summary never depends on an LLM (and never invents facts).

Output fits the ReplanEvent contract: trigger_text + reasons {activity_id: sentence}.
"""

from typing import Any

from pydantic import BaseModel, Field

from app.agents.llm import ask_json
from app.config import MAX_REASON_CHARS


class Reason(BaseModel):
    activity_id: str
    reason: str = Field(description="One short sentence for the traveller.")


class ExplanationShape(BaseModel):
    trigger: str = Field(description="The change in a few words, e.g. 'you're running late'.")
    reasons: list[Reason] = Field(default_factory=list)


def _activities(itinerary: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {a["id"]: a for day in itinerary.get("days", []) for a in day["activities"]}


def facts(
    diff: dict[str, list[str]],
    before: dict[str, Any],
    after: dict[str, Any],
    repairs: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """One fact row per changed, moved or removed activity (what A7 may talk about)."""
    old, new = _activities(before), _activities(after)
    code_reason = {r["activity_id"]: r.get("why") or r.get("reason") for r in repairs}
    rows = []
    for kind in ("changed", "moved", "removed"):
        for activity_id in diff.get(kind, []):
            was, now = old.get(activity_id, {}), new.get(activity_id, {})
            rows.append({
                "activity_id": activity_id,
                "kind": {"changed": "replaced", "moved": "moved", "removed": "removed"}[kind],
                "old_place": (was.get("place") or {}).get("name"),
                "new_place": (now.get("place") or {}).get("name") if now else None,
                "old_time": (was.get("start") or "")[11:16],
                "new_time": (now.get("start") or "")[11:16] if now else None,
                "why": code_reason.get(activity_id) or now.get("reason") or was.get("reason"),
            })
    return rows


def fallback(trigger: str, rows: list[dict[str, Any]]) -> tuple[str, dict[str, str]]:
    """Plain-code summary: always available, never invents anything."""
    reasons = {}
    for row in rows:
        why = row["why"] or {
            "replaced": "Its place changed.",
            "moved": "Its time changed.",
            "removed": "It no longer fits the plan.",
        }[row["kind"]]
        reasons[row["activity_id"]] = why
    return trigger, reasons


def build_prompt(trigger: str, rows: list[dict[str, Any]]) -> str:
    lines = "\n".join(
        f"- id {r['activity_id']}: {r['kind']}; was {r['old_place']} at {r['old_time']}"
        + (f"; now {r['new_place']} at {r['new_time']}" if r["kind"] != "removed" else "")
        + f"; reason from the planner: {r['why'] or 'not given'}"
        for r in rows
    )
    return f"""Explain a change to a travel plan, briefly and kindly.

What happened: {trigger}

Changes:
{lines}

For each id above write one short sentence (under 25 words) that tells the traveller
what changed and the planner's reason. Use ONLY the facts above. Do not describe the
places (no location, food, quality, prices, hours or opinions). "trigger" repeats
what happened in a few words."""


def explain(
    trigger: str,
    diff: dict[str, list[str]],
    before: dict[str, Any],
    after: dict[str, Any],
    repairs: list[dict[str, Any]],
) -> tuple[str, dict[str, str], str]:
    """Return (trigger_text, reasons by activity id, who wrote it: "llm" or "rules")."""
    rows = facts(diff, before, after, repairs)
    trigger_text, reasons = fallback(trigger, rows)
    if not rows:
        return trigger_text, reasons, "rules"

    answer = ask_json(build_prompt(trigger, rows), ExplanationShape)
    if answer is None:
        return trigger_text, reasons, "rules"

    allowed = {r["activity_id"]: r for r in rows}
    all_names = {
        (a.get("place") or {}).get("name", "")
        for plan in (before, after)
        for a in _activities(plan).values()
    } - {""}
    used_llm = False
    for item in answer.reasons:
        row = allowed.get(item.activity_id)
        text = " ".join(item.reason.split())
        if row is None or not text:
            continue  # an activity that did not change, or an empty answer
        own = {row["old_place"], row["new_place"]} - {None}
        if any(name in text for name in all_names - own):
            continue  # names a place that is not part of this change
        reasons[item.activity_id] = text[:MAX_REASON_CHARS]
        used_llm = True
    # The trigger stays the one code built from the checked change (A5): it is
    # grammatical after "Because ..." and grounded; A7 writes only the reasons.
    return trigger_text, reasons, "llm" if used_llm else "rules"

