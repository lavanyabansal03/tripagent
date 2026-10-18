# Data Contracts

> **Scope:** Shared data contracts for TripAgent, including trip preferences, provider-compatible place fields, workflow events, and validation rules. These contracts define the target data format for frontend and backend implementation.

## 1. Purpose

This document defines the shared data structures that TripAgent's frontend (TypeScript), backend (Python/Pydantic), preferences extraction, tools, and AI workflow exchange.

It preserves the original contract's field names and models except where the team agreed to revise them. In particular, budget changes from one numeric field to a range and splurges; Place details reflect provider data availability and distinguish unknown values from confirmed ones.

## 2. Source of Truth and Conventions

- **Existing implementation reference:** `frontend/src/types/index.ts` and the current backend API models. Preserve unchanged fields from these implementations; this document specifies agreed additions and proposed normalizations. Once reviewed and merged, the final contract and code must remain synchronized.
- **Pydantic implementation:** `backend/app/models/`.
- **Validation code:** `backend/app/validation/`.
- **Tests:** `backend/tests/`.
- **Preferences extraction:** `backend/app/agents/preferences.py`.
- JSON keys use `snake_case`.
- Dates use `YYYY-MM-DD`. Timestamps use ISO 8601. Scheduled activity timestamps must include a UTC offset (for example, `2026-10-20T14:00:00-07:00`); use the destination’s correct offset for the activity date, including daylight saving time. A destination timezone identifier is still needed when generating future local times, because a fixed offset alone does not capture daylight-saving transitions.
- Required fields are listed without **optional**.
- `T | null` means the value may be `null`; **optional** means the key can be omitted.
- Defined defaults apply when normalizing input.
- Enums are case-sensitive.
- `Provenance` = `explicit | inferred | default`.
- `Severity` = `hard | soft | data-gap`.
- Unknown external/provider values must never be converted to `0`, `false`, or an unverified claim.
- If a check cannot be confirmed, return a `data-gap` result and display *Not confirmed*.
- Shared data-format changes require two PR reviewers before merging.

## 3. Trip Data Model

The Trip model stores basic information about a traveler's trip.

| Field | Type | Notes |
|---|---|---|
| `id` | string | Nonempty trip ID |
| `destination` | string | Nonempty destination |
| `start_date`, `end_date` | date string | Inclusive trip range; start <= end |
| `status` | `draft \| planning \| planned \| adapting \| infeasible \| error` | Trip lifecycle |
| `current_version` | integer | Nonnegative itinerary version |
| `created_at` | ISO 8601 datetime string | Creation time |

### Validation Rules

1. Trip ID and destination must be nonempty.
2. Start date must not be later than end date.
3. Status must match an allowed value.
4. Current version must be nonnegative.
5. Dates and timestamps must follow the specified formats.

## 4. TripRequirements Data Model

The TripRequirements model stores travel preferences and constraints.

The agreed Oct 9 budget direction replaces the original single `budget: number | null` in `TripRequirements` with `budget_min`, `budget_max`, and splurges. Existing API requests and UI controls still using `budget` require a small migration/normalization step; do not silently pass both formats as independent canonical fields.

| Field | Type | Default / Rules |
|---|---|---|
| `trip_id` | string | Required |
| `version` | integer | Required, nonnegative |
| `destination` | string | Required |
| `start_date`, `end_date` | date string | Required; start <= end |
| `budget_min` | number or null | Default `null`; >= 0 if provided |
| `budget_max` | number or null | Default `null`; >= 0 and >= budget_min |
| `budget_strictness` | `strict \| flexible \| none` | Default `flexible` |
| `budget_level` | `cheap \| moderate \| expensive \| null` | Default `null` |
| `must_do` | `MustDo[]` | Default `[]` |
| `mode` | `walking \| transit \| driving \| cycling` | Transportation preference |
| `pace` | `relaxed \| moderate \| packed` | Travel pace |
| `interests` | string[] | Preferred activities |
| `avoid` | string[] | Activities to avoid |
| `tourist_local_ratio` | number | 0–100 |
| `max_travel_min` | number | Nonnegative |
| `daily_start`, `daily_end` | `HH:MM` string | Preferred daily schedule |
| `dietary` | `DietaryPreference[]` | Default `[]` |
| `accessibility` | `AccessibilityPreference[]` | Default `[]` |
| `free_text` | string | Original user preferences |
| `provenance` | `Record<string, Provenance>` | Preference source |
| `travelers` | `Travelers` | Default `{adults: 1, children: 0, infants: 0}` |
| `kid_friendly` | boolean | Derived from children/infants |
| `energy` | `calm \| balanced \| adventurous` | Default `balanced` |
| `safety_first` | boolean | Default `false` |
| `medical_access` | `MedicalAccess` | Default `{required: false, max_minutes: 20}` |
| `indoor_outdoor` | `indoor \| outdoor \| mix` | Default `mix` |
| `weather_backup` | boolean | Default `true` |

### 4.1 Dietary Preferences

Allowed values:

- `vegetarian`
- `vegan`
- `halal`
- `kosher`
- `gluten_free`
- `dairy_free`
- `nut_allergy`

Unknown dietary information must not be treated as confirmation that a restaurant meets the requirement.

### 4.2 Accessibility Preferences

Allowed values:

- `wheelchair`
- `step_free`
- `limited_walking`
- `visual`
- `hearing`

Missing accessibility information must be reported as unconfirmed.

### 4.3 Travelers

| Field | Type | Allowed Values | Default |
|---|---|---|---|
| `adults` | integer | 1–10 | 1 |
| `children` | integer | 0–10 | 0 |
| `infants` | integer | 0–5 | 0 |
| `solo` | derived boolean | True when traveling alone | Derived |

`solo` is derived as:

`adults == 1 && children == 0 && infants == 0`

### 4.4 MedicalAccess

| Field | Type | Default |
|---|---|---|
| `required` | boolean | false |
| `max_minutes` | integer (5–60) | 20 |

### 4.5 Budget Interpretation

1. `budget_min` and `budget_max` must be nonnegative when provided.
2. `budget_min` must not exceed `budget_max`.
3. `budget_strictness: none` disables budget-limit validation.
4. `budget_level` represents qualitative preferences rather than numerical amounts.
5. A request such as "cheap trip" must not automatically become a numeric budget.
6. `budget_min` guides itinerary ranking and is not a failure threshold.
7. Splurge activities are excluded from the regular budget calculation.
8. Unknown costs must not be interpreted as zero.

### 4.6 Safety Preferences

The `safety_first` field is controlled by the traveler.

The system must not infer gender, age, disability, or safety needs from a name or writing style.

When enabled, planning may prefer:

- Daylight activities.
- Busy, well-reviewed locations.
- Shorter walking distances after dark.
- Less isolated routes.

The system must not claim that a location is guaranteed safe.

### 4.7 Weather and Indoor/Outdoor Preferences

`indoor_outdoor` supports:

- `indoor`
- `outdoor`
- `mix`

`weather_backup` indicates whether indoor alternatives should be considered for outdoor activities.

Live weather validation requires a connected weather provider. Until then, weather preferences must not be presented as verified forecasts.

## 5. Place Data Model

The Place model stores information about locations recommended by TripAgent.

The structure supports incomplete external API information.

| Field | Type | Notes |
|---|---|---|
| `id` | string | Required |
| `sources` | `Array<mapbox \| foursquare \| seed>` | Existing provider labels |
| `provider_ids` | `Record<string, string>` | Provider identifiers |
| `name` | string | Nonempty |
| `categories` | string[] | Provider categories |
| `experience_types` | `ExperienceCategory[]` | Experience categories |
| `lat`, `lng` | number | Valid coordinates |
| `address` | string | Location address |
| `price_level` | `1 \| 2 \| 3 \| 4 \| null` (optional) | General price category |
| `est_cost_low` | number or null (optional) | Minimum estimated cost |
| `est_cost_high` | number or null (optional) | Maximum estimated cost |
| `cost_basis` | `known \| price_level \| free \| unknown` | Cost evidence |
| `hours` | `OpeningPeriod[] \| null` (optional) | Structured opening hours |
| `rating` | number or null (optional) | Provider rating |
| `review_count` | number or null (optional) | Number of reviews |
| `popularity` | number or null (optional) | Popularity information |
| `local_signal` | `tourist \| local \| hidden \| unknown` | Local classification |
| `field_provenance` | `Record<string, Provenance>` | Information source |
| `retrieved_at` | ISO 8601 datetime string | Retrieval timestamp |
| `tip` | string or null (optional) | Additional place information |
| `accessibility_status` | `yes \| limited \| no \| unknown` (optional) | Default `unknown` |
| `dietary_options` | `DietaryPreference[] \| null` (optional) | Default `null` |
| `kid_friendly` | boolean or null (optional) | Default `null` |

