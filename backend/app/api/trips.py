"""Trip intake, clarification, planning, and trace API endpoints."""

import logging
from datetime import UTC, datetime
from typing import Any, Literal
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.agents.preferences import Preferences, extract_preferences
from app.graph.trip_planner import build_trip_graph

router = APIRouter(prefix="/trips", tags=["trips"])
runs_router = APIRouter(prefix="/runs", tags=["runs"])
trip_graph = build_trip_graph()
logger = logging.getLogger(__name__)

# Form fields the traveller can change. The Svelte form sends every field
# (defaults included) and lists the ones the traveller changed in `touched`.
FormField = Literal[
    "destination",
    "start_date",
    "end_date",
    "budget",
    "budget_strictness",
    "mode",
    "pace",
    "max_travel_min",
    "interests",
    "avoid",
    "tourist_local_ratio",
]


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
    # None = an older client that does not say; then any field it sent counts as chosen.
    touched: list[FormField] | None = None

    def user_chose(self, field: str) -> bool:
        """True when the traveller set this field themselves (not a form default)."""
        if self.touched is not None:
            return field in self.touched
        return field in self.model_fields_set

    @model_validator(mode="after")
    def validate_trip_dates(self) -> "TripRequest":
        if self.start_date or self.end_date:
            try:
                start = datetime.fromisoformat(self.start_date).date() if self.start_date else None
                end = datetime.fromisoformat(self.end_date).date() if self.end_date else None
            except ValueError as error:
                raise ValueError("Trip dates must use YYYY-MM-DD format") from error
            if start is not None and end is not None and end < start:
                raise ValueError("End date cannot be before start date")
        return self


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
_clarification_rounds: dict[str, int] = {}
_clarification_exhausted: set[str] = set()
_runs: dict[str, RunStatus] = {}
_traces: dict[str, list[ExecutionEvent]] = {}
_itineraries: dict[str, dict[str, Any]] = {}


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


def _read_note(free_text: str) -> Preferences:
    """Ask the Preferences agent to read the "Tell us more" note.

    Reading the note is an extra: if there is no note, no API key, or Gemini
    fails, the trip is still created from the form alone.
    """
    if not free_text.strip():
        return Preferences()
    try:
        return extract_preferences(free_text) or Preferences()
    except Exception:
        logger.warning("Could not read the trip note; using form values only", exc_info=True)
        return Preferences()


def _merge_items(from_form: list[str], from_note: list[str]) -> list[str]:
    """Form items first, then new items from the note; same word in any case counts once."""
    merged: list[str] = []
    seen: set[str] = set()
    for item in [*from_form, *from_note]:
        key = item.strip().lower()
        if key and key not in seen:
            seen.add(key)
            merged.append(item)
    return merged


def _form_provenance(request: TripRequest) -> dict[str, str]:
    """Label each form value "explicit" (traveller chose it) or "default" (we assumed it)."""
    provenance = {"destination": "explicit"}
    for field in ("start_date", "end_date"):
        provenance[field] = "explicit" if getattr(request, field) else "default"
    for field in (
        "budget",
        "budget_strictness",
        "mode",
        "pace",
        "max_travel_min",
        "tourist_local_ratio",
        "interests",
        "avoid",
    ):
        provenance[field] = "explicit" if request.user_chose(field) else "default"
    return provenance


