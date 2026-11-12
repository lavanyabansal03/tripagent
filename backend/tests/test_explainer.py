"""A7 Explainer (fake LLMs; no network)."""

from app.agents import explainer
from app.agents.explainer import ExplanationShape, Reason, explain
from app.config import MAX_REASON_CHARS


def act(activity_id, name, start, reason=None):
    a = {"id": activity_id, "start": f"2026-11-20T{start}:00-08:00", "place": {"name": name}}
    if reason:
        a["reason"] = reason
    return a


BEFORE = {"days": [{"day": 1, "activities": [
    act("a", "Frye Art Museum", "10:00"),
    act("b", "Storyville", "12:00"),
    act("c", "Park", "15:00"),
    act("k", "Kept Cafe", "17:00"),
]}]}
AFTER = {"days": [{"day": 1, "activities": [
    act("a", "Seattle Art Museum", "10:00"),
    act("b", "Storyville", "13:30", reason="You're running 90 minutes late."),
    act("k", "Kept Cafe", "17:00"),
]}]}
DIFF = {"changed": ["a"], "moved": ["b"], "removed": ["c"], "added": [], "preserved": ["k"]}
REPAIRS = [
    {"activity_id": "a", "reason": "It is closed today.",
     "why": "Closest museum with listed hours."},
    {"activity_id": "c", "reason": "It no longer fits in the day."},
]


def fake_llm(monkeypatch, answer):
    prompts = []

    def ask(prompt, shape):
        prompts.append(prompt)
        return answer

    monkeypatch.setattr(explainer, "ask_json", ask)
    return prompts


def test_without_an_llm_every_change_gets_a_code_reason():
    trigger, reasons, by = explain("a place closed", DIFF, BEFORE, AFTER, REPAIRS)

    assert by == "rules"
    assert trigger == "a place closed"
    assert reasons == {
        "a": "Closest museum with listed hours.",
        "b": "You're running 90 minutes late.",
        "c": "It no longer fits in the day.",
    }
    assert "k" not in reasons  # kept activities get no reason


def test_llm_sentences_are_used_and_only_for_changed_activities(monkeypatch):
    prompts = fake_llm(monkeypatch, ExplanationShape(trigger="the museum closed", reasons=[
        Reason(
            activity_id="a",
            reason="Frye Art Museum is closed, so we picked Seattle Art Museum.",
        ),
        Reason(activity_id="k", reason="We kept this."),          # not changed: ignored
        Reason(activity_id="zzz", reason="Made up."),              # unknown id: ignored
    ]))

    trigger, reasons, by = explain("a place closed", DIFF, BEFORE, AFTER, REPAIRS)

    assert by == "llm"
    assert trigger == "the museum closed"
    assert reasons["a"].startswith("Frye Art Museum is closed")
    assert reasons["b"] == "You're running 90 minutes late."  # filled from code
    assert "k" not in reasons and "zzz" not in reasons
    assert "id a: replaced; was Frye Art Museum" in prompts[0]


def test_sentence_naming_another_place_is_dropped(monkeypatch):
    fake_llm(monkeypatch, ExplanationShape(trigger="x", reasons=[
        Reason(activity_id="b", reason="We moved Storyville after Kept Cafe."),
    ]))

    _, reasons, _ = explain("late", DIFF, BEFORE, AFTER, REPAIRS)

    assert reasons["b"] == "You're running 90 minutes late."


def test_long_sentences_are_cut(monkeypatch):
    fake_llm(monkeypatch, ExplanationShape(trigger="x", reasons=[
        Reason(activity_id="c", reason="word " * 200),
    ]))

    _, reasons, _ = explain("late", DIFF, BEFORE, AFTER, REPAIRS)

    assert len(reasons["c"]) <= MAX_REASON_CHARS


def test_no_changes_means_no_llm_call(monkeypatch):
    def must_not_run(*_args):
        raise AssertionError("nothing to explain")

    monkeypatch.setattr(explainer, "ask_json", must_not_run)
    empty = {"changed": [], "moved": [], "removed": [], "added": [], "preserved": ["k"]}

    assert explain("budget changed", empty, BEFORE, BEFORE, []) == ("budget changed", {}, "rules")
