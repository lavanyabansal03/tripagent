"""Read the "Tell us more" note with Gemini, and with NVIDIA Nemotron as a backup.

LLM_PRIMARY in .env picks which one goes first. If it has no key or fails, the
other one is tried. If both fail, the answer is None and the trip is created
from the form alone.
"""

from functools import partial

from app.agents.llm import first_answer
from app.agents.nvidia_llm import ask_nvidia_for_json
from app.agents.preferences import Preferences, build_prompt, extract_preferences
from app.config import settings


def read_with_gemini(note: str) -> Preferences | None:
    return extract_preferences(note)  # Kaleb's agent; None when there is no key


def read_with_nvidia(note: str) -> Preferences | None:
    if not settings.NVIDIA_API_KEY:
        return None
    answer = ask_nvidia_for_json(build_prompt(note), Preferences.model_json_schema())
    return Preferences.model_validate(answer)


READERS = {"gemini": read_with_gemini, "nvidia": read_with_nvidia}


def read_preferences(note: str) -> Preferences | None:
    """Try the primary LLM, then the backup. None if neither gives an answer."""
    return first_answer({name: partial(read, note) for name, read in READERS.items()})
