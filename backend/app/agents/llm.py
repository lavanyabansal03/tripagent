"""Shared LLM helper for the agents: ask a question, get a checked answer back.

Every agent that uses an LLM calls `ask_json(prompt, Shape)`:
- it tries LLM_PRIMARY first (NVIDIA by default), then the other one (ADR-009);
- the answer must match the Pydantic `Shape`, or it counts as a failure;
- it returns None when no LLM has a key or both fail, so every caller must
  have a plain-code fallback. The LLM proposes; code decides (CLAUDE.md).

Tests never reach a real LLM: tests/conftest.py removes both keys.
"""

import logging
import time
from collections.abc import Callable
from functools import partial
from typing import Any, TypeVar

from google import genai
from google.genai import errors, types
from pydantic import BaseModel

from app.agents.nvidia_llm import ask_nvidia_for_json
from app.config import GEMINI_TIMEOUT_SECONDS, LLM_MAX_TRIES, settings

logger = logging.getLogger(__name__)

Shape = TypeVar("Shape", bound=BaseModel)
Answer = TypeVar("Answer")

# Gemini answers 429 (too many requests) or 503 (busy) on the free tier.
RETRY_CODES = {429, 503}
MAX_TRIES = LLM_MAX_TRIES  # from config.py


def call_with_retry(call, sleep=time.sleep):
    """Run call(); on 429/503 wait 2, then 4 seconds and try again (MAX_TRIES in total)."""
    for attempt in range(MAX_TRIES):
        try:
            return call()
        except errors.APIError as error:
            if error.code not in RETRY_CODES or attempt == MAX_TRIES - 1:
                raise
            sleep(2 ** (attempt + 1))
    return None  # not reached: the loop returns or raises


def ask_gemini(prompt: str, shape: type[Shape]) -> Shape | None:
    if not settings.GOOGLE_API_KEY:
        return None
    # Without a time limit a stuck request would hang the request forever.
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


def without_nulls(value: Any) -> Any:
    """Drop null values, at any depth, from an LLM's JSON answer.

    Seen live: NVIDIA answers "avoid": null or "short_name": null for "nothing here".
    A null means "not stated", which is each field's default (an empty list, "" or
    None). Without this, one null failed the whole answer and the agent fell back to
    Gemini or plain rules. A required field that is null is still missing, so the
    answer is still rejected (the LLM proposes; code decides).
    """
    if isinstance(value, dict):
        return {key: without_nulls(item) for key, item in value.items() if item is not None}
    if isinstance(value, list):
        return [without_nulls(item) for item in value if item is not None]
    return value


def ask_nvidia(prompt: str, shape: type[Shape]) -> Shape | None:
    if not settings.NVIDIA_API_KEY:
        return None
    answer = ask_nvidia_for_json(prompt, shape.model_json_schema())
    return shape.model_validate(without_nulls(answer))


PROVIDERS: dict[str, Callable[[str, type[BaseModel]], BaseModel | None]] = {
    "gemini": ask_gemini,
    "nvidia": ask_nvidia,
}


def first_answer(attempts: dict[str, Callable[[], Answer | None]]) -> Answer | None:
    """Run the primary LLM's attempt, then the backup's. None if neither answers.

    `attempts` maps "gemini" and "nvidia" to a no-argument function. An attempt
    that raises or returns None counts as "no answer".
    """
    backup = "nvidia" if settings.LLM_PRIMARY == "gemini" else "gemini"
    for name in (settings.LLM_PRIMARY, backup):
        try:
            answer = attempts[name]()
        except Exception as error:  # noqa: BLE001 - any failure moves on to the backup
            logger.warning("%s gave no usable answer (%s); trying the next LLM", name, error)
            continue
        if answer is not None:
            return answer
    return None


def ask_json(prompt: str, shape: type[Shape]) -> Shape | None:
    """Ask the primary LLM, then the backup. None if neither gives a valid answer."""
    return first_answer({name: partial(ask, prompt, shape) for name, ask in PROVIDERS.items()})
