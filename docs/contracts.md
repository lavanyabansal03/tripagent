# Data Contracts

Shapes for Trip, Preferences, Place, Activity, CheckResult. Changes to these
require a message in the team chat and two reviewers.

## Field provenance (proposed, F-01)

Travellers must always be able to tell where a value came from, so the UI shows a
label per field. The preference provenance enum is being widened from
`explicit | inferred | default` to:

| Value | Meaning | UI label |
|-------|---------|----------|
| `from_text` | The traveller wrote it in "Tell us more" | From your note |
| `from_form` | The traveller picked or typed it in the form | You chose this |
| `inferred` | We guessed it from another signal (e.g. "locals enjoy" → 80% local) | We guessed this from your note. Tap to change. |
| `default` | We assumed it; the traveller never chose it | We assumed this. Tap to change. |

- Applies to `TripRequirements.provenance` and `field_provenance` on preferences
  (`docs/03_architecture_agent_design.md`, section 3.1).
- Implemented on the frontend (types, demo engine, "Here's what we understood").
- **The backend `TripRequirements.provenance` literal still lists
  `explicit | inferred | default`** (`backend/app/api/trips.py`). It should be
  updated to match when the provenance work is reviewed so live and demo modes
  agree. Until then the UI maps unknown values to `from_form`.
- Provider data on `Place` uses a separate `FieldProvenance`
  (`explicit | inferred | unknown`); it records whether a provider field was
  present, not where a user preference came from.
