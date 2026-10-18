from datetime import date, time
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class MustDo(BaseModel):
    text: str = Field(min_length=1)
    splurge: bool = False
    place_id: str | None = None


class Travelers(BaseModel):
    adults: int = Field(default=1, ge=1, le=10)
    children: int = Field(default=0, ge=0, le=10)
    infants: int = Field(default=0, ge=0, le=5)

    @property
    def solo(self) -> bool:
        return (
            self.adults == 1
            and self.children == 0
            and self.infants == 0
        )


class MedicalAccess(BaseModel):
    required: bool = False
    max_minutes: int = Field(default=20, ge=5, le=60)


class TripRequirements(BaseModel):


    trip_id: str = Field(min_length=1)
    version: int = Field(ge=0)

    destination: str = Field(min_length=1)
    start_date: date
    end_date: date


    budget_min: float | None = Field(default=None, ge=0)
    budget_max: float | None = Field(default=None, ge=0)

    budget_strictness: Literal[
        "strict", "flexible", "none"
    ] = "flexible"

    budget_level: Literal[
        "cheap", "moderate", "expensive"
    ] | None = None

    must_do: list[MustDo] = Field(default_factory=list)


    mode: Literal[
        "walking", "transit", "driving", "cycling"
    ]

    pace: Literal[
        "relaxed", "moderate", "packed"
    ]

    interests: list[str]
    avoid: list[str]

    tourist_local_ratio: float = Field(ge=0, le=100)
    max_travel_min: int = Field(ge=0)

    daily_start: time
    daily_end: time


    dietary: list[
        Literal[
            "vegetarian",
            "vegan",
            "halal",
            "kosher",
            "gluten_free",
            "dairy_free",
            "nut_allergy"
        ]
    ] = Field(default_factory=list)


    accessibility: list[
        Literal[
            "wheelchair",
            "step_free",
            "limited_walking",
            "visual",
            "hearing"
        ]
    ] = Field(default_factory=list)


    free_text: str

    provenance: dict[
        str,
        Literal["explicit", "inferred", "default"]
    ]


    travelers: Travelers = Field(default_factory=Travelers)

    kid_friendly: bool | None = None

    energy: Literal[
        "calm", "balanced", "adventurous"
    ] = "balanced"


    safety_first: bool = False


    medical_access: MedicalAccess = Field(
        default_factory=MedicalAccess
    )


    indoor_outdoor: Literal[
        "indoor", "outdoor", "mix"
    ] = "mix"

    weather_backup: bool = True

  
    @model_validator(mode="after")
    def validate_requirements(self):

        # Check trip dates
        if self.start_date > self.end_date:
            raise ValueError(
                "Start date cannot be after end date"
            )

        # Check budget range
        if (
            self.budget_min is not None
            and self.budget_max is not None
        ):
            if self.budget_min > self.budget_max:
                raise ValueError(
                    "Minimum budget cannot exceed maximum budget"
                )

        # Check daily schedule
        if self.daily_start >= self.daily_end:
            raise ValueError(
                "Daily start time must be before daily end time"
            )

        # Derive kid-friendly preference from travelers
        has_children = (
            self.travelers.children > 0
            or self.travelers.infants > 0
        )

        if self.kid_friendly is None:
            self.kid_friendly = has_children
        elif self.kid_friendly != has_children:
            raise ValueError(
                "kid_friendly must match traveler information"
            )

        return self
