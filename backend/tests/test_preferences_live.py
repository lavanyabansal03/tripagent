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


# The AI may word things differently ("touristy stuff" vs "touristy
# attractions"), so interests and avoid only need to share a key word.
MIN_CORRECT = 8
FILLER_WORDS = {"stuff", "things", "places", "spots", "good", "nice", "cool", "the", "a", "of"}


def key_words(text: str) -> set[str]:
    """Lowercase words without filler words or a plural "s" ("Clubs" -> "club")."""
    words = text.lower().replace("-", " ").split()
    return {word.rstrip("s") for word in words if word not in FILLER_WORDS}


def similar(a: str, b: str) -> bool:
    """True if two items share a key word, or one contains the other ("club" in "nightclub")."""
    for word_a in key_words(a):
        for word_b in key_words(b):
            if word_a == word_b:
                return True
            long_enough = min(len(word_a), len(word_b)) >= 4
            if long_enough and (word_a in word_b or word_b in word_a):
                return True
    return False


def same_items(got: list[str], expected: list[str]) -> bool:
    """Every expected item was found, and nothing unrelated was added."""
    found_all = all(any(similar(g, e) for g in got) for e in expected)
    nothing_extra = all(any(similar(g, e) for e in expected) for g in got)
    return found_all and nothing_extra


def check_example(result, expected) -> list[str]:
    """Return the list of mistakes for one example (empty means correct)."""
    mistakes = []
    if result.budget != expected["budget"]:
        mistakes.append(f"budget: got {result.budget!r}, expected {expected['budget']!r}")
    want_minutes = expected["max_travel_minutes"]
    if result.max_travel_minutes != want_minutes:
        mistakes.append(f"travel time: got {result.max_travel_minutes}, expected {want_minutes}")
    for field in ("interests", "avoid"):
        got = getattr(result, field)
        if not same_items(got, expected[field]):
            mistakes.append(f"{field}: got {got}, expected {expected[field]}")
    return mistakes


def test_similar_wording_counts_as_a_match():
    assert similar("touristy stuff", "touristy attractions")
    assert similar("clubs", "nightclubs")
    assert not similar("museums", "nightclubs")
    assert same_items(["coffee", "architecture"], ["architecture", "coffee"])
    assert not same_items(["coffee"], ["coffee", "architecture"])


def test_preference_examples_live():
    if not settings.GOOGLE_API_KEY:
        pytest.skip("GOOGLE_API_KEY is not set.")

    with EXPECTED_FILE.open(encoding="utf-8") as file:
        expected_answers = json.load(file)

    correct = 0
    for number, description in EXAMPLES:
        result = extract_preferences(description)
        mistakes = check_example(result, expected_answers[str(number)])
        if mistakes:
            print(f"Example {number} MISS: " + "; ".join(mistakes))
        else:
            correct += 1
            print(f"Example {number} OK")

    print(f"Score: {correct}/{len(EXAMPLES)} (need {MIN_CORRECT})")
    assert correct >= MIN_CORRECT, f"Only {correct}/{len(EXAMPLES)} examples were right"
