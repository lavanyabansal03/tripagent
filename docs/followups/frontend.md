# Frontend follow-ups

Found while running Yahya's Svelte branch (`yahya-azeem/frontend-svelte`, commit `d62bc87`)
on Oct 8, 2026. Paths are relative to `frontend/src/`.

| # | Change | When | Owner | Status |
|---|---|---|---|---|
| F-01 | Fix the "where it came from" labels on *Here's what we understood* | Now (Sprint 1 demo) | Frontend + Preferences | Open |
| F-02 | Add "Add your own" to the **Avoid** list | Now | Frontend | Open |
| F-03 | Budget as a range (min to max), not one number | Sprint 2 | Frontend + Validation | Open |
| F-04 | More "Getting around" options | Sprint 2, after the Mapbox spike | Frontend + Tools | Open |
| F-05 | Linter: keep oxlint, drop the ESLint plan | Now (docs only) | Frontend | Open, needs team OK |
| F-06 | Map labels overlap when legs are close ("12 min" drawn twice) | Sprint 2 (US-07) | Frontend & Maps | Open |

---

## F-01 Fix the provenance labels

The Sprint 1 demo is exactly this screen (US-17), and the design rule is "never hide
uncertainty", so wrong labels here are a demo-day problem.

**What we saw** with destination "Seattle" and the Maya note:

| Chip | Label shown | Correct label | Why it is wrong |
|---|---|---|---|
| food | From your note | *remove the chip* | The note never mentions food. The keyword `eat` matches inside "S**eat**tle". |
| transit | From your note | You chose this | Picked in the form, not written in the note. |
| moderate | From your note | We assumed this. Tap to change. | Form default the user never touched. |
| 30 min travel | We guessed this from your note | From your note | The note literally says "30 minutes". |
| coffee, bookstores, photography | From your note | From your note | Correct. |
| *(missing)* local favourites 80% | — | We guessed this from your note | Inferred from "places locals enjoy" but not shown. |
| *(missing)* avoid list, budget | — | Show them | The screen leaves them out entirely. |

**Root causes**

1. `api/mock/engine.ts` `extractFreeText()` matches keywords with `includes()`, so it finds
   words inside other words. Match whole words: `new RegExp(`\\b${w}`)`.
2. Provenance has only `explicit | inferred | default` (`types/index.ts`), and `createTrip()`
   marks every form field `explicit`. `PreferenceChips.svelte` shows `explicit` as
   "From your note", so form choices are mislabelled.
3. A number the user typed (`30 minutes`) is marked `inferred`; it should be `explicit`.
   `inferred` is for real guesses (e.g. "locals enjoy" → 80% local).
4. Untouched form defaults (pace, mode, slider) are marked `explicit`; they should be `default`.
   The form needs to remember which fields the user actually changed.
5. `pages/UnderstoodPage.svelte` builds chips only for interests, mode, pace, travel and
   dietary.

**Fix**

- Split the provenance values so the UI can tell them apart:
  `from_text | from_form | inferred | default` (rename to taste).
  **This changes the shared contract** (`docs/03` section 3.1 `field_provenance`, and
  `docs/contracts.md` once written), so agree it with Validation and get two reviews.
- Label copy (add the new line to `docs/06_design_system_ux_copy.md` and `copy/en.json`):

  | Value | Label |
  |---|---|
  | `from_text` | From your note |
  | `from_form` | You chose this |
  | `inferred` | We guessed this from your note. Tap to change. |
  | `default` | We assumed this. Tap to change. |

- Add chips for avoid, budget and the tourist/local ratio.
- Add a test using the Maya note with destination "Seattle" that asserts `food` is **not**
  extracted.
- The real extractor will be Gemini (US-17), but DEMO_MODE uses this mock on demo day,
  so the mock must be right too.

## F-02 "Add your own" for Avoid

Interests has an "Add your own" field and button; Avoid only offers fixed chips
(culture, nightlife, shopping, food). Reuse the same input in `components/TripForm.svelte`.
The backend must treat a free-text avoid value the same way as a free-text interest.

## F-03 Budget as a range

Today: one number plus "Keep me strictly within budget". Proposed: min and max (or
"total" vs "per day"). This changes `budget` in the contract and the budget validator
(V-01/V-02), and ties in with the cost-range table in US-18. Do it in Sprint 2 together
with those stories, not as a UI-only change.

## F-04 More ways to get around

Today: Walking, Transit, Driving, Cycling. Candidates: taxi/rideshare, ferry, "mix".
Every option needs real travel times from the routing provider. **Check first:** Mapbox
Directions has walking, cycling and driving profiles but no public-transit routing, so
even the existing "Transit" option needs a plan. Decide in the S0-05 spike, then build with
the travel matrix story (US-23/24).

## F-05 Linter

The tech-stack doc plans ESLint + `eslint-plugin-svelte`, but the Svelte app already uses
oxlint and passes. Proposal: keep oxlint for JS/TS and rely on `svelte-check` (already set
up, 0 errors) for Svelte templates and accessibility warnings. Update
`constitution/03-tech-stack/tech-stack.md` and open question B2 if the team agrees.

## F-06 Map label overlap

Without a Mapbox token the fallback map draws leg labels on top of each other when stops are
close. Check again with a real token before fixing.
