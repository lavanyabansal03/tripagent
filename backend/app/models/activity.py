from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


class Activity(BaseModel):
    id: str = Field(min_length=1)
    trip_id: str = Field(min_length=1)
    version: int = Field(ge=0)
    day: int = Field(ge=1)

    place_id: str = Field(min_length=1)

    start: datetime
    end: datetime

    est_cost: float | None = Field(default=None, ge=0)

    cost_basis: Literal[
        "known", "price_level", "free", "unknown"
    ] = "unknown"

    priority: Literal[
        "high", "medium", "low"
    ] = "medium"

    purpose_tags: list[str] = Field(default_factory=list)

    status: Literal[
        "planned", "done", "locked", "cancelled"
    ] = "planned"

    change_type: Literal[
        "added", "replaced", "moved",
        "removed", "kept"
    ] | None = None

    reason: str | None = None

    warnings: list[dict[str, Any]] = Field(default_factory=list)
    backups: list[dict[str, Any]] = Field(default_factory=list)

    place: dict[str, Any]

    splurge: bool = False

    @model_validator(mode="after")
    def validate_activity(self):

        if self.start.tzinfo is None or self.end.tzinfo is None:
            raise ValueError("Activity times must include timezone offsets")

        if self.start >= self.end:
            raise ValueError("Activity must end after it starts")

        return self
