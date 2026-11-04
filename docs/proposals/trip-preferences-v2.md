# Proposal: more trip preferences

**Status:** Proposal, discussed by the team on Oct 8, 2026. Not part of `docs/contracts.md` yet.
**For:** Validation Eng. (Harshita), to turn into the contract and Pydantic models.
**Also affects:** Preferences Eng. (extraction from the note), Frontend & Maps Eng. (form controls),
Tools Eng. (what data we can get), Agent Graph Eng. (planning rules).

Adding fields to `TripRequirements` changes a shared model, so it needs a message in the team
chat and two reviewers, as usual.

## 1. Summary

| # | Feature | New field(s) | In the contract today? | Can we get the data? | Suggested sprint |
|---|---|---|---|---|---|
| 0 | Budget range + splurges | `budget_min`, `budget_max`, `budget_level`, `must_do` | Replaces single `budget` | Yes, the user tells us | 2 (contract now) |
| 1 | Who is going (group size) | `travelers` | No | Yes, the user tells us | 2 |
| 2 | Family / kid-friendly | `travelers.children`, `kid_friendly` | No | Partly: place categories | 2 |
| 3 | Infant-friendly | `travelers.infants` | No | Rarely: stroller access and changing tables are mostly unknown | 2 (soft check only) |
| 4 | Energy level (calm vs adventurous) | `energy` | No | Yes: place categories | 2 |
| 5 | Dietary restrictions | `dietary` (needs a fixed list) | Yes, as free `string[]` | Partly: restaurant tags | 2 |
| 6 | Accessibility | `accessibility` (needs a fixed list) | Yes, as free `string[]` | Partly: some venues list wheelchair access | 2 |
| 7 | Safety-first | `safety_first` | No | No direct data, only indirect signals | 3 or stretch |
| 8 | Hospital nearby | `medical_access` | No | Yes: hospital search on the map | Stretch |
| 9 | Climate / weather | `indoor_outdoor` now; forecast later | No | Preference yes; forecast needs a weather provider | Preference 2; forecast P2 (US-28) |

Features 5 and 6 already exist in the contract. They only need a fixed list of allowed values.

## 2. Rules for every new field

1. **The user chooses; we never guess from who they are.** Never infer safety needs, gender,
   age or disability from a name or writing style. Only use what the user selects or writes.
2. **Never promise what we cannot check.** If we have no data (for example, no wheelchair
   information for a venue), the check returns `severity: "data-gap"` and the UI says
   "Not confirmed". It must not say "accessible" or "safe".
3. **Every field has provenance** (`explicit`, `inferred` or `default`), like the existing fields.
   "Traveling with my 2 kids" in the note gives `travelers.children = 2`, marked `explicit`.
4. **Defaults are neutral.** If the user says nothing, the plan works as it does today.

## 3. Field details

### 3.0 Budget: a range, plus splurges

Agreed direction (Oct 9): the budget is a **range** (for example $200-500), and the user can
mark one or more **splurges**, activities they want whatever they cost. This replaces the single
`budget` number in TripRequirements (follow-up F-03).

| Field | Type | Allowed values | Default |
|---|---|---|---|
| `budget_min` | number or null | 0 or more | `null` |
| `budget_max` | number or null | 0 or more, at least `budget_min` | `null` |
| `budget_strictness` | string (enum) | `strict`, `flexible`, `none` | `flexible` |
| `budget_level` | string (enum) or null | `cheap`, `moderate`, `expensive` | `null` |
| `must_do` | MustDo[] | see below | `[]` |

`budget_strictness: none` means "I don't mind about budget": no budget check runs.

**MustDo**, something the user really wants to do:

| Field | Type | Description |
|---|---|---|
| `text` | string | What the user asked for, in their words ("dinner at the Space Needle") |
| `splurge` | boolean | `true`: it does not count toward the budget |
| `place_id` | string or null | Filled in by Discovery once a real place is found |

Activity gets one new field: `splurge: boolean` (default `false`), copied from the MustDo it came from.

**From the note** (Preferences Eng.):

| User writes | Result |
|---|---|
| "$200-500" | `budget_min: 200`, `budget_max: 500` |
| "under $300" | `budget_min: null`, `budget_max: 300` |
| "cheap trip" | both `null`, `budget_level: cheap` (never turn a word into a dollar amount) |
| "budget doesn't matter" | both `null`, `budget_strictness: none` |
| "I'm on a budget, but I really want a seaplane tour, whatever it costs" | `must_do: [{text: "seaplane tour", splurge: true}]` |

**Rules** (Validation Eng.):

