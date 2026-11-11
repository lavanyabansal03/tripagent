"""A2 Discovery, LLM part: turn each interest into search words the place search knows.

The place search understands a fixed list of words (SEARCH_WORDS, the same words
the Geoapify adapter maps to its categories). Interests from the form or the note
often do not match them ("hiking", "art galleries", "quirky stuff"). The LLM picks
up to two words from the list for each interest; code drops any word that is not on
the list and any interest the traveller did not give. Without a usable answer,
Discovery searches the interests as written.
"""

from typing import Any

from pydantic import BaseModel, Field

from app.agents.llm import ask_json
from app.tools.geoapify import CATEGORY_MAP

SEARCH_WORDS = sorted(CATEGORY_MAP)
WORDS_PER_INTEREST = 2


class InterestWords(BaseModel):
    interest: str = Field(description="One of the traveller's interests, exactly as given.")
    words: list[str] = Field(description="Up to 2 words from the allowed list; [] if none fit.")


class SearchPlan(BaseModel):
    interests: list[InterestWords]


def build_prompt(trip: dict[str, Any], interests: list[str]) -> str:
    return f"""You plan place searches for a trip to {trip.get("destination") or "the city"}.

The place search only understands these words: {", ".join(SEARCH_WORDS)}.

For each interest below, choose up to {WORDS_PER_INTEREST} of those words that would find
places a traveller with that interest would enjoy. Use only words from the list. If no
word fits an interest, give an empty list for it.

Interests: {"; ".join(interests)}
Things to avoid: {", ".join(trip.get("avoid") or []) or "nothing stated"}
Traveller's note: {trip.get("free_text") or "none"}

Answer with every interest exactly as written above and its words."""


def plan_with_llm(trip: dict[str, Any], interests: list[str]) -> dict[str, list[str]]:
    """interest -> checked search words. Empty dict when the LLM gives no usable answer."""
    answer = ask_json(build_prompt(trip, interests), SearchPlan)
    if answer is None:
        return {}
    by_lower = {interest.lower(): interest for interest in interests}
    allowed = set(SEARCH_WORDS)
    avoid = {str(item).strip().lower() for item in trip.get("avoid") or []}
    plan: dict[str, list[str]] = {}
    for item in answer.interests:
        interest = by_lower.get(item.interest.strip().lower())
        if interest is None:
            continue  # the LLM made up an interest
        words: list[str] = []
        for word in item.words:
            word = word.strip().lower()
            if word in allowed and word not in avoid and word not in words:
                words.append(word)
        if words:
            plan[interest] = words[:WORDS_PER_INTEREST]
    return plan
