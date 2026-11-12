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
# A second "Build my plan" for the same trip waits this long for the first one to
# finish (then it gets the same run); after that it gets 409.
PLAN_WAIT_SECONDS = 180
# L3 loop: repair tries after the first plan (docs/03 5.3, SRS FR-16).
MAX_REPAIR_ITERATIONS = 3
# A6 Repair: valid replacements shown to the LLM, and LLM choices per plan.
REPAIR_OPTIONS_FOR_LLM = 4
MAX_REPAIR_LLM_CALLS = 5
# L4 changes: the longest delay A5 accepts, and the longest A7 reason per activity.
MAX_DELAY_MINUTES = 600
MAX_REASON_CHARS = 200
# Discovery agent: the most place searches it may make for one trip.
MAX_DISCOVERY_CALLS = 8
# Countries TripAgent plans trips in (ISO codes, lower case). USA only for now;
# add codes here to allow more countries.
ALLOWED_COUNTRIES = ["us"]
# A2 famous places: the most names the LLM may suggest (each is one map lookup, or two).
MAX_FAMOUS_PLACES = 12
# Planner: most stops in one day for each pace, counting the lunch stop (the 09:00-20:00
# day still decides whether they all fit).
STOPS_PER_DAY = {"relaxed": 3, "moderate": 4, "packed": 5}
# Travel times between stops: the longest the whole step may take; slower legs get the
# rough estimate (transit lookups can take 5-10 s each).
ROUTES_TIME_LIMIT_S = 10
# Backup agent: backups kept per activity (FR-41 target 2) and searches per plan.
BACKUPS_PER_ACTIVITY = 2
MAX_BACKUP_SEARCHES = 15
# Place searches that may run at the same time (they only wait on the network).
PARALLEL_SEARCHES = 6

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
    # gemini-3.8-flash / 3.7-flash kept answering 503 "high demand" on the free
    # tier (checked 2026-11-11); 3.5-flash answered every time, in about 1s.
    GEMINI_MODEL: str = "gemini-3.5-flash"
    # NVIDIA Nemotron (build.nvidia.com). Model names change; check the site and
    # override in .env if needed.
    NVIDIA_API_KEY: str = ""
    NVIDIA_MODEL: str = "nvidia/nemotron-3.5-lightning-30b-a3b"
    # Which LLM to try first: "nvidia" (default, the more reliable one) or
    # "gemini". The other is the backup (ADR-009).
    LLM_PRIMARY: Literal["gemini", "nvidia"] = "nvidia"
    MAPBOX_SECRET_TOKEN: str = ""
    # Place search (free plan, no card). Used only when DEMO_MODE is false.
    GEOAPIFY_API_KEY: str = ""
    DATABASE_URL: str = "sqlite:///./tripagent.db"
    DEMO_MODE: bool = True
    # Comma-separated browser origins allowed to call the API. Use "*" to allow
    # any origin (the API has no cookies/auth, so credentials are then disabled).
    CORS_ORIGINS: str = "http://localhost:5173"


settings = Settings()
