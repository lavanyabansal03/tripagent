"""Shared pytest setup.

Ordinary tests must never call a real LLM (Gemini or NVIDIA): it is slow, rate-limited on
the free tier, and makes results depend on the network. Every test runs as if
no API key were set, except the live preference test, which is meant to call
Gemini and skips itself when no key is available.
"""

import pytest

from app import storage
from app.config import settings

LIVE_TEST_MODULES = {"test_preferences_live"}


@pytest.fixture(autouse=True)
def no_real_gemini_calls(request, monkeypatch):
    if request.module.__name__.rsplit(".", 1)[-1] not in LIVE_TEST_MODULES:
        monkeypatch.setattr(settings, "GOOGLE_API_KEY", "")
        monkeypatch.setattr(settings, "NVIDIA_API_KEY", "")


@pytest.fixture(autouse=True)
def fresh_database():
    """Every test gets its own empty in-memory database (never the real file)."""
    storage.use_database("sqlite://")
    yield
    storage.engine().dispose()
