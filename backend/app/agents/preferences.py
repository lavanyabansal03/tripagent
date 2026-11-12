from typing import Literal

from pydantic import BaseModel, Field

from app.agents.llm import ask_gemini


class Preferences(BaseModel):
    interests: list[str] = Field(default_factory=list)
    avoid: list[str] = Field(default_factory=list)
    budget_min: float | None = None
    budget_max: float | None = None
    budget_level: Literal["cheap", "moderate", "expensive"] | None = None
    max_travel_min: int | None = None


def build_prompt(trip_description: str) -> str:
    """Kaleb's extraction prompt, shared by Gemini and the NVIDIA backup."""
    return f"""
You are a travel preference extraction assistant.

Read the user's trip description and extract these preferences:

1. interests — specific activities, attractions, foods, or experiences
   the traveler wants. Use concise category names instead of copying
   the user's full wording. Remove subjective modifiers such as
   "good", "cool", and "nice" when they don't add meaning.
   Preserve meaningful descriptions.

2. avoid — specific things the traveler does not like or wants to avoid.

3. budget_min — minimum monetary budget if explicitly provided.
4. budget_max — maximum monetary budget if explicitly provided.
5. budget_level — use "cheap", "moderate", or "expensive".
   If the user does not describe a budget, return null.
   Do not invent monetary amounts.

6. max_travel_min — maximum number of minutes the traveler
   wants to travel between activities.

Only extract information that is actually stated or clearly implied.
Do not invent preferences. Use null for missing numeric values.

User trip description:
{trip_description}
"""


def extract_preferences(trip_description: str) -> Preferences | None:
    """Read the note with Gemini. None when there is no Gemini key."""
    return ask_gemini(build_prompt(trip_description), Preferences)
