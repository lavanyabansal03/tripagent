import json
from pathlib import Path

import pytest

from app.agents.preferences import extract_preferences
from app.config import settings

EXPECTED_FILE = Path(__file__).with_name("preferences_expected.json")

EXAMPLES = [
    (
        1,
        "I want a 5-day trip with beaches and seafood. "
        "I want to avoid nightlife. My budget is cheap and "
        "I do not want to travel more than 20 minutes.",
    ),
    (
        2,
        "I'm going to Chicago and mostly wanna see cool architecture, "
        "find good coffee and explore local neighborhoods instead of "
        "doing all the touristy stuff. Moderate budget. Fine with "
        "traveling up to an hour between places.",
    ),
    (
        3,
        "looking for somewhere peaceful with nice views and trails to walk, "
        "nothing with clubs or people partying all night lol. trying to "
        "keep it cheap and not spend more than 40 mins getting between activities",
    ),
    (
        4,
        "So me and my friends are going away for a few days and we love live "
        "music, tacos, and just wandering around looking at record stores. "
        "We really don't want those packed tourist places where you wait in "
        "line forever. Ideally nothing more than like half an hour away "
        "from the next thing.",
    ),
    (
        5,
        "We want to go camping, kayak if possible, and find some waterfalls. "
        "I'm okay spending a bit more for the right experience but not going "
        "crazy with money. Definitely no expensive restaurants though. "
        "Travel time between activities should be under 1.5 hours.",
    ),
    (
        6,
        "visiting for the weekend!! into museums, street food and taking pics "
        "of everything 📸. don't send me to malls or clubs pls. Budget is low, "
        "and I'd rather keep each trip between spots under 45 mins.",
    ),
    (
        7,
        "Taking the kids on a trip and need stuff they'll actually enjoy. "
        "Theme parks, aquariums, maybe places to get ice cream. Not interested "
        "in art galleries. Keep drives short, like 25 min max. Haven't decided "
        "how much we wanna spend yet.",
    ),
    (
        8,
        "We're looking for a luxurious weekend: really nice hotels, fine dining "
        "and a spa day. No hiking or camping. Money isn't really an issue. "
        "I'd prefer activities within 30 minutes of each other.",
    ),
    (
        9,
        "i love basketball and finding local places to eat, plus parks if the "
        "weather's nice. pls avoid those super long guided tours, they bore me. "
        "trying to do this trip on the cheap but haven't thought about how far "
        "apart places can be",
    ),
    (
        10,
        "okay so not really into big busy cities, would rather check out farmers "
        "markets and little bakeries and maybe go on some scenic drives?? "
        "don't need anything fancy but haven't set a budget yet. "
        "would be nice if the activities weren't more than an hour apart. "
        "busy downtown areas are a no for me",
    ),
]


def test_preference_examples_live():
    if not settings.GOOGLE_API_KEY:
        pytest.skip("GOOGLE_API_KEY is not set.")

    with EXPECTED_FILE.open(encoding="utf-8") as file:
        expected_answers = json.load(file)

    for number, description in EXAMPLES:
        expected = expected_answers[str(number)]
        result = extract_preferences(description)

        assert result.budget == expected["budget"], f"Example {number}: budget"
        assert result.max_travel_minutes == expected["max_travel_minutes"], (
            f"Example {number}: travel time"
        )
        assert set(result.interests) == set(expected["interests"]), f"Example {number}: interests"
        assert set(result.avoid) == set(expected["avoid"]), f"Example {number}: avoid"
