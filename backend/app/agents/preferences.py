from google import genai
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
   the traveler wants. Do NOT include general adjectives or descriptions
   such as "relaxing", "outdoorsy", "luxurious", "low-key", or "family"
   unless the user clearly identifies them as something they want to do.

2. avoid — specific things the traveler does not like or wants to avoid
3. budget — use "cheap", "moderate", or "expensive"
4. max_travel_minutes — the maximum number of minutes the traveler
   wants to travel between activities

Only extract information that is actually stated or clearly implied.
Do not invent preferences. Preserve meaningful descriptive words from the
user's wording, such as "great food", instead of unnecessarily shortening
them to "food".

User trip description:
{trip_description}
"""

    response = client.models.generate_content(
        model="gemini-3.8-flash",
        contents=prompt,
        config={
    "response_mime_type": "application/json",
    "response_schema": Preferences,
    "thinking_config": {
        "thinking_level": "low",
    },
},
    )

    return Preferences.model_validate_json(response.text)