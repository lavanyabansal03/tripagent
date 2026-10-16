"""Trip intake, clarification, planning, and trace API endpoints."""

from datetime import UTC, datetime
from typing import Any, Literal
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from app.graph.trip_planner import build_trip_graph

router = APIRouter(prefix="/trips", tags=["trips"])
runs_router = APIRouter(prefix="/runs", tags=["runs"])
trip_graph = build_trip_graph()


class TripRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    destination: str = Field(min_length=1)
    interests: list[str] = Field(default_factory=list)
    start_date: str | None = None
    end_date: str | None = None
    budget: float | None = None
    budget_strictness: Literal["strict", "flexible"] = "strict"
    mode: Literal["walking", "transit", "driving", "cycling"] = "transit"
    pace: Literal["relaxed", "moderate", "packed"] = "moderate"
    max_travel_min: int = Field(default=30, ge=1)
    avoid: list[str] = Field(default_factory=list)
    tourist_local_ratio: int = Field(default=50, ge=0, le=100)
    free_text: str = ""


class Trip(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    destination: str
    start_date: str
    end_date: str
    status: Literal["draft", "planning", "planned", "adapting", "infeasible", "error"]
    current_version: int
    created_at: str


class TripRequirements(BaseModel):
    model_config = ConfigDict(extra="forbid")

    trip_id: str
    version: int = 1
    destination: str
    start_date: str
    end_date: str
    budget: float | None = None
    budget_strictness: Literal["strict", "flexible"] = "strict"
    mode: Literal["walking", "transit", "driving", "cycling"] = "transit"
    pace: Literal["relaxed", "moderate", "packed"] = "moderate"
    interests: list[str] = Field(default_factory=list)
    avoid: list[str] = Field(default_factory=list)
    tourist_local_ratio: int = 50
    max_travel_min: int = 30
    daily_start: str = "09:00"
    daily_end: str = "20:00"
    dietary: list[str] = Field(default_factory=list)
    accessibility: list[str] = Field(default_factory=list)
    free_text: str = ""
    provenance: dict[str, Literal["explicit", "inferred", "default"]] = Field(
        default_factory=dict
    )


class Question(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    field: str
    text: str
    options: list[str] | None = None


class ExecutionEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    trip_id: str
    run_id: str
    node: str
    type: Literal["node", "tool", "llm", "validation", "loop"]
    iteration: int
    status: Literal["started", "ok", "failed", "degraded", "skipped"]
    duration_ms: int
    metadata: dict[str, Any]
    ts: str


class CreateTripResponse(BaseModel):
    trip: Trip
    requirements: TripRequirements
    questions: list[Question]


class AnswersRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    answers: dict[str, str] = Field(default_factory=dict)


class PlanResponse(BaseModel):
    run_id: str


class RunStatus(BaseModel):
    run_id: str
    trip_id: str
    status: Literal["queued", "running", "done", "failed", "infeasible", "needs-user"]
    phase: Literal["intake", "plan", "repair", "adapt", "done"]
    step: str
    step_index: int
    step_count: int
    terminal: Literal["PASS", "INFEASIBLE", "NEEDS_USER", "ERROR"] | None
    message: str | None = None
    started_at: str


# The Sprint 1 backend is intentionally in-memory, like the graph checkpointer.
_trips: dict[str, Trip] = {}
_requirements: dict[str, TripRequirements] = {}
_questions: dict[str, list[Question]] = {}
_runs: dict[str, RunStatus] = {}
_traces: dict[str, list[ExecutionEvent]] = {}


def _get_trip(trip_id: str) -> Trip:
    trip = _trips.get(trip_id)
    if trip is None:
        raise HTTPException(status_code=404, detail="Trip not found")
    return trip


def _get_requirements(trip_id: str) -> TripRequirements:
    requirements = _requirements.get(trip_id)
    if requirements is None:
        raise HTTPException(status_code=404, detail="Trip not found")
    return requirements


def _questions_for(start_date: str | None, end_date: str | None) -> list[Question]:
    questions = []
    if not start_date:
        questions.append(
            Question(id="start_date", field="start_date", text="When does your trip start?")
        )
    if not end_date:
        questions.append(
            Question(id="end_date", field="end_date", text="When does your trip end?")
        )
    return questions


@router.post("", response_model=CreateTripResponse, status_code=201)
def create_trip(request: TripRequest) -> CreateTripResponse:
    trip_id = str(uuid4())
    start_date = request.start_date or ""
    end_date = request.end_date or ""
    now = datetime.now(UTC).isoformat()

    trip = Trip(
        id=trip_id,
        destination=request.destination,
        start_date=start_date,
        end_date=end_date,
        status="draft",
        current_version=0,
        created_at=now,
    )
    provenance = {
        "destination": "explicit",
        "start_date": "explicit" if start_date else "default",
        "end_date": "explicit" if end_date else "default",
        "mode": "explicit",
        "pace": "explicit",
    }
    requirements = TripRequirements(
        trip_id=trip_id,
        destination=request.destination,
        start_date=start_date,
        end_date=end_date,
        budget=request.budget,
        budget_strictness=request.budget_strictness,
        mode=request.mode,
        pace=request.pace,
        interests=request.interests,
        avoid=request.avoid,
        tourist_local_ratio=request.tourist_local_ratio,
        max_travel_min=request.max_travel_min,
        free_text=request.free_text,
        provenance=provenance,
    )
    questions = _questions_for(request.start_date, request.end_date)
    _trips[trip_id] = trip
    _requirements[trip_id] = requirements
    _questions[trip_id] = questions
    return CreateTripResponse(trip=trip, requirements=requirements, questions=questions)


@router.post("/{trip_id}/answers", response_model=TripRequirements)
def answer_questions(trip_id: str, request: AnswersRequest) -> TripRequirements:
    trip = _get_trip(trip_id)
    requirements = _get_requirements(trip_id)
    questions = _questions.get(trip_id, [])
    updates: dict[str, str] = {}

    for question in questions:
        answer = request.answers.get(question.id, request.answers.get(question.field, "")).strip()
        if answer:
            updates[question.field] = answer

    requirements = requirements.model_copy(update=updates)
    trip = trip.model_copy(update=updates)
    remaining = _questions_for(requirements.start_date, requirements.end_date)
    _requirements[trip_id] = requirements
    _trips[trip_id] = trip
    _questions[trip_id] = remaining
    return requirements


@router.post("/{trip_id}/plan", response_model=PlanResponse)
def plan_trip(trip_id: str) -> PlanResponse:
    trip = _get_trip(trip_id)
    requirements = _get_requirements(trip_id)
    if _questions.get(trip_id):
        raise HTTPException(
            status_code=409, detail="Answer the trip-date questions before planning"
        )

    existing_run_id = next(
        (run_id for run_id, run in _runs.items() if run.trip_id == trip_id), None
    )
    if existing_run_id:
        return PlanResponse(run_id=existing_run_id)

    run_id = str(uuid4())
    started_at = datetime.now(UTC).isoformat()
    _trips[trip_id] = trip.model_copy(update={"status": "planning"})
    graph_trip = requirements.model_dump()
    graph_trip["trip_id"] = trip_id
    result = trip_graph.invoke(
        {"trip": graph_trip, "logs": [], "run_id": run_id},
        {"configurable": {"thread_id": trip_id}},
    )
    succeeded = result.get("status") == "completed"
    status: Literal["done", "failed"] = "done" if succeeded else "failed"
    _runs[run_id] = RunStatus(
        run_id=run_id,
        trip_id=trip_id,
        status=status,
        phase="done",
        step="completed" if succeeded else "failed",
        step_index=5,
        step_count=5,
        terminal="PASS" if succeeded else "ERROR",
        message=result.get("explanation"),
        started_at=started_at,
    )
    if succeeded:
        _trips[trip_id] = _trips[trip_id].model_copy(
            update={"status": "planned", "current_version": 1}
        )
    else:
        _trips[trip_id] = _trips[trip_id].model_copy(update={"status": "error"})
    _traces[trip_id] = [ExecutionEvent.model_validate(event) for event in result.get("logs", [])]
    return PlanResponse(run_id=run_id)


@router.get("/{trip_id}", response_model=Trip)
def get_trip(trip_id: str) -> Trip:
    return _get_trip(trip_id)


@router.get("/{trip_id}/requirements", response_model=TripRequirements)
def get_trip_requirements(trip_id: str) -> TripRequirements:
    return _get_requirements(trip_id)


@router.get("/{trip_id}/itinerary")
def get_itinerary(trip_id: str, version: int | None = None) -> None:
    _get_trip(trip_id)
    return None


@router.get("/{trip_id}/trace", response_model=list[ExecutionEvent])
def get_trace(trip_id: str) -> list[ExecutionEvent]:
    _get_trip(trip_id)
    return _traces.get(trip_id, [])


@router.get("/{trip_id}/versions", response_model=list[int])
def get_versions(trip_id: str) -> list[int]:
    trip = _get_trip(trip_id)
    return [trip.current_version] if trip.current_version else []


@router.get("/{trip_id}/replans", response_model=list[dict[str, Any]])
def get_replans(trip_id: str) -> list[dict[str, Any]]:
    _get_trip(trip_id)
    return []


@runs_router.get("/{run_id}", response_model=RunStatus)
def get_run(run_id: str) -> RunStatus:
    run = _runs.get(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return run
