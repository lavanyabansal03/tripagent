import json
from pathlib import Path

import pytest
from google.genai import errors

from app.agents import preferences as preferences_agent
from app.agents.preferences import (
    MAX_TRIES,
    Preferences,
    call_with_retry,
    extract_preferences,
)
from app.config import GEMINI_TIMEOUT_SECONDS, settings

EXPECTED_FILE = Path(__file__).with_name("preferences_expected.json")


def test_preference_examples():
    with EXPECTED_FILE.open(encoding="utf-8") as file:
        expected_answers = json.load(file)

    assert len(expected_answers) == 10

    for number in range(1, 11):
        assert str(number) in expected_answers, f"Missing example {number}"
        Preferences.model_validate(expected_answers[str(number)])


def busy_error(code):
    return errors.APIError(code, {"error": {"code": code, "message": "busy"}})


def test_retry_waits_and_tries_again_when_gemini_is_busy():
    answers = [busy_error(503), busy_error(429), "ok"]
    waits = []

    def call():
        answer = answers.pop(0)
        if isinstance(answer, Exception):
            raise answer
        return answer

    assert call_with_retry(call, sleep=waits.append) == "ok"
    assert waits == [2, 4]


def test_retry_gives_up_after_max_tries():
    waits = []

    def call():
        raise busy_error(503)

    with pytest.raises(errors.APIError):
        call_with_retry(call, sleep=waits.append)
    assert len(waits) == MAX_TRIES - 1


def test_retry_does_not_repeat_other_errors():
    waits = []

    def call():
        raise busy_error(400)

    with pytest.raises(errors.APIError):
        call_with_retry(call, sleep=waits.append)
    assert waits == []


def test_missing_api_key_skips_extraction(monkeypatch):
    monkeypatch.setattr(settings, "GOOGLE_API_KEY", "")

    assert extract_preferences("I want beaches and seafood.") is None


def test_gemini_call_has_a_time_limit(monkeypatch):
    """A slow Gemini answer must not hang trip creation forever."""
    created = {}

    class FakeModels:
        def generate_content(self, **_kwargs):
            class Answer:
                text = '{"interests": ["coffee"], "avoid": []}'

            return Answer()

    class FakeClient:
        def __init__(self, **kwargs):
            created.update(kwargs)
            self.models = FakeModels()

    monkeypatch.setattr(settings, "GOOGLE_API_KEY", "test-key")
    monkeypatch.setattr(preferences_agent.genai, "Client", FakeClient)

    result = extract_preferences("I love coffee.")

    assert result.interests == ["coffee"]
    assert created["http_options"].timeout == GEMINI_TIMEOUT_SECONDS * 1000
