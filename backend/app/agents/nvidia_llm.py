"""Backup LLM: NVIDIA Nemotron through NVIDIA's hosted API.

Used when Gemini is busy or failing. NVIDIA's API has the same request format
as OpenAI's chat API, so we call it with a plain HTTP request (no OpenAI library).
"""

import json
import re
import time

import httpx

from app.config import LLM_MAX_TRIES, NVIDIA_BASE_URL, NVIDIA_TIMEOUT_SECONDS, settings

# Busy answers worth one more try (too many requests, server busy or slow).
RETRY_CODES = {429, 503, 504}
MAX_TRIES = LLM_MAX_TRIES  # from config.py


class NvidiaError(Exception):
    """NVIDIA did not give a usable answer."""


def ask_nvidia_for_json(prompt: str, schema: dict, post=httpx.post, sleep=time.sleep) -> dict:
    """Send the prompt and return the JSON object NVIDIA answers with.

    `post` and `sleep` can be replaced in tests so no real request is made.
    """
    if not settings.NVIDIA_API_KEY:
        raise NvidiaError("NVIDIA_API_KEY is not set.")

    body = {
        "model": settings.NVIDIA_MODEL,
        "messages": [
            {
                "role": "system",
                "content": "Answer with one JSON object only, matching this JSON schema: "
                + json.dumps(schema),
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0,
        "max_tokens": 1024,
        # Nemotron models can "think" first; we only want the answer.
        "chat_template_kwargs": {"enable_thinking": False},
    }
    headers = {"Authorization": f"Bearer {settings.NVIDIA_API_KEY}"}

    for attempt in range(MAX_TRIES):
        response = post(
            f"{NVIDIA_BASE_URL}/chat/completions",
            json=body,
            headers=headers,
            timeout=NVIDIA_TIMEOUT_SECONDS,
        )
        if response.status_code in RETRY_CODES and attempt < MAX_TRIES - 1:
            sleep(2 ** (attempt + 1))
            continue
        if response.status_code != 200:
            raise NvidiaError(f"NVIDIA answered {response.status_code}.")
        text = response.json()["choices"][0]["message"]["content"] or ""
        return _first_json_object(text)

    raise NvidiaError("NVIDIA stayed busy.")  # not reached; the loop returns or raises


def _first_json_object(text: str) -> dict:
    """Pull the JSON object out of the answer, ignoring ```json fences or <think> notes."""
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S)
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end < start:
        raise NvidiaError("NVIDIA's answer had no JSON object.")
    try:
        return json.loads(text[start : end + 1])
    except json.JSONDecodeError as error:
        raise NvidiaError("NVIDIA's answer was not valid JSON.") from error
