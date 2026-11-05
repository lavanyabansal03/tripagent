import time
from typing import Literal

from google import genai
from google.genai import errors
from pydantic import BaseModel, Field

from app.config import settings


class Preferences(BaseModel):
    interests: list[str] = Field(default_factory=list)
    avoid: list[str] = Field(default_factory=list)

    budget_min: float | None = None
    budget_max: float | None = None
    budget_level: Literal["cheap", "moderate", "expensive"] | None = None

    max_travel_min: int | None = None


def extract_preferences(trip_description: str) -> Preferences | None:
    if not settings.GOOGLE_API_KEY:
        return None

    client = genai.Client(api_key=settings.GOOGLE_API_KEY)

    prompt = f"""
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

    response = call_with_retry(
        lambda: client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=prompt,
            config={
                "response_mime_type": "application/json",
                "response_schema": Preferences,
                "thinking_config": {
                    "thinking_level": "low",
                },
            },
        )
    )

    return Preferences.model_validate_json(response.text)


# Gemini can return 429 (too many requests) or 503 (busy).
RETRY_CODES = {429, 503}
MAX_TRIES = 4


def call_with_retry(call, sleep=time.sleep):
    """Retry Gemini requests on 429/503 errors."""

    for attempt in range(MAX_TRIES):
        try:
            return call()
        except errors.APIError as error:
            if error.code not in RETRY_CODES or attempt == MAX_TRIES - 1:
                raise

            sleep(2 ** (attempt + 1))
