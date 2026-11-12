"""Changes during the trip (L4): the endpoints behind Adjust trip, Swap, Undo and Simulate.

    POST /trips/{id}/changes                      text or quick button -> A5 -> replan
    POST /trips/{id}/activities/{aid}/swap        use one of the stored backups
    POST /trips/{id}/versions/{v}/restore         Undo: make version v current again
    POST /trips/{id}/simulate                     demo disruptions: closure, delay

Each change runs right away (like POST /plan); the website then reads the run, the
new version, the change history and the trace. Only one change runs at a time per
trip: the lock lives in this process, which is right for one server (Render's free
plan runs one). A second change at the same time gets 409.
"""

import logging
import threading
from datetime import UTC, datetime
from time import perf_counter
from typing import Any, Literal
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from app import storage
from app.agents.apply_change import ChangeError
from app.agents.backup import attach_backups
from app.agents.change_interpreter import PROTECTED_STATUSES, Interpretation, interpret
from app.agents.repair_choice import choose_with_llm
from app.agents.replan import replan
from app.api.trips import (
    ExecutionEvent,
    PlanResponse,
    RunStatus,
    Trip,
    TripRequirements,
    _load,
    _save,
)

router = APIRouter(prefix="/trips", tags=["changes"])
logger = logging.getLogger(__name__)

_locks: dict[str, threading.Lock] = {}
_locks_guard = threading.Lock()


class ChangeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str | None = None
    typed: dict[str, Any] | None = None
    day: int | None = Field(default=None, ge=1)  # the day open on screen


class ChangeResponse(BaseModel):
    run_id: str  # "" when A5 needs an answer first
    change: dict[str, Any]  # the ChangeEvent


class SwapRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    backup_id: str


class SimulateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: str
    activity_id: str | None = None


class RestoreResponse(BaseModel):
    version: int


# --- helpers ---------------------------------------------------------------------


def _lock_for(trip_id: str) -> threading.Lock:
    with _locks_guard:
        return _locks.setdefault(trip_id, threading.Lock())


def _current(trip_id: str) -> tuple[dict[str, Any], Trip, TripRequirements, dict[str, Any]]:
    record = _load(trip_id)
    trip = Trip.model_validate(record["trip"])
    requirements = TripRequirements.model_validate(record["requirements"])
    itinerary = storage.get_itinerary(trip_id, trip.current_version or None)
    if not itinerary:
        raise HTTPException(status_code=409, detail="Plan the trip before changing it")
    return record, trip, requirements, itinerary


def _event(trip_id, run_id, node, kind, message, ms=0, status="ok", **details) -> dict:
    return ExecutionEvent(
        id=str(uuid4()), trip_id=trip_id, run_id=run_id, node=node, type=kind,
        iteration=details.pop("iteration", 1), status=status, duration_ms=max(0, ms),
        metadata={"message": message, **details}, ts=datetime.now(UTC).isoformat(),
    ).model_dump(mode="json")


def _change_event(trip_id: str, interp: Interpretation, raw_text: str, source: str) -> dict:
    payload = dict(interp.payload)
    if interp.status != "ok":
        payload = {"question": interp.question}
    return {
        "id": str(uuid4()),
        "trip_id": trip_id,
        "source": source,
        "type": interp.type,
        "payload": payload,
        "raw_text": raw_text,
        "status": "applied" if interp.status == "ok" else "needs-clarification",
    }