### 5.1 Experience Categories

Supported categories:

- `food`
- `cafe`
- `nature`
- `culture`
- `shopping`
- `nightlife`
- `event`
- `landmark`

### 5.2 OpeningPeriod Data Model

The validation-facing Place format uses structured periods. Existing frontend/provider code may currently expose `hours` as text; that data should be normalized at the provider-to-domain boundary where reliably parseable, rather than requiring a provider to return this shape. If parsing is uncertain, use `null` for normalized hours and retain raw provider text separately where useful.

| Field | Type | Description |
|---|---|---|
| `day` | weekday enum | Day of the week |
| `open` | `HH:MM` | Opening time |
| `close` | `HH:MM` | Closing time |
| `closes_next_day` | boolean | Default false |

Supported weekdays:

`monday`, `tuesday`, `wednesday`, `thursday`, `friday`, `saturday`, `sunday`

Example:

```json
{
  "day": "monday",
  "open": "09:00",
  "close": "17:00",
  "closes_next_day": false
}
```

If opening hours are unavailable, use `null`.

An empty list does not automatically prove that a place is permanently closed.

Holiday closures and timezone differences must be handled separately.

### 5.3 Accessibility Status

The accessibility field supports four states:

- `yes`: Accessibility is reported as available.
- `limited`: Partial accessibility is reported.
- `no`: Accessibility is reported as unavailable.
- `unknown`: Information is unavailable.

A generic accessibility status does not confirm every specific accessibility requirement.

### 5.4 Dietary Information

`dietary_options` is optional.

- `null`: Dietary information is unknown.
- `[]`: No supported options are confirmed, only when reliable provider data establishes this.
- `["vegetarian", "vegan"]`: Reported dietary options.

Dietary categories must not be treated as guarantees of allergen safety.

### 5.5 Kid-Friendly Information

`kid_friendly` may contain:

- `true`
- `false`
- `null`

When suitability is inferred from categories such as parks or zoos, its provenance must be recorded as inferred.

### 5.6 External Provider Data Rules

**Nitin’s provider spike notes (reported observations, not guarantees):** Mapbox returned structured opening-hour periods for approximately 80% of tested places. Exact ticket prices were not available in the tested responses; Foursquare Premium price tiers were documented but not tested. Ratings, accessibility, dietary information, and family suitability may be missing or inferred. These findings describe the tested sample, not guaranteed provider coverage.

- `Place.cost_basis = "price_level"` indicates an estimate derived from a general price tier, **not a verified admission price**; keep the estimated amount `null` if no defensible estimate is possible.
- `Place.field_provenance["kid_friendly"] = "inferred"` whenever a category is used to guess suitability. An inferred `true` is not confirmation.
- For `accessibility_status`, use `"unknown"` when there is no trustworthy information; for `dietary_options`, use `null` when unknown, not `[]`.
- Keep hospitals out of the `Place` fields: obtain nearby hospitals through a separate place search when needed.

1. Missing external information must remain unknown.
2. Estimated costs must not be represented as verified ticket prices.
3. Price levels do not equal actual ticket costs.
4. Ratings and review counts are optional.
5. Accessibility and dietary support must not be assumed.
6. Opening-hour information must be normalized before validation.
7. Hospital searches are handled separately rather than stored in every Place.
8. Provider limitations must be reflected in validation results.

## 6. Activity Data Model

The Activity model represents scheduled events in an itinerary.

