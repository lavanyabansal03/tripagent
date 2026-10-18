from datetime import datetime, time
from typing import Literal

from pydantic import BaseModel, Field, model_validator


Weekday = Literal[
    "monday", "tuesday", "wednesday",
    "thursday", "friday", "saturday", "sunday"
]

DietaryPreference = Literal[
    "vegetarian", "vegan", "halal", "kosher",
    "gluten_free", "dairy_free", "nut_allergy"
]

ExperienceCategory = Literal[
    "food", "cafe", "nature", "culture",
    "shopping", "nightlife", "event", "landmark"
]


class OpeningPeriod(BaseModel):
    day: Weekday
    open: time
    close: time
    closes_next_day: bool = False


class Place(BaseModel):

    # Basic information
    id: str = Field(min_length=1)
    sources: list[Literal["mapbox", "foursquare", "seed"]]
    provider_ids: dict[str, str]

    name: str = Field(min_length=1)
    categories: list[str]
    experience_types: list[ExperienceCategory]

    # Location
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    address: str

    # Cost information
    price_level: Literal[1, 2, 3, 4] | None = None

    est_cost_low: float | None = Field(default=None, ge=0)
    est_cost_high: float | None = Field(default=None, ge=0)

    cost_basis: Literal[
        "known", "price_level", "free", "unknown"
    ] = "unknown"

    # Opening hours
    hours: list[OpeningPeriod] | None = None

    # Ratings
    rating: float | None = None
    review_count: int | None = Field(default=None, ge=0)
    popularity: float | None = None

    # Local information
    local_signal: Literal[
        "tourist", "local", "hidden", "unknown"
    ] = "unknown"

    # Data source information
    field_provenance: dict[
        str, Literal["explicit", "inferred", "default"]
    ]

    retrieved_at: datetime
    tip: str | None = None

    # Accessibility
    accessibility_status: Literal[
        "yes", "limited", "no", "unknown"
    ] = "unknown"

    # Dietary information
    dietary_options: list[DietaryPreference] | None = None

    # Family suitability
    kid_friendly: bool | None = None

    @model_validator(mode="after")
    def validate_place(self):

        if (
            self.est_cost_low is not None
            and self.est_cost_high is not None
            and self.est_cost_low > self.est_cost_high
        ):
            raise ValueError(
                "Minimum estimated cost cannot exceed maximum"
            )

        return self