def _run_change(
    trip_id: str,
    change: dict[str, Any],
    change_type: str,
    payload: dict[str, Any],
    trigger: str,
    first_events: list[dict[str, Any]],
) -> str:
    """Apply one change and save everything. Returns the run id."""
    lock = _lock_for(trip_id)
    if not lock.acquire(blocking=False):
        raise HTTPException(status_code=409, detail="A change is already being applied")
    run_id = first_events[0]["run_id"] if first_events else str(uuid4())
    started_at = datetime.now(UTC).isoformat()
    events = list(first_events)
    try:
        record, trip, requirements, itinerary = _current(trip_id)
        req_dict = requirements.model_dump(mode="json")
        backup_trip = {**req_dict, "trip_id": trip_id}

        def add_backups(plan: dict[str, Any], only_ids: set[str] | None) -> int:
            try:
                return attach_backups(plan, backup_trip, only_ids=only_ids)
            except Exception:  # no backups is fine; the change itself still applies
                logger.warning("Backup search failed during a change", exc_info=True)
                return 0

        try:
            result = replan(
                change_type=change_type, payload=payload, trigger=trigger,
                trigger_id=change["id"], trip_id=trip_id, requirements=req_dict,
                itinerary=itinerary, places=storage.get_places(trip_id),
                versions=storage.list_versions(trip_id),
                choose=choose_with_llm, add_backups=add_backups,
            )
        except ChangeError as error:
            raise HTTPException(status_code=404, detail=str(error)) from None

        t = result.timings
        events.append(_event(trip_id, run_id, "apply", "node", f"Applied: {trigger}",
                             t.get("apply", 0)))
        for iteration in range(1, result.iterations + 1):
            events.append(_event(trip_id, run_id, "repair", "loop",
                                 "Replaced or rearranged only what broke", iteration=iteration))
        choices = [c for c in result.itinerary.get("repairs", []) if c.get("options", 0) > 1]
        if choices:
            by_llm = sum(1 for c in choices if c.get("chosen_by") == "llm")
            events.append(_event(trip_id, run_id, "repair_choice", "llm",
                                 f"LLM chose {by_llm} of {len(choices)} replacements"))
        events.append(_event(trip_id, run_id, "validator", "validation",
                             f"Checked the new plan: {result.terminal}", t.get("repair", 0),
                             terminal=result.terminal))
        events.append(_event(trip_id, run_id, "explain", "llm",
                             f"Explained the change ({result.explained_by})", t.get("explain", 0)))

        storage.save_itinerary(trip_id, result.itinerary)
        storage.save_replan(result.event)
        new_requirements = TripRequirements.model_validate(result.requirements)
        new_trip = trip.model_copy(update={
            "current_version": result.itinerary["version"],
            "status": "infeasible" if result.terminal == "INFEASIBLE" else "planned",
        })
        _save(new_trip, new_requirements, [], record["clarification_rounds"],
              record["clarification_exhausted"])
        events.append(_event(trip_id, run_id, "save", "node",
                             f"Saved version {result.itinerary['version']}"))
        status: Literal["done", "infeasible"] = (
            "infeasible" if result.terminal == "INFEASIBLE" else "done"
        )
        run = RunStatus(
            run_id=run_id, trip_id=trip_id, status=status, phase="adapt", step=status,
            step_index=5, step_count=5, terminal=result.terminal,
            message=result.explanation, started_at=started_at,
        )
    except HTTPException:
        raise
    except Exception as error:  # an unexpected failure: the current version stays as it was
        logger.exception("Change failed")
        events.append(_event(trip_id, run_id, "stop", "node", "The change could not be applied",
                             status="failed", error=str(error)))
        run = RunStatus(
            run_id=run_id, trip_id=trip_id, status="failed", phase="adapt", step="failed",
            step_index=5, step_count=5, terminal="ERROR",
            message="We couldn't apply that change. Your plan is unchanged.",
            started_at=started_at,
        )
    finally:
        lock.release()

    storage.save_run(run.model_dump(mode="json"))
    storage.append_trace(trip_id, run_id, events)
    return run_id


# --- endpoints ---------------------------------------------------------------------


