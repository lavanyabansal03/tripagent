# Data Contracts

## 1. Purpose

This document defines the shared data structures used by the TripAgent frontend and backend.

The frontend uses TypeScript interfaces, while the backend uses Python Pydantic models. Both must follow the same data contracts to ensure information is exchanged consistently.

These contracts describe the structure, required fields, data types, and validation rules for trips, traveler preferences, places, activities, and validation results.

Any changes to shared data models must be communicated in the team chat and approved by two reviewers before merging.

## 2. Source of Truth

The current frontend data structures are defined in:

`frontend/src/types/index.ts`

The corresponding Python models will be implemented in:

`backend/app/models/`

The validation functions will be implemented in:

`backend/app/validation/`

Kaleb's preference extraction model is currently defined in:

`backend/app/agents/preferences.py`

The frontend and backend models must remain consistent. Any differences in field names or data types should be documented and resolved before integration.

## 3. Trip Data Model

The Trip model stores basic information about a traveler's trip.

Source: `frontend/src/types/index.ts`

| Field | Type | Description |
|---|---|---|
| id | string | Unique identifier for the trip |
| destination | string | City or location the traveler plans to visit |
| start_date | string | Starting date of the trip |
| end_date | string | Ending date of the trip |
| status | string (enum) | Current planning status of the trip |
| current_version | number (integer) | Current version of the itinerary |
| created_at | string | Date and time when the trip was created |

### Allowed Trip Status Values

The `status` field must contain one of the following values:

- `draft`
- `planning`
- `planned`
- `adapting`
- `infeasible`
- `error`

### Example Trip

```json
{
  "id": "T001",
  "destination": "New York",
  "start_date": "2026-10-12",
  "end_date": "2026-10-15",
  "status": "draft",
  "current_version": 1,
  "created_at": "2026-10-08T10:00:00"
}
```

### Validation Rules

1. The trip ID must be a non-empty string.
2. The destination must be provided.
3. The start date must not be later than the end date.
4. The status must match one of the allowed values.
5. The current version must be a non-negative integer.
6. Dates must use the ISO format (YYYY-MM-DD).
7. The creation timestamp should use a consistent ISO 8601 datetime format.

## 4. TripRequirements Data Model

The TripRequirements model stores the traveler's preferences and constraints. These requirements guide the AI when creating an itinerary and help the validation system determine whether the itinerary meets the user's needs.

Source: `frontend/src/types/index.ts`

| Field | Type | Description |
|---|---|---|
| trip_id | string | Identifies the trip |
| version | number (integer) | Requirements version |
| destination | string | Travel destination |
| start_date | string | Trip starting date |
| end_date | string | Trip ending date |
| budget | number or null | Maximum budget specified by the traveler |
| budget_strictness | string (enum) | Whether the budget is strict or flexible |
| mode | string (enum) | Preferred transportation method |
| pace | string (enum) | Preferred travel pace |
| interests | string[] | Activities and experiences the traveler enjoys |
| avoid | string[] | Activities and experiences the traveler wants to avoid |
| tourist_local_ratio | number | Preference for tourist attractions versus local experiences |
| max_travel_min | number | Maximum preferred travel time between activities |
| daily_start | string | Preferred daily starting time |
| daily_end | string | Preferred daily ending time |
| dietary | string[] | Dietary requirements |
| accessibility | string[] | Accessibility requirements |
| free_text | string | Original travel preferences provided by the user |
| provenance | Record<string, Provenance> | Indicates whether each preference was explicit, inferred, or a default |

### Allowed Values

- `budget_strictness`: `strict`, `flexible`
- `mode`: `walking`, `transit`, `driving`, `cycling`
- `pace`: `relaxed`, `moderate`, `packed`
- `provenance`: `explicit`, `inferred`, `default`

### Proposed Validation Rules

1. The trip ID must be a non-empty string.
2. The start date must not be later than the end date.
3. The budget must be non-negative when provided.
4. A null budget indicates that no numeric budget has been specified.
5. Budget strictness must match an allowed value.
6. The tourist-local ratio must be between 0 and 100.
7. Maximum travel time must be non-negative.
8. Daily start and end times must follow the `HH:MM` format.
9. Transportation mode and travel pace must match their allowed values.
10. Provenance values must be `explicit`, `inferred`, or `default`.