1. `budget_min` must not be more than `budget_max`.
2. The budget check adds up all activities **except splurges** and compares the total with
   `budget_max`: `strict` gives a `hard` failure, `flexible` gives a `soft` warning, `none` runs no check.
   Activities with an unknown cost give `data-gap`, never zero.
3. `budget_min` is never a failure. It tells ranking that nicer, pricier options are fine when
   the total is well below it.
4. Splurge activities are `priority: high`. Repair may move them but must not remove them
   without asking the user.
5. If Discovery cannot find a real place for a MustDo, ask the user (clarification loop), and
   never invent one.

**UI** (Frontend & Maps Eng.): two boxes "From $__ to $__", a "Budget doesn't matter" option,
and a field "Anything you want to do, whatever it costs?". The plan shows splurges separately:
"Trip: $430 of $500 · Plus your splurge: seaplane tour, about $250."

### 3.1 `travelers`: who is going

| Field | Type | Allowed values | Default |
|---|---|---|---|
| `travelers.adults` | integer | 1 to 10 | 1 |
| `travelers.children` | integer | 0 to 10 (ages 2-12) | 0 |
| `travelers.infants` | integer | 0 to 5 (under 2) | 0 |
| `travelers.solo` | boolean | derived: `adults == 1` and no children or infants | — |

- **Form:** three number steppers (adults, children, infants).
- **From the note:** "me and my partner" gives 2 adults; "with my 2 kids" gives 2 children.
- **Changes the budget check.** Costs from providers are usually per person. The budget
  validator must multiply per-person costs by the number of paying travelers. The team must
  also decide whether `budget` means the whole group or per person (suggest: whole group).

### 3.2 `kid_friendly`: family trips

| Field | Type | Default |
|---|---|---|
| `kid_friendly` | boolean | `true` if `children > 0` or `infants > 0`, otherwise `false` |