@router.post("", response_model=CreateTripResponse, status_code=201)
def create_trip(request: TripRequest) -> CreateTripResponse:
    trip_id = str(uuid4())
    start_date = request.start_date or ""
    end_date = request.end_date or ""
    now = datetime.now(UTC).isoformat()

    note = _read_note(request.free_text)
    interests = _merge_items(request.interests, note.interests)
    avoid = _merge_items(request.avoid, note.avoid)

    # A number from the note replaces a form value only if the traveller never set it.
    max_travel_min = request.max_travel_min
    if (
        note.max_travel_min is not None
        and note.max_travel_min >= 1
        and not request.user_chose("max_travel_min")
    ):
        max_travel_min = note.max_travel_min
    budget = request.budget
    if note.budget_max is not None and not request.user_chose("budget"):
        budget = note.budget_max

    trip = Trip(
        id=trip_id,
        destination=request.destination,
        start_date=start_date,
        end_date=end_date,
        status="draft",
        current_version=0,
        created_at=now,
    )
    provenance = _form_provenance(request)
    # Values taken from the note are marked "inferred" (docs/contracts.md open decision 7).
    if note.interests and not request.interests:
        provenance["interests"] = "inferred"
    if note.avoid and not request.avoid:
        provenance["avoid"] = "inferred"
    if max_travel_min != request.max_travel_min:
        provenance["max_travel_min"] = "inferred"
    if budget != request.budget:
        provenance["budget"] = "inferred"
    requirements = TripRequirements(
        trip_id=trip_id,
        destination=request.destination,
        start_date=start_date,
        end_date=end_date,
        budget=budget,
        budget_strictness=request.budget_strictness,
        mode=request.mode,
        pace=request.pace,
        interests=interests,
        avoid=avoid,
        tourist_local_ratio=request.tourist_local_ratio,
        max_travel_min=max_travel_min,
        free_text=request.free_text,
        provenance=provenance,
    )
    questions = _questions_for(request.start_date, request.end_date)
    _trips[trip_id] = trip
    _requirements[trip_id] = requirements
    _questions[trip_id] = questions
    _clarification_rounds[trip_id] = 1 if questions else 0
    return CreateTripResponse(trip=trip, requirements=requirements, questions=questions)


@router.post("/{trip_id}/answers", response_model=TripRequirements)
def answer_questions(trip_id: str, request: AnswersRequest) -> TripRequirements:
    trip = _get_trip(trip_id)
    requirements = _get_requirements(trip_id)
    questions = _questions.get(trip_id, [])
    if trip_id in _clarification_exhausted:
        raise HTTPException(status_code=409, detail="Trip-date clarification limit reached")
    updates: dict[str, str] = {}

    for question in questions:
        answer = request.answers.get(question.id, request.answers.get(question.field, "")).strip()
        if answer:
            updates[question.field] = answer

    candidate_start = updates.get("start_date", requirements.start_date)
    candidate_end = updates.get("end_date", requirements.end_date)
    if candidate_start or candidate_end:
        try:
            start = datetime.fromisoformat(candidate_start).date() if candidate_start else None
            end = datetime.fromisoformat(candidate_end).date() if candidate_end else None
        except ValueError as error:
            raise HTTPException(
                status_code=422, detail="Trip dates must use YYYY-MM-DD format"
            ) from error
        if start is not None and end is not None and end < start:
            raise HTTPException(status_code=422, detail="End date cannot be before start date")

    requirements = requirements.model_copy(update=updates)
    trip = trip.model_copy(update=updates)
    remaining = _questions_for(requirements.start_date, requirements.end_date)
    if remaining:
        if _clarification_rounds.get(trip_id, 0) >= 2:
            remaining = []
            _clarification_exhausted.add(trip_id)
        else:
            _clarification_rounds[trip_id] = _clarification_rounds.get(trip_id, 0) + 1
    _requirements[trip_id] = requirements
    _trips[trip_id] = trip
    _questions[trip_id] = remaining
    return requirements


@router.post("/{trip_id}/plan", response_model=PlanResponse)
def plan_trip(trip_id: str) -> PlanResponse:
    trip = _get_trip(trip_id)
    requirements = _get_requirements(trip_id)
    if _questions.get(trip_id) or trip_id in _clarification_exhausted:
        raise HTTPException(
            status_code=409,
            detail="Trip dates are required; the two-round clarification limit was reached",
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
    succeeded = result.get("status") in ("completed", "infeasible")
    run_status: Literal["done", "failed", "infeasible"] = (
        "infeasible"
        if result.get("terminal") == "INFEASIBLE"
        else "done"
        if succeeded
        else "failed"
    )
    _runs[run_id] = RunStatus(
        run_id=run_id,
        trip_id=trip_id,
        status=run_status,
        phase="done",
        step=run_status,
        step_index=5,
        step_count=5,
        terminal=result.get("terminal") or ("PASS" if succeeded else "ERROR"),
        message=result.get("explanation") or None,
        started_at=started_at,
    )
    if succeeded:
        _trips[trip_id] = _trips[trip_id].model_copy(
            update={
                "status": "infeasible" if run_status == "infeasible" else "planned",
                "current_version": 1,
            }
        )
        _itineraries[trip_id] = result.get("itinerary", {})
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
def get_itinerary(trip_id: str, version: int | None = None) -> dict[str, Any] | None:
    _get_trip(trip_id)
    itinerary = _itineraries.get(trip_id)
    if itinerary is None or (version is not None and version != itinerary.get("version")):
        return None
    return itinerary


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