| Field | Type | Notes |
|---|---|---|
| `id` | string | Activity identifier |
| `trip_id` | string | Associated trip |
| `version` | integer | Itinerary version |
| `day` | integer | Positive trip day |
| `place_id` | string | Associated place |
| `start` | ISO 8601 datetime string | Start time |
| `end` | ISO 8601 datetime string | End time |
| `est_cost` | number or null | Estimated cost |
| `cost_basis` | `known \| price_level \| free \| unknown` | Cost evidence |
| `priority` | `high \| medium \| low` | Activity importance |
| `purpose_tags` | string[] | Activity purposes |
| `status` | `planned \| done \| locked \| cancelled` | Activity state |
| `change_type` | `added \| replaced \| moved \| removed \| kept \| null` (optional) | Replanning change |
| `reason` | string or null (optional) | Explanation |
| `warnings` | `ValidationResult[]` (optional) | Validation warnings |
| `backups` | `Backup[]` (optional) | Alternative activities |
| `place` | `Place` | Associated place information |
| `splurge` | boolean | Default false |

### 6.1 Backup Data Model

| Field | Type |
|---|---|
| `activity_id` | string |
| `place_id` | string |
| `rank` | number |
| `purpose_similarity` | number |
| `cost_delta` | number |
| `travel_delta_min` | number |
| `validated_at` | ISO 8601 datetime string |

### 6.2 Activity Cost Convention (Proposed Implementation Decision)

- `est_cost` is the **estimated total cost for the whole traveling group**, after any required per-person calculation.
- Example: three paying travelers × $20 per ticket gives `est_cost: 60`; a $50 per-group price gives `est_cost: 50`.
- When the quote or number of paying travelers cannot be established, use `null`; do not substitute `0`.
- Splurge costs count toward the overall estimated trip total but not the regular budget limit.
- `est_cost` alone does not store the provider’s raw per-person price or price basis; preserve that upstream if an audit or recalculation is needed.

### 6.3 Activity Validation Rules

1. Activity identifiers must be valid.
2. Start time must be earlier than end time.
3. Estimated costs must be nonnegative when provided.
4. Activity status and priority must match allowed values.
5. Activities must reference valid places.
6. Splurge activities must be excluded from regular budget calculations.
7. Splurge activities must receive high priority.
8. Replanning must not remove requested splurges without user confirmation.

## 7. ValidationResult Data Model

The ValidationResult model records the outcome of validation checks.

| Field | Type | Description |
|---|---|---|
| `id` | string | Validation identifier |
| `trip_id` | string | Associated trip |
| `version` | integer | Itinerary version |
| `rule` | string | Validation rule |
| `passed` | boolean | Whether the check passed |
| `severity` | `hard \| soft \| data-gap` | Severity |
| `message` | string | Validation explanation |
| `activity_ids` | string[] | Related activities |

### Severity Values

**hard:** A constraint violation requiring correction.

**soft:** A warning or flexible preference violation.

**data-gap:** Insufficient information to determine validity.

Unknown information must not be marked as a confirmed pass.

### Example ValidationResult

```json
{
  "id": "V001",
  "trip_id": "T001",
  "version": 1,
  "rule": "no_overlap",
  "passed": false,
  "severity": "hard",
  "message": "Two scheduled activities overlap.",
  "activity_ids": ["A001", "A002"]
}
```

## 8. MustDo Data Model

The MustDo model represents activities the traveler specifically requests.

| Field | Type | Default / Rules |
|---|---|---|
| `text` | string | Required |
| `splurge` | boolean | Default false |
| `place_id` | string or null | Default null |

### MustDo Rules

1. Text must be nonempty.
2. Splurge defaults to false.
3. Place ID may remain null until discovery.
4. Splurges are excluded from regular budget calculations.
5. Splurges receive high activity priority.
6. Requested activities must not be invented if discovery fails.
7. The system must ask for clarification if a requested place cannot be identified.

### Example MustDo

```json
{
  "text": "Seaplane tour",
  "splurge": true,
  "place_id": null
}
```

## 9. Question Data Model

The Question model represents a question asked when the system requires clarification.

| Field | Type | Description |
|---|---|---|
| `id` | string | Unique question ID |
| `field` | string | Field requiring clarification |
| `text` | string | Question shown to the traveler |
| `options` | string[] (optional) | Suggested answers |

