"""Shared LLM helper for the agents: ask a question, get a checked answer back.

Every agent that uses an LLM calls `ask_json(prompt, Shape)`:
- it tries LLM_PRIMARY first (NVIDIA by default), then the other one (ADR-009);
- the answer must match the Pydantic `Shape`, or it counts as a failure;
- it returns None when no LLM has a key or both fail, so every caller must
  have a plain-code fallback. The LLM proposes; code decides (CLAUDE.md).

Tests never reach a real LLM: tests/conftest.py removes both keys.
"""

import logging
from collections.abc import Callable
from typing import TypeVar

from google import genai
from google.genai import types
from pydantic import BaseModel

from app.agents.nvidia_llm import ask_nvidia_for_json
from app.agents.preferences import call_with_retry
from app.config import GEMINI_TIMEOUT_SECONDS, settings

logger = logging.getLogger(__name__)

Shape = TypeVar("Shape", bound=BaseModel)


def ask_gemini(prompt: str, shape: type[Shape]) -> Shape | None:
    if not settings.GOOGLE_API_KEY:
        return None
    client = genai.Client(
        api_key=settings.GOOGLE_API_KEY,
        http_options=types.HttpOptions(timeout=GEMINI_TIMEOUT_SECONDS * 1000),
    )
    config = {
        "response_mime_type": "application/json",
        "response_schema": shape,
        "thinking_config": {"thinking_level": "low"},
    }
    response = call_with_retry(
        lambda: client.models.generate_content(
            model=settings.GEMINI_MODEL, contents=prompt, config=config
        )
    )
    return shape.model_validate_json(response.text)


def ask_nvidia(prompt: str, shape: type[Shape]) -> Shape | None:
    if not settings.NVIDIA_API_KEY:
        return None
    return shape.model_validate(ask_nvidia_for_json(prompt, shape.model_json_schema()))


PROVIDERS: dict[str, Callable[[str, type[BaseModel]], BaseModel | None]] = {
    "gemini": ask_gemini,
    "nvidia": ask_nvidia,
}


def ask_json(prompt: str, shape: type[Shape]) -> Shape | None:
    """Ask the primary LLM, then the backup. None if neither gives a valid answer."""
    backup = "nvidia" if settings.LLM_PRIMARY == "gemini" else "gemini"
    for name in (settings.LLM_PRIMARY, backup):
        try:
            answer = PROVIDERS[name](prompt, shape)
        except Exception as error:
            logger.warning("%s gave no usable answer (%s); trying the next LLM", name, error)
            continue
        if answer is not None:
            return answer
    return None
