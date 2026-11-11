"""App settings, read from environment variables (and the root .env file if present).

Every key is optional so the app can start with no API keys set.
"""

from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from pydantic_settings import BaseSettings

# Hard caps for graph loops; keep every retry/clarification path bounded.
MAX_CLARIFICATION_ATTEMPTS = 2
MAX_FIND_ATTEMPTS = 3
# L3 loop: repair tries after the first plan (docs/03 5.3, SRS FR-16).
MAX_REPAIR_ITERATIONS = 3
# A6 Repair: valid replacements shown to the LLM, and LLM choices per plan.
REPAIR_OPTIONS_FOR_LLM = 4
MAX_REPAIR_LLM_CALLS = 5
# Discovery agent: the most place searches it may make for one trip.
MAX_DISCOVERY_CALLS = 8
# Backup agent: backups kept per activity (FR-41 target 2) and searches per plan.
BACKUPS_PER_ACTIVITY = 2
MAX_BACKUP_SEARCHES = 15

# LLM calls (Gemini and NVIDIA): tries per call on 429/503, i.e. 2 retries, then the
# other LLM is the fallback (docs/03 L6 "2 retries + 1 fallback").
LLM_MAX_TRIES = 3
# Longest wait for one Gemini answer before giving up (each retry gets its own limit).
GEMINI_TIMEOUT_SECONDS = 20
# Same idea for the NVIDIA backup LLM.
NVIDIA_TIMEOUT_SECONDS = 20
NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"

# The .env file lives at the repo root (one level above backend/).
load_dotenv(Path(__file__).resolve().parents[2] / ".env")


class Settings(BaseSettings):
    GOOGLE_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-3.8-flash"
    # Backup LLM (NVIDIA Nemotron) for when Gemini is busy or failing. Optional.
    # Model names change; check build.nvidia.com and override in .env if needed.
    NVIDIA_API_KEY: str = ""
    NVIDIA_MODEL: str = "nvidia/nemotron-3.5-lightning-30b-a3b"
    # Which LLM to try first: "gemini" (default) or "nvidia". The other is the backup.
    LLM_PRIMARY: Literal["gemini", "nvidia"] = "gemini"
    MAPBOX_SECRET_TOKEN: str = ""
    # Place search (free plan, no card). Used only when DEMO_MODE is false.
    GEOAPIFY_API_KEY: str = ""
    DATABASE_URL: str = "sqlite:///./tripagent.db"
    DEMO_MODE: bool = True
    # Comma-separated browser origins allowed to call the API. Use "*" to allow
    # any origin (the API has no cookies/auth, so credentials are then disabled).
    CORS_ORIGINS: str = "http://localhost:5173"


settings = Settings()
