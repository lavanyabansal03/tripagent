"""App settings, read from environment variables (and the root .env file if present).

Every key is optional so the app can start with no API keys set.
"""

from pathlib import Path

from dotenv import load_dotenv
from pydantic_settings import BaseSettings

# The .env file lives at the repo root (one level above backend/).
load_dotenv(Path(__file__).resolve().parents[2] / ".env")


class Settings(BaseSettings):
    GOOGLE_API_KEY: str = ""
    MAPBOX_SECRET_TOKEN: str = ""
    FOURSQUARE_API_KEY: str = ""
    DATABASE_URL: str = "sqlite:///./tripagent.db"
    DEMO_MODE: bool = True


settings = Settings()
