"""Place: one real-world location (a cafe, a park, a museum...).

TEMPORARY HOME. This copy mirrors the Place type in frontend/src/types/index.ts and the
draft in docs/contracts.md. When the shared Pydantic models land in backend/app/models/,
delete this file and import Place from there instead.
"""

from typing import Literal, Self

from pydantic import BaseModel, Field, model_validator

ExperienceType = Literal[
    "food", "cafe", "nature", "culture", "shopping", "nightlife", "event", "landmark"
]
CostBasis = Literal["known", "price_level", "free", "unknown"]
LocalSignal = Literal["tourist", "local", "hidden", "unknown"]
Provenance = Literal["explicit", "inferred", "default"]
Source = Literal["mapbox", "foursquare", "seed"]


class Place(BaseModel):
    """A place we might put in a trip. Anything we do not know stays None (never zero)."""

    id: str = Field(min_length=1)
    sources: list[Source]
    provider_ids: dict[str, str] = Field(default_factory=dict)
    name: str = Field(min_length=1)
    categories: list[str] = Field(default_factory=list)
    experience_types: list[ExperienceType] = Field(default_factory=list)
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    address: str
    price_level: Literal[1, 2, 3, 4] | None = None
    est_cost_low: float | None = Field(default=None, ge=0)
    est_cost_high: float | None = Field(default=None, ge=0)
    cost_basis: CostBasis = "unknown"
    hours: str | None = None
    rating: float | None = None
    review_count: int | None = Field(default=None, ge=0)
    popularity: float | None = None
    local_signal: LocalSignal = "unknown"
    field_provenance: dict[str, Provenance] = Field(default_factory=dict)
    retrieved_at: str
    tip: str | None = None

    @model_validator(mode="after")
    def _check_cost_range(self) -> Self:
        low, high = self.est_cost_low, self.est_cost_high
        if low is not None and high is not None and low > high:
            raise ValueError("est_cost_low must not be more than est_cost_high")
        return self