### Example Question

```json
{
  "id": "Q001",
  "field": "budget_max",
  "text": "What is your maximum budget?",
  "options": ["200", "500", "No limit"]
}
```

### Question Rules

1. Question ID must be nonempty.
2. The field must identify the information requiring clarification.
3. Question text must be provided.
4. Options must contain strings when supplied.
5. Critical missing or contradictory information should trigger clarification before planning.

## 10. ExecutionEvent Data Model

The ExecutionEvent model records individual steps performed by the AI workflow.

| Field | Type | Description |
|---|---|---|
| `id` | string | Event identifier |
| `trip_id` | string | Associated trip |
| `run_id` | string | Planning run |
| `node` | string | Workflow component |
| `type` | `node \| tool \| llm \| validation \| loop` | Event type |
| `iteration` | integer | Nonnegative |
| `status` | `started \| ok \| failed \| degraded \| skipped` | Execution status |
| `duration_ms` | number | Nonnegative milliseconds |
| `metadata` | `Record<string, unknown>` | Additional event information |
| `ts` | ISO 8601 datetime string | Timestamp |

### Example ExecutionEvent

```json
{
  "id": "E001",
  "trip_id": "T001",
  "run_id": "R001",
  "node": "validation",
  "type": "validation",
  "iteration": 1,
  "status": "ok",
  "duration_ms": 120,
  "metadata": {
    "checks_completed": 2
  },
  "ts": "2026-10-13T14:30:00Z"
}
```

### ExecutionEvent Rules

1. Event identifiers must be nonempty.
2. Event type must match allowed values.
3. Execution status must match allowed values.
4. Iteration must be nonnegative.
5. Duration must be nonnegative.
6. Metadata must be a structured object.
7. Timestamps must follow ISO 8601.
8. Sensitive information and API secrets must not be stored in event metadata.

## 11. Other Existing Frontend Models

The revised contract preserves the following existing frontend entities:

- `EventItem`
- `ItineraryVersion`
- `ChangeEvent`
- `ReplanDiff`
- `ReplanEvent`
- `LatLng`
- `DayCluster`
- `RouteLeg`
- `ItineraryDay`
- `Itinerary`
- `RunStatus`
- `InfeasibleReport`
- `CreateTripResponse`
- `PlanResponse`

Their definitions remain as specified in:

`frontend/src/types/index.ts`

The existing `ChangeEvent.type` continues to support `weather`.

These entities must not be removed or renamed without an agreed contract change.

## 12. Shared Validation Rules

### 12.1 Activity Overlap Validation

Rule name: `no_overlap`

For two active activities A and B belonging to the same trip and itinerary version:

`A.start < B.end AND B.start < A.end`

If the condition is true, the activities overlap.

The validator returns:

- `passed: false`
- `severity: hard`
- Relevant activity IDs
- An explanatory message

Activities that touch at exactly the same boundary do not overlap.

Example:

| Activity | Start | End | Result |
|---|---|---|---|
| Museum | 10:00 | 12:00 | |
| Lunch | 11:30 | 13:00 | FAIL |

Cancelled activities are excluded from the active schedule check.

Complete dates and times must be compared rather than time-of-day alone.

### 12.2 Budget Validation

Rule name: `budget_limit`

1. Validate nonnegative budget limits.
2. Ensure budget_min does not exceed budget_max.
3. Skip budget validation when budget_strictness is `none`.
4. Exclude splurge activities from the regular budget calculation.
5. Include known, non-splurge activity costs in the budget total.
6. Compare the total against budget_max when a maximum is provided.
7. A strict budget violation produces a hard failure.
8. A flexible budget violation produces a soft warning.
9. Unknown non-splurge costs produce a data-gap result.
10. Budget minimum is guidance for ranking, not a failure threshold.
11. Qualitative budget levels must not be converted to numeric limits without clarification or an agreed rule.
12. **If the team adopts the group-total convention**, normalize `Activity.est_cost` to the total for the traveling group before budget validation. Multiply a per-person quoted price by the number of paying travelers only once; never multiply an already-group-total `est_cost` again.
13. If a provider quote does not say whether it is per-person or per-group, the cost is not confirmed and budget validation must report `data-gap` rather than guess.
14. Group-vs-person budget scope and the paying-traveler calculation remain open decisions in the Oct 9 proposal. Do not claim these are already approved.

