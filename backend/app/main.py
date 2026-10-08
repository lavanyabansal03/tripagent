"""TripAgent backend entry point. Run with: uvicorn app.main:app --reload"""

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.trips import router as trips_router
from app.config import settings

app = FastAPI(title="TripAgent API")

# Let the Vite dev server (frontend) call this API from the browser.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
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