### Integration Note: Kaleb's Preferences Model

Kaleb's proposed preference extraction model differs from the frontend TripRequirements interface in two important ways:

| Kaleb's Model | Frontend Model | Difference |
|---|---|---|
| `budget: str \| None` | `budget: number \| null` | Kaleb extracts qualitative budgets such as "cheap", while the frontend expects numeric amounts |
| `max_travel_minutes` | `max_travel_min` | Different field names |

These differences must be resolved before integration.

A qualitative budget such as "cheap" should not automatically be treated as a specific monetary amount without an agreed conversion rule or user clarification.

The shared TripRequirements contract retains the frontend field names for now. Any mapping from Kaleb's extracted preferences to TripRequirements requires team review.

## 5. Place Data Model

The Place model stores information about locations that TripAgent may recommend or include in an itinerary.

Source: `frontend/src/types/index.ts`

| Field | Type | Description |
|---|---|---|
| id | string | Unique identifier for the place |
| sources | string[] | Data providers such as mapbox, foursquare, or seed |
| provider_ids | Record<string, string> | Identifiers assigned by external providers |
| name | string | Name of the place |
| categories | string[] | Categories associated with the place |
| experience_types | ExperienceCategory[] | Types of experiences offered |
| lat | number | Latitude of the location |
| lng | number | Longitude of the location |
| address | string | Physical address |
| price_level | 1, 2, 3, 4, or null (optional) | General price category |
| est_cost_low | number or null (optional) | Minimum estimated cost |
| est_cost_high | number or null (optional) | Maximum estimated cost |
| cost_basis | CostBasis | How the cost was determined |
| hours | string or null (optional) | Opening hours |
| rating | number or null (optional) | Average user rating |
| review_count | number or null (optional) | Number of reviews |
| popularity | number or null (optional) | Popularity score |
| local_signal | LocalSignal | Whether the place is tourist-oriented or local |
| field_provenance | Record<string, Provenance> | Source of each field's information |
| retrieved_at | string | Timestamp when the information was retrieved |
| tip | string or null (optional) | Additional information about the place |

### Allowed Values

**ExperienceCategory:**
`food`, `cafe`, `nature`, `culture`, `shopping`, `nightlife`, `event`, `landmark`

**CostBasis:**
`known`, `price_level`, `free`, `unknown`

**LocalSignal:**
`tourist`, `local`, `hidden`, `unknown`

### Proposed Validation Rules

1. The place ID and name must be non-empty strings.
2. Latitude must be between -90 and 90.
3. Longitude must be between -180 and 180.
4. Price level must be between 1 and 4 when provided.
5. Estimated costs must be non-negative when provided.
6. The minimum estimated cost must not exceed the maximum estimated cost when both are available.
7. Cost basis must match one of the allowed values.
8. Experience categories must match the supported categories.
9. Local signal must match one of the allowed values.
10. The retrieval timestamp should use ISO 8601 format.

### Validation Considerations

Place information may come from external providers and may be incomplete or outdated.

A missing estimated cost should not automatically be treated as zero.

The validation system should distinguish between a place that is confirmed free and a place whose cost is unknown.

Opening hours and other provider information may need additional verification before an activity is included in the final itinerary.

## 6. Activity Data Model

The Activity model represents a scheduled activity within a travel itinerary. Each activity has a location, starting time, ending time, estimated cost, and priority.

Source: `frontend/src/types/index.ts`

| Field | Type | Description |
|---|---|---|
| id | string | Unique identifier for the activity |
| trip_id | string | Identifies the trip |
| version | number (integer) | Itinerary version |
| day | number (integer) | Day of the trip |
| place_id | string | Identifier of the associated place |
| start | string | Activity starting date and time |
| end | string | Activity ending date and time |
| est_cost | number or null | Estimated activity cost |
| cost_basis | CostBasis | How the estimated cost was determined |
| priority | Priority | Importance of the activity |
| purpose_tags | string[] | Categories or purposes of the activity |
| status | ActivityStatus | Current activity status |
| change_type | ChangeType or null (optional) | How the activity changed during replanning |
| reason | string or null (optional) | Explanation for the change |
| warnings | ValidationResult[] (optional) | Validation warnings related to the activity |
| backups | Backup[] (optional) | Alternative activities |
| place | Place | Full information about the associated place |