- **Used by:** Discovery and ranking prefer kid-friendly categories (zoos, parks, aquariums,
  museums with kids' sections) and drop adult-only places (bars, nightclubs).
- **Check (hard):** no nightlife or 21+ venues when `kid_friendly` is true.
- **Check (soft):** at most 3 activities in a row without a break.

### 3.3 Infant needs

No separate field: it comes from `travelers.infants > 0`.

- **Planning:** earlier `daily_end` (suggest 18:00), a midday break, slower pace.
- **Check (soft):** prefer step-free places, which works well with strollers.
- **Data gap:** changing tables and stroller access are rarely listed. Show "Not confirmed",
  never "Infant-friendly".

### 3.4 `energy`: calm or adventurous

| Field | Type | Allowed values | Default |
|---|---|---|---|
| `energy` | string (enum) | `calm`, `balanced`, `adventurous` | `balanced` |

This is different from `pace`. **Pace** is how many stops per day; **energy** is what kind of
stops.

- `calm`: parks, cafes, gardens, scenic views, spas.
- `adventurous`: hiking, kayaking, climbing, bike tours, nightlife.
- **Used by:** ranking only. No hard check.
- **From the note:** "relaxing trip", "low-key" give `calm`; "thrill", "outdoorsy" give `adventurous`.

### 3.5 `dietary`: fixed list

| Field | Type | Allowed values | Default |
|---|---|---|---|
| `dietary` | string[] | `vegetarian`, `vegan`, `halal`, `kosher`, `gluten_free`, `dairy_free`, `nut_allergy` | `[]` |

- **Used by:** food places only.
- **Check:** `soft` if a food stop is not tagged as matching; `data-gap` if there is no menu or
  diet information. Allergies (`nut_allergy`) are always shown as "Check with the restaurant",
  never as safe.

### 3.6 `accessibility`: fixed list

| Field | Type | Allowed values | Default |
|---|---|---|---|
| `accessibility` | string[] | `wheelchair`, `step_free`, `limited_walking`, `visual`, `hearing` | `[]` |

- `wheelchair` / `step_free`: **check (hard)** if the venue is known to be not accessible;
  `data-gap` if unknown.
- `limited_walking`: lower the walking limit between stops (suggest 10 minutes) and prefer
  transit or driving. This reuses the existing travel-time check with a smaller limit.
- `visual` / `hearing`: no data source yet; store them and show them, but no check.

### 3.7 `safety_first`: solo or late-night comfort

| Field | Type | Default |
|---|---|---|
| `safety_first` | boolean | `false` (the form can suggest it when `travelers.solo` is true, but never turns it on by itself) |

There is no reliable "safety" data from our providers. We can only use **indirect signals**,
and the UI must describe what we did, not promise safety:

- End outdoor and walking activities before dark (`daily_end` near sunset).
- Prefer busy, well-reviewed places (`popularity`, `review_count`) over isolated ones.
- Avoid long walking legs after dark; prefer transit or driving in the evening.
- Avoid isolated trails for a solo traveler.

**UI copy:** "We chose busy, well-reviewed places and kept walking to daylight hours." Do not
use the word "safe" for a place.

### 3.8 `medical_access`: hospital nearby

| Field | Type | Allowed values | Default |
|---|---|---|---|
| `medical_access.required` | boolean | | `false` |
| `medical_access.max_minutes` | integer | 5 to 60 | 20 |

- **Data:** search for hospitals and urgent care on the map (Tools Eng. to confirm in the
  S0-05 spike).
- **Check (soft):** each day has a hospital within `max_minutes` of its activities.

### 3.9 Climate and weather

| Field | Type | Allowed values | Default |
|---|---|---|---|
| `indoor_outdoor` | string (enum) | `indoor`, `outdoor`, `mix` | `mix` |
| `weather_backup` | boolean | | `true` (each outdoor activity gets an indoor backup) |

- **Now:** a preference only, used by ranking and by the Backup Agent (indoor backups for
  outdoor activities).
- **Later:** a live forecast needs a weather provider. Weather-triggered replanning is US-28, a
  P2 item in the roadmap. Keep `ChangeEvent.type` open for `weather`, as the roadmap says.

## 4. Changes to existing checks

| Existing check | Change |
|---|---|
| Budget | Compare with `budget_max`, skip splurges (3.0), and multiply per-person costs by the number of paying travelers (3.1). |
| Travel time | Smaller walking limit for `limited_walking` (3.6) and for infants (3.3). |
| Daily hours | Earlier `daily_end` for infants (3.3) and `safety_first` (3.7). |
| Avoid list | Also drop adult-only venues when `kid_friendly` is true (3.2). |

## 5. Suggested Pydantic shape

A starting point for `backend/app/models/`. Names follow the frontend style (`snake_case`).

```python
from typing import Literal
from pydantic import BaseModel, Field

class Travelers(BaseModel):
    adults: int = Field(1, ge=1, le=10)
    children: int = Field(0, ge=0, le=10)
    infants: int = Field(0, ge=0, le=5)

    @property
    def solo(self) -> bool:
        return self.adults == 1 and self.children == 0 and self.infants == 0

class MedicalAccess(BaseModel):
    required: bool = False
    max_minutes: int = Field(20, ge=5, le=60)

class MustDo(BaseModel):
    text: str = Field(min_length=1)
    splurge: bool = False
    place_id: str | None = None

Dietary = Literal["vegetarian", "vegan", "halal", "kosher", "gluten_free", "dairy_free", "nut_allergy"]
Accessibility = Literal["wheelchair", "step_free", "limited_walking", "visual", "hearing"]

# New fields added to the existing TripRequirements model (budget_min/max replace budget):
class TripRequirementsAdditions(BaseModel):
    budget_min: float | None = Field(None, ge=0)
    budget_max: float | None = Field(None, ge=0)
    budget_strictness: Literal["strict", "flexible", "none"] = "flexible"
    budget_level: Literal["cheap", "moderate", "expensive"] | None = None
    must_do: list[MustDo] = []
    travelers: Travelers = Travelers()
    kid_friendly: bool = False          # default derived from travelers
    energy: Literal["calm", "balanced", "adventurous"] = "balanced"
    dietary: list[Dietary] = []
    accessibility: list[Accessibility] = []
    safety_first: bool = False
    medical_access: MedicalAccess = MedicalAccess()
    indoor_outdoor: Literal["indoor", "outdoor", "mix"] = "mix"
    weather_backup: bool = True
```

## 6. Who does what

| Person | Task |
|---|---|
| Harshita | Agree the field names and allowed values in chat, add them to `contracts.md` and the models, and update the budget and travel-time checks (section 4). |
| Kaleb | Teach the "Tell us more" reader to pick up these fields from the note, and add test sentences for them (for example "solo trip, vegetarian, traveling with my 2-year-old"). |
| Yahya | Add the form controls: traveler steppers, energy choice, diet and accessibility chips, safety and hospital toggles, indoor/outdoor choice. Use the copy rules in section 2. |
| Nitin | In the S0-05 spike, check which of these the providers actually return: wheelchair access, kid-friendly tags, diet tags, hospital search. |
| Sathwika | Planning rules: earlier day end, midday break, indoor backups. |

## 7. Open questions

1. Is `budget` for the whole group or per person? (Suggest: whole group.)
2. Which features go into Sprint 2, and which wait? (Suggest: 1-6 and the `indoor_outdoor`
   preference in Sprint 2; 7 and 8 only if Sprint 2's goal is met.)
3. Does the form show all of these, or hide some under "More options" so it stays short?
