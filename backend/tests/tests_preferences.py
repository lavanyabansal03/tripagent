import json
from pathlib import Path

from app.agents.preferences import Preferences

EXPECTED_FILE = Path(__file__).with_name("preferences_expected.json")


def test_preference_examples():
    with EXPECTED_FILE.open(encoding="utf-8") as file:
        expected_answers = json.load(file)

    assert len(expected_answers) == 10

    for number in range(1, 11):
        assert str(number) in expected_answers, f"Missing example {number}"
        Preferences.model_validate(expected_answers[str(number)])