### Allowed Values

**Priority:** `high`, `medium`, `low`

**ActivityStatus:** `planned`, `done`, `locked`, `cancelled`

**ChangeType:** `added`, `replaced`, `moved`, `removed`, `kept`

**CostBasis:** `known`, `price_level`, `free`, `unknown`

### Proposed Validation Rules

1. The activity ID and trip ID must be non-empty strings.
2. Each activity must reference a valid place.
3. The starting time must be earlier than the ending time.
4. The day number must correspond to a valid day of the trip.
5. Estimated costs must be non-negative when provided.
6. Priority, status, change type, and cost basis must use their allowed values.
7. Start and end timestamps should use a consistent ISO 8601 datetime format.

### Activity Overlap Validation

Activities within the same itinerary must not overlap.

For two activities A and B, an overlap occurs when:

`A.start < B.end AND B.start < A.end`

Example:

| Activity | Start | End | Result |
|---|---|---|---|
| Museum | 10:00 | 12:00 | |
| Lunch | 11:30 | 13:00 | FAIL — Overlap |

Activities that touch at the same boundary do not overlap.

Example:

- Activity A: 10:00–11:00
- Activity B: 11:00–12:00
- Result: PASS

The validator should compare activities belonging to the same itinerary version using their complete dates and times.

### Activity Cost Validation

Each activity contains an estimated cost (`est_cost`) and a cost basis (`cost_basis`).

- `known`: The cost is based on available price information.
- `price_level`: The cost is estimated using a price category.
- `free`: The activity is identified as free.
- `unknown`: The cost is not known.

An unknown cost must not automatically be treated as zero.

Budget validation should follow the team's agreed policy for handling uncertain costs.

## 7. ValidationResult Data Model

The ValidationResult model represents the outcome of a validation check. It tells the system whether a rule passed or failed and identifies the activities involved.

Source: `frontend/src/types/index.ts`

| Field | Type | Description |
|---|---|---|
| id | string | Unique identifier for the validation result |
| trip_id | string | Trip associated with the validation result |
| version | number (integer) | Itinerary version being validated |
| rule | string | Name of the validation rule |
| passed | boolean | Whether the validation check passed |
| severity | Severity | Importance of the validation result |
| message | string | Explanation of the validation outcome |
| activity_ids | string[] | Identifiers of activities involved |

### Allowed Severity Values

- `hard`: A constraint violation that must be addressed.
- `soft`: A warning or preference that may be flexible.
- `data-gap`: Missing or insufficient information prevents a confident decision.

### Example: Overlapping Activities

```json
{
  "id": "V001",
  "trip_id": "T001",
  "version": 1,
  "rule": "no_overlap",
  "passed": false,
  "severity": "hard",
  "message": "Museum and lunch overlap between 11:30 and 12:00.",
  "activity_ids": ["A001", "A002"]
}
```

### Example: Budget Validation

```json
{
  "id": "V002",
  "trip_id": "T001",
  "version": 1,
  "rule": "budget_limit",
  "passed": false,
  "severity": "hard",
  "message": "Estimated trip cost exceeds the specified budget.",
  "activity_ids": ["A001", "A002", "A003"]
}
```

### Proposed Validation Rules

1. Each validation result must have a unique, non-empty identifier.
2. The trip ID and itinerary version must identify the itinerary being checked.
3. The `rule` field must identify the validation check performed.
4. The `passed` field must contain a boolean value (`true` or `false`).
5. The `severity` field must match an allowed value.
6. The `message` field should clearly explain the validation outcome.
7. The `activity_ids` field must contain a list of relevant activity identifiers.

### Validation Behavior

The validation system should return structured results rather than only printing error messages.

For example:

- If two activities overlap, the overlap validator returns a failed ValidationResult.
- If the itinerary exceeds a strict budget, the budget validator returns a failed ValidationResult.
- If the cost of an activity is unknown, the validator should report the uncertainty according to the team's agreed policy.

These results can be used by the AI agents to identify problems and revise the itinerary.

The exact rule names and handling of uncertain costs must be confirmed by the team.
