"""TripAgent backend entry point. Run with: uvicorn app.main:app --reload"""

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.trips import router as trips_router
from app.api.trips import runs_router
from app.config import settings

app = FastAPI(title="TripAgent API")

# Browser origins allowed to call this API. Local dev defaults to the Vite dev
# server; production sets CORS_ORIGINS (use "*" when there is no cookie/auth).
_origins = [origin.strip() for origin in settings.CORS_ORIGINS.split(",") if origin.strip()]
_allow_all = _origins == ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=not _allow_all,
    allow_methods=["*"],
    allow_headers=["*"],
)

# All routes live under /api (e.g. /api/health).
router = APIRouter(prefix="/api")


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "demo_mode": settings.DEMO_MODE}


app.include_router(router)
app.include_router(trips_router, prefix="/api")
app.include_router(runs_router, prefix="/api")
