"""Tests for the NVIDIA backup LLM and the Gemini -> NVIDIA order. No real requests."""

import json

import pytest

from app.agents import nvidia_llm, preferences_reader
from app.agents.nvidia_llm import NvidiaError, ask_nvidia_for_json
from app.agents.preferences import Preferences, build_prompt
from app.config import NVIDIA_TIMEOUT_SECONDS, settings

SCHEMA = Preferences.model_json_schema()


class FakeResponse:
    def __init__(self, status_code, content=""):
        self.status_code = status_code
        self._content = content

    def json(self):
        return {"choices": [{"message": {"content": self._content}}]}


def fake_post(*answers):
    """A stand-in for httpx.post that returns the given answers in order."""
    calls = []
    queue = list(answers)

    def post(url, **kwargs):
        calls.append((url, kwargs))
        return queue.pop(0)

    return post, calls


@pytest.fixture
def nvidia_key(monkeypatch):
    monkeypatch.setattr(settings, "NVIDIA_API_KEY", "test-key")


def test_sends_prompt_with_key_model_and_time_limit(nvidia_key):
    post, calls = fake_post(FakeResponse(200, '{"interests": ["coffee"]}'))

    answer = ask_nvidia_for_json("hello", SCHEMA, post=post)

    assert answer == {"interests": ["coffee"]}
    url, kwargs = calls[0]
    assert url.endswith("/chat/completions")
    assert kwargs["headers"]["Authorization"] == "Bearer test-key"
    assert kwargs["json"]["model"] == settings.NVIDIA_MODEL
    assert kwargs["json"]["messages"][1]["content"] == "hello"
    assert kwargs["timeout"] == NVIDIA_TIMEOUT_SECONDS


def test_reads_json_inside_code_fences_and_think_notes(nvidia_key):
    text = '<think>hmm {"x": 1}</think>\n```json\n{"interests": ["museums"]}\n```'
    post, _ = fake_post(FakeResponse(200, text))

    assert ask_nvidia_for_json("hi", SCHEMA, post=post) == {"interests": ["museums"]}


def test_retries_when_busy_then_succeeds(nvidia_key):
    post, calls = fake_post(FakeResponse(429), FakeResponse(503), FakeResponse(200, "{}"))
    waits = []

    assert ask_nvidia_for_json("hi", SCHEMA, post=post, sleep=waits.append) == {}
    assert len(calls) == 3
    assert waits == [2, 4]


def test_gives_up_after_max_tries(nvidia_key):
    post, calls = fake_post(*[FakeResponse(503)] * nvidia_llm.MAX_TRIES)

    with pytest.raises(NvidiaError):
        ask_nvidia_for_json("hi", SCHEMA, post=post, sleep=lambda _s: None)
    assert len(calls) == nvidia_llm.MAX_TRIES


def test_does_not_retry_a_bad_request(nvidia_key):
    post, calls = fake_post(FakeResponse(401))

    with pytest.raises(NvidiaError):
        ask_nvidia_for_json("hi", SCHEMA, post=post)
    assert len(calls) == 1


@pytest.mark.parametrize("text", ["no json here", "{not: valid}"])
def test_answer_without_valid_json_is_an_error(nvidia_key, text):
    post, _ = fake_post(FakeResponse(200, text))

    with pytest.raises(NvidiaError):
        ask_nvidia_for_json("hi", SCHEMA, post=post)


def test_no_key_means_no_request():
    with pytest.raises(NvidiaError):
        ask_nvidia_for_json("hi", SCHEMA, post=lambda *a, **k: pytest.fail("called"))


def test_nvidia_uses_kalebs_prompt(nvidia_key, monkeypatch):
    seen = {}

    def fake_ask(prompt, schema):
        seen["prompt"] = prompt
        return {"interests": ["coffee"], "max_travel_min": 20}

    monkeypatch.setattr(preferences_reader, "ask_nvidia_for_json", fake_ask)

    result = preferences_reader.read_with_nvidia("I love coffee")

    assert seen["prompt"] == build_prompt("I love coffee")
    assert result == Preferences(interests=["coffee"], max_travel_min=20)


def test_nvidia_answer_that_breaks_the_schema_is_rejected(nvidia_key, monkeypatch):
    monkeypatch.setattr(
        preferences_reader,
        "ask_nvidia_for_json",
        lambda _p, _s: {"budget_level": "very cheap"},
    )

    with pytest.raises(ValueError):
        preferences_reader.read_with_nvidia("cheap trip")


def test_nvidia_null_means_not_stated(nvidia_key, monkeypatch):
    # Seen live: {"avoid": null} failed the whole note, so nothing from it was used.
    monkeypatch.setattr(
        preferences_reader,
        "ask_nvidia_for_json",
        lambda _p, _s: {"interests": ["pizza"], "avoid": None, "budget_max": None},
    )

    result = preferences_reader.read_with_nvidia("pizza please")

    assert result.interests == ["pizza"]
    assert result.avoid == [] and result.budget_max is None


# --- Order: primary first, backup second ------------------------------------


def use_readers(monkeypatch, gemini, nvidia):
    log = []

    def wrap(name, outcome):
        def reader(_note):
            log.append(name)
            if isinstance(outcome, Exception):
                raise outcome
            return outcome

        return reader

    monkeypatch.setattr(
        preferences_reader,
        "READERS",
        {"gemini": wrap("gemini", gemini), "nvidia": wrap("nvidia", nvidia)},
    )
    return log


def test_gemini_first_by_default(monkeypatch):
    log = use_readers(monkeypatch, Preferences(interests=["g"]), Preferences(interests=["n"]))

    assert preferences_reader.read_preferences("note").interests == ["g"]
    assert log == ["gemini"]


def test_nvidia_steps_in_when_gemini_fails(monkeypatch):
    log = use_readers(monkeypatch, RuntimeError("503"), Preferences(interests=["n"]))

    assert preferences_reader.read_preferences("note").interests == ["n"]
    assert log == ["gemini", "nvidia"]


def test_nvidia_steps_in_when_gemini_has_no_key(monkeypatch):
    log = use_readers(monkeypatch, None, Preferences(interests=["n"]))

    assert preferences_reader.read_preferences("note").interests == ["n"]
    assert log == ["gemini", "nvidia"]


def test_nvidia_can_be_primary(monkeypatch):
    monkeypatch.setattr(settings, "LLM_PRIMARY", "nvidia")
    log = use_readers(monkeypatch, Preferences(interests=["g"]), Preferences(interests=["n"]))

    assert preferences_reader.read_preferences("note").interests == ["n"]
    assert log == ["nvidia"]


def test_both_failing_gives_none(monkeypatch):
    use_readers(monkeypatch, RuntimeError("busy"), NvidiaError("busy"))

    assert preferences_reader.read_preferences("note") is None


def test_no_keys_at_all_gives_none_without_any_request():
    # The shared test setup removes both keys.
    assert preferences_reader.read_preferences("I love coffee") is None


def test_schema_sent_to_nvidia_is_valid_json():
    json.dumps(SCHEMA)
