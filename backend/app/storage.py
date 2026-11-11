"""Saved data: trips, itinerary versions, runs and trace events (ADR-005).

One small database with four tables. Each row keeps its data as JSON, so the
API models can change without a database migration.

- Locally: a SQLite file (DATABASE_URL=sqlite:///./tripagent.db, the default).
- Online (Render): Postgres, for example a free Neon database. Render's free
  server wipes its disk on restart, so a SQLite file there would be lost.

Only this file talks to the database; the API calls the small functions below.
"""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Integer,
    MetaData,
    String,
    Table,
    create_engine,
    delete,
    insert,
    select,
    update,
)
from sqlalchemy.engine import Engine
from sqlalchemy.pool import StaticPool

from app.config import settings

metadata = MetaData()

trips = Table(
    "trips",
    metadata,
    Column("id", String, primary_key=True),
    Column("trip", JSON, nullable=False),  # the Trip
    Column("requirements", JSON, nullable=False),  # the TripRequirements
    Column("questions", JSON, nullable=False),  # open clarification questions
    Column("clarification_rounds", Integer, nullable=False, default=0),
    Column("clarification_exhausted", Boolean, nullable=False, default=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
)

itinerary_versions = Table(
    "itinerary_versions",
    metadata,
    Column("trip_id", String, primary_key=True),
    Column("version", Integer, primary_key=True),
    Column("itinerary", JSON, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
)

runs = Table(
    "runs",
    metadata,
    Column("id", String, primary_key=True),
    Column("trip_id", String, nullable=False, index=True),
    Column("run", JSON, nullable=False),  # the RunStatus
)

trace_events = Table(
    "trace_events",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("trip_id", String, nullable=False, index=True),
    Column("run_id", String, nullable=False),
    Column("event", JSON, nullable=False),  # one ExecutionEvent
)

_engine: Engine | None = None
LOCAL_DATABASE = "sqlite:///./tripagent.db"


def _database_url(url: str) -> str:
    """Neon and Render give 'postgres://' or 'postgresql://'; we use the psycopg 3 driver."""
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix) :]
    return url


def use_database(url: str) -> Engine:
    """Connect to `url` and create the tables if they are missing. Tests use 'sqlite://'."""
    global _engine
    url = _database_url(url.strip() or LOCAL_DATABASE)  # empty -> the local file
    if url.startswith("sqlite"):
        # In-memory SQLite needs one shared connection; a file is fine either way.
        options: dict[str, Any] = {"connect_args": {"check_same_thread": False}}
        if url in ("sqlite://", "sqlite:///:memory:"):
            options["poolclass"] = StaticPool
        engine = create_engine(url, **options)
    else:
        engine = create_engine(url, pool_pre_ping=True)  # Neon closes idle connections
    metadata.create_all(engine)
    _engine = engine
    return engine


def engine() -> Engine:
    """The current database, connecting to DATABASE_URL on first use."""
    return _engine or use_database(settings.DATABASE_URL)


def _now() -> datetime:
    return datetime.now(UTC)


# --- trips -------------------------------------------------------------------


def save_trip(
    trip: dict[str, Any],
    requirements: dict[str, Any],
    questions: list[dict[str, Any]],
    clarification_rounds: int,
    clarification_exhausted: bool,
) -> None:
    """Insert or replace one trip and its intake state."""
    row = {
        "trip": trip,
        "requirements": requirements,
        "questions": questions,
        "clarification_rounds": clarification_rounds,
        "clarification_exhausted": clarification_exhausted,
        "updated_at": _now(),
    }
    with engine().begin() as db:
        changed = db.execute(update(trips).where(trips.c.id == trip["id"]).values(**row))
        if changed.rowcount == 0:
            db.execute(insert(trips).values(id=trip["id"], **row))


def get_trip(trip_id: str) -> dict[str, Any] | None:
    """The trip row as a dict, or None if there is no such trip."""
    with engine().connect() as db:
        row = db.execute(select(trips).where(trips.c.id == trip_id)).mappings().first()
    return dict(row) if row else None


# --- itinerary versions ------------------------------------------------------


def save_itinerary(trip_id: str, itinerary: dict[str, Any]) -> None:
    """Store one itinerary version. Versions are never overwritten (ADR-005)."""
    with engine().begin() as db:
        db.execute(
            insert(itinerary_versions).values(
                trip_id=trip_id,
                version=itinerary["version"],
                itinerary=itinerary,
                created_at=_now(),
            )
        )


def get_itinerary(trip_id: str, version: int | None = None) -> dict[str, Any] | None:
    """One version, or the newest one when `version` is None."""
    query = select(itinerary_versions.c.itinerary).where(itinerary_versions.c.trip_id == trip_id)
    if version is None:
        query = query.order_by(itinerary_versions.c.version.desc()).limit(1)
    else:
        query = query.where(itinerary_versions.c.version == version)
    with engine().connect() as db:
        return db.execute(query).scalar()


def list_versions(trip_id: str) -> list[int]:
    query = (
        select(itinerary_versions.c.version)
        .where(itinerary_versions.c.trip_id == trip_id)
        .order_by(itinerary_versions.c.version)
    )
    with engine().connect() as db:
        return list(db.execute(query).scalars())


# --- runs --------------------------------------------------------------------


def save_run(run: dict[str, Any]) -> None:
    with engine().begin() as db:
        changed = db.execute(update(runs).where(runs.c.id == run["run_id"]).values(run=run))
        if changed.rowcount == 0:
            db.execute(insert(runs).values(id=run["run_id"], trip_id=run["trip_id"], run=run))


def get_run(run_id: str) -> dict[str, Any] | None:
    with engine().connect() as db:
        return db.execute(select(runs.c.run).where(runs.c.id == run_id)).scalar()


def run_id_for_trip(trip_id: str) -> str | None:
    """The trip's planning run, if it already has one."""
    with engine().connect() as db:
        return db.execute(select(runs.c.id).where(runs.c.trip_id == trip_id).limit(1)).scalar()


# --- trace events ------------------------------------------------------------


def save_trace(trip_id: str, run_id: str, events: list[dict[str, Any]]) -> None:
    """Store the trace of one run (replacing an earlier copy of that run's trace)."""
    with engine().begin() as db:
        db.execute(delete(trace_events).where(trace_events.c.run_id == run_id))
        if events:
            db.execute(
                insert(trace_events),
                [{"trip_id": trip_id, "run_id": run_id, "event": event} for event in events],
            )


def get_trace(trip_id: str) -> list[dict[str, Any]]:
    """All trace events of a trip, oldest first."""
    query = (
        select(trace_events.c.event)
        .where(trace_events.c.trip_id == trip_id)
        .order_by(trace_events.c.id)
    )
    with engine().connect() as db:
        return list(db.execute(query).scalars())