### Example Budget Calculation

Maximum budget: $500

| Activity | Cost | Splurge |
|---|---|---|
| Museum | $50 | No |
| Lunch | $40 | No |
| Shopping | $100 | No |
| Helicopter tour | $350 | Yes |

Regular budget total:

`50 + 40 + 100 = 190`

Splurge total:

`350`

Overall estimated total:

`540`

Budget comparison:

`190 <= 500`

Result: PASS, assuming all relevant costs are known and use the same cost basis.

### 12.3 Accessibility Validation

1. Confirmed incompatibility with a required accessibility condition produces a hard failure.
2. Missing accessibility information produces data-gap.
3. Generic accessibility status does not confirm every specific accommodation.
4. The system must not claim accessibility without reliable supporting information.

### 12.4 Dietary Validation

1. Dietary preferences apply to food-related locations.
2. Missing dietary information produces data-gap.
3. Documented mismatches may produce soft warnings.
4. Nut-allergy requirements must always include a recommendation to confirm directly with the venue.
5. The system must never guarantee allergen safety.

### 12.5 Family-Friendly Validation

1. Known adult-only venues are disallowed when kid_friendly is true.
2. Category-based family suitability must be marked as inferred.
3. Unknown family suitability must not be treated as confirmed.

### 12.6 Safety Validation

1. Safety preferences must be explicitly selected by the traveler.
2. The system may favor daylight activities and less isolated routes.
3. No numeric safety score is supported by current provider information.
4. The system must not guarantee that a location is safe.

### 12.7 Medical Access Validation

1. Hospital information must be obtained through a separate search.
2. Nearby medical facilities must not be assumed without supporting data.
3. Travel-time constraints must be verified before claiming that a hospital is within the requested distance or time.
4. Missing medical-access data must be reported as unconfirmed.

### 12.8 Weather Validation

1. Indoor/outdoor preferences guide itinerary ranking.
2. Weather backups provide alternatives for outdoor activities.
3. Live forecast validation requires an integrated weather provider.
4. Forecast-related claims must not be made without current supporting data.

### 12.9 Opening Hours Validation

1. Opening hours must use structured OpeningPeriod data.
2. Activities should be checked against the venue's operating hours.
3. Unknown opening hours produce data-gap.
4. Holiday closures and exceptional hours require additional confirmation.
5. The system must not mark an activity as confirmed open without sufficient evidence.

## 13. Open Decisions and Integration Notes

**Change policy:** Align this document to working shared structures wherever they do not conflict with the Oct 9 preference direction. Only mandate changes for agreed new fields and essential validation behavior. Schema changes need team review and two PR reviewers; this draft is not itself a merged team decision.

The items below require agreement or implementation work; their presence does **not** mean the existing frontend or backend has already adopted these formats.

1. **Budget scope:** Confirm that min/max budgets apply to the entire group (the preference proposal recommends this but leaves the decision to the team).
2. **Costs:** Confirm the proposed group-total interpretation for `Activity.est_cost` and how the number of *paying* travelers is determined.
3. **Minimum-change migration:** Keep existing Trip, Activity, ValidationResult, Question, and ExecutionEvent fields where unchanged. Update the frontend and backend API boundary for the approved budget range, MustDo, and preference additions. Accept the legacy single `budget` field only through an explicitly documented temporary adapter if needed; avoid two competing internal standards. For `hours`, preserve provider raw text and normalize to `OpeningPeriod[]` only when evidence permits. Do not require all tools to rewrite their provider responses.
4. **Splurge linkage:** When converting a `MustDo` into a scheduled `Activity`, copy `splurge`; if discovery cannot identify the requested place, request clarification rather than inventing a match.
5. **Timezone:** Generate destination-local times using the destination’s timezone rules and serialize activity timestamps with the correct offset for each date.
6. **Provider limitations:** Structured opening hours may be unavailable from external tools; keep `hours: null` and produce `data-gap` rather than invent hours.
