"""App settings, read from environment variables (and the root .env file if present).

Every key is optional so the app can start with no API keys set.
"""

from pathlib import Path

from dotenv import load_dotenv
from pydantic_settings import BaseSettings

# Hard caps for graph loops; keep every retry/clarification path bounded.
MAX_CLARIFICATION_ATTEMPTS = 2
MAX_FIND_ATTEMPTS = 3
# L3 loop: repair tries after the first plan (docs/03 5.3, SRS FR-16).
MAX_REPAIR_ITERATIONS = 3
# Discovery agent: the most place searches it may make for one trip.
MAX_DISCOVERY_CALLS = 8
# Backup agent: backups kept per activity (FR-41 target 2) and searches per plan.
BACKUPS_PER_ACTIVITY = 2
MAX_BACKUP_SEARCHES = 15

# Longest wait for one Gemini answer before giving up (each retry gets its own limit).
GEMINI_TIMEOUT_SECONDS = 20

# The .env file lives at the repo root (one level above backend/).
load_dotenv(Path(__file__).resolve().parents[2] / ".env")


class Settings(BaseSettings):
    GOOGLE_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-3.8-flash"
    MAPBOX_SECRET_TOKEN: str = ""
    FOURSQUARE_API_KEY: str = ""
    # Place search (free plan, no card). Used only when DEMO_MODE is false.
    GEOAPIFY_API_KEY: str = ""
    DATABASE_URL: str = "sqlite:///./tripagent.db"
    DEMO_MODE: bool = True
    # Comma-separated browser origins allowed to call the API. Use "*" to allow
    # any origin (the API has no cookies/auth, so credentials are then disabled).
    CORS_ORIGINS: str = "http://localhost:5173"


settings = Settings()
