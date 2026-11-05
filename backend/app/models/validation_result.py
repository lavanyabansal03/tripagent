
from typing import Literal

from pydantic import BaseModel, Field


class ValidationResult(BaseModel):
    id: str = Field(min_length=1)
    trip_id: str = Field(min_length=1)
    version: int = Field(ge=0)
    rule: str = Field(min_length=1)
    passed: bool
    severity: Literal["hard", "soft", "data-gap"]
    message: str = Field(min_length=1)
    activity_ids: list[str] = Field(default_factory=list)
