"""HTTP endpoints for starting and resuming the demo trip-planning graph."""

from typing import Any
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from langgraph.types import Command
from pydantic import BaseModel, ConfigDict, Field

from app.graph.trip_planner import build_trip_graph

router = APIRouter(prefix="/trips", tags=["trips"])
trip_graph = build_trip_graph()


class TripRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    destination: str = Field(min_length=1)
    interests: list[str] = Field(default_factory=list)
    start_date: str | None = None
    end_date: str | None = None


class TripAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid")

    start_date: str | None = None
    end_date: str | None = None


def _config(thread_id: str) -> dict[str, Any]:
    return {"configurable": {"thread_id": thread_id}}


def _response(thread_id: str) -> dict[str, Any]:
    snapshot = trip_graph.get_state(_config(thread_id))
    if not snapshot.values:
        raise HTTPException(status_code=404, detail="Trip session not found")
    state = snapshot.values
    return {
        "thread_id": thread_id,
        "status": state.get("status", "running"),
        "question": state.get("question") if state.get("status") == "awaiting_input" else None,
        "trip": state.get("trip"),
        "places": state.get("places", []),
        "saved_trip": state.get("saved_trip"),
        "logs": state.get("logs", []),
        "explanation": state.get("explanation"),
    }


@router.post("/plan")
def plan_trip(request: TripRequest) -> dict[str, Any]:
    thread_id = str(uuid4())
    trip = request.model_dump(exclude_none=True)
    trip["trip_id"] = thread_id
    trip_graph.invoke({"trip": trip, "logs": []}, _config(thread_id))
    return _response(thread_id)


@router.post("/{thread_id}/answer")
def answer_question(thread_id: str, answer: TripAnswer) -> dict[str, Any]:
    config = _config(thread_id)
    snapshot = trip_graph.get_state(config)
    if not snapshot.values:
        raise HTTPException(status_code=404, detail="Trip session not found")
    if snapshot.values.get("status") != "awaiting_input":
        raise HTTPException(status_code=409, detail="This trip is not waiting for an answer")
    # Preserve explicit nulls so even a blank response resumes the graph and uses
    # one of its two clarification turns. The graph ignores null date values.
    trip_graph.invoke(Command(resume=answer.model_dump()), config)
    return _response(thread_id)