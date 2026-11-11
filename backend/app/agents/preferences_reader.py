"""Read the "Tell us more" note with Gemini, and with NVIDIA Nemotron as a backup.

LLM_PRIMARY in .env picks which one goes first. If it has no key or fails, the
other one is tried. If both fail, the answer is None and the trip is created
from the form alone.
"""

import logging

from app.agents.nvidia_llm import ask_nvidia_for_json
from app.agents.preferences import Preferences, build_prompt, extract_preferences
from app.config import settings

logger = logging.getLogger(__name__)


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
    backup = "nvidia" if settings.LLM_PRIMARY == "gemini" else "gemini"
    for name in (settings.LLM_PRIMARY, backup):
        try:
            result = READERS[name](note)
        except Exception:
            logger.warning("%s could not read the trip note; trying the next LLM", name)
            continue
        if result is not None:
            return result
    return None
