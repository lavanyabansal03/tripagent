import time

from google import genai
from google.genai import errors
from pydantic import BaseModel, Field

from app.config import settings


class Preferences(BaseModel):
    interests: list[str] = Field(default_factory=list)
    avoid: list[str] = Field(default_factory=list)
    budget: str | None = None
    max_travel_minutes: int | None = None


def extract_preferences(trip_description: str) -> Preferences:
    if not settings.GOOGLE_API_KEY:
        raise ValueError("GOOGLE_API_KEY is not set.")

    client = genai.Client(api_key=settings.GOOGLE_API_KEY)

    prompt = f"""
You are a travel preference extraction assistant.

Read the user's trip description and extract exactly these four things:

1. interests — specific activities, attractions, foods, or experiences
   the traveler wants. Use concise category names instead of copying
   the user's full wording. For example, "cool architecture" becomes
   "architecture", "good coffee" becomes "coffee", and "explore local
   neighborhoods" becomes "local neighborhoods". 
   Remove subjective modifiers such as "good", "cool", and "nice"
   from interests. Return the core category, such as "coffee",
   "architecture", and "scenic views".
   
   Do NOT include general adjectives or descriptions such as "relaxing",
   "outdoorsy", "luxurious", "low-key", or "family" unless the user
   clearly identifies them as something they want to do.

2. avoid — specific things the traveler does not like or wants to avoid
3. budget — use "cheap", "moderate", or "expensive"
4. max_travel_minutes — the maximum number of minutes the traveler
   wants to travel between activities

Only extract information that is actually stated or clearly implied.
Do not invent preferences.

User trip description:
{trip_description}
"""

    config = {
        "response_mime_type": "application/json",
        "response_schema": Preferences,
        "thinking_config": {
            "thinking_level": "low",
        },
    }
    response = call_with_retry(
        lambda: client.models.generate_content(
            model=settings.GEMINI_MODEL, contents=prompt, config=config
        )
    )

    return Preferences.model_validate_json(response.text)


# Gemini answers 429 (too many requests) or 503 (busy) on the free tier.
RETRY_CODES = {429, 503}
MAX_TRIES = 4


def call_with_retry(call, sleep=time.sleep):
    """Run call(); on 429/503 wait 2, 4, 8 seconds and try again (MAX_TRIES in total)."""
    for attempt in range(MAX_TRIES):
        try:
            return call()
        except errors.APIError as error:
            if error.code not in RETRY_CODES or attempt == MAX_TRIES - 1:
                raise
            sleep(2 ** (attempt + 1))