@router.post("/{trip_id}/changes", response_model=ChangeResponse)
def submit_change(trip_id: str, request: ChangeRequest) -> ChangeResponse:
    _, _, requirements, itinerary = _current(trip_id)
    run_id = str(uuid4())
    day = request.day or 1
    started = perf_counter()
    interp = interpret(
        text=request.text, typed=request.typed, itinerary=itinerary,
        requirements=requirements.model_dump(mode="json"), day=day,
    )
    interpret_ms = int((perf_counter() - started) * 1000)
    raw_text = request.text or ""
    change = _change_event(trip_id, interp, raw_text, "user")
    first = [_event(
        trip_id, run_id, "interpret", "llm" if interp.source == "llm" else "node",
        f"Understood the change as '{interp.type}' ({interp.source})", interpret_ms,
    )]
    if interp.status != "ok":
        storage.append_trace(trip_id, run_id, first)
        return ChangeResponse(run_id="", change=change)
    run_id = _run_change(trip_id, change, interp.type, interp.payload, interp.trigger, first)
    return ChangeResponse(run_id=run_id, change=change)


@router.post("/{trip_id}/activities/{activity_id}/swap", response_model=PlanResponse)
def swap_backup(trip_id: str, activity_id: str, request: SwapRequest) -> PlanResponse:
    _, _, _, itinerary = _current(trip_id)
    activity = next(
        (a for day in itinerary["days"] for a in day["activities"] if a["id"] == activity_id),
        None,
    )
    if activity is None:
        raise HTTPException(status_code=404, detail="Activity not found")
    backup = next(
        (b for b in activity.get("backups") or [] if b.get("place_id") == request.backup_id), None
    )
    if backup is None:
        raise HTTPException(status_code=404, detail="Backup not found")
    name = (backup.get("place") or {}).get("name", "a backup")
    payload = {"activity_id": activity_id, "backup_id": request.backup_id}
    change = {
        "id": str(uuid4()), "trip_id": trip_id, "source": "user", "type": "preference",
        "payload": payload, "raw_text": "", "status": "applied",
    }
    run_id = str(uuid4())
    first = [_event(trip_id, run_id, "interpret", "node", f"You picked {name}")]
    return PlanResponse(run_id=_run_change(
        trip_id, change, "swap", payload, f"you picked {name}", first
    ))


@router.post("/{trip_id}/versions/{version}/restore", response_model=RestoreResponse)
def restore_version(trip_id: str, version: int) -> RestoreResponse:
    record = _load(trip_id)
    if version not in storage.list_versions(trip_id):
        raise HTTPException(status_code=404, detail="Version not found")
    trip = Trip.model_validate(record["trip"]).model_copy(update={"current_version": version})
    requirements = TripRequirements.model_validate(record["requirements"])
    _save(trip, requirements, [], record["clarification_rounds"],
          record["clarification_exhausted"])
    return RestoreResponse(version=version)


@router.post("/{trip_id}/simulate", response_model=PlanResponse)
def simulate(trip_id: str, request: SimulateRequest) -> PlanResponse:
    _, _, _, itinerary = _current(trip_id)
    run_id = str(uuid4())
    if request.type == "delay":
        change_type, payload, trigger = "time", {"minutes": 90, "day": 1}, (
            "you're running 90 minutes late"
        )
    elif request.type == "closure":
        candidates = [
            a for day in itinerary["days"] for a in day["activities"]
            if a.get("status") not in PROTECTED_STATUSES
        ]
        target = next((a for a in candidates if a["id"] == request.activity_id), None)
        target = target or (candidates[0] if candidates else None)
        if target is None:
            raise HTTPException(status_code=409, detail="No activity can be closed")
        change_type, payload = "closure", {"activity_id": target["id"]}
        trigger = f"{target['place'].get('name')} closed"
    else:
        raise HTTPException(status_code=422, detail="Only 'closure' and 'delay' can be simulated")
    change = {
        "id": str(uuid4()), "trip_id": trip_id, "source": "simulated", "type": change_type,
        "payload": payload, "raw_text": "", "status": "applied",
    }
    first = [_event(trip_id, run_id, "interpret", "node", f"Simulated: {trigger}")]
    return PlanResponse(run_id=_run_change(trip_id, change, change_type, payload, trigger, first))
