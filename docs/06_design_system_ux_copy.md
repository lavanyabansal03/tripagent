# TripAgent: Design System & UX Copy Guide

_Tokens, components, states, accessibility, voice and screen copy_

| Field | Value |
|---|---|
| Owner role | Design (Frontend & Maps Eng. leads; Preferences Eng. co-owns copy) |
| Team | Product Owner / Engineering Manager; five engineers in role areas: Preferences, Validation, Agent Graph, Tools, Frontend & Maps |
| Version | 2.3 (October 5, 2026) |
| Status | Living document, updated each sprint |
| Method | Design system (tokens, components, patterns) + UX copy principles |

## 1. Design Principles

1. **Show the plan, then the reasoning.** The itinerary and map come first; the trace and reasons are one click away.
2. **Never hide uncertainty.** Assumed preferences, unknown costs, missing hours and stale events are always labelled.
3. **Changes are visible and reversible.** Every adjustment shows what changed, what stayed, and offers undo.
4. **Meaning never depends on colour alone.** Status and change types always pair colour with an icon and a word.
5. **Consistency over creativity.** Use tokens and existing components before inventing new ones.

## 2. Design Tokens

Tokens are defined once as CSS custom properties in `frontend/src/styles/tokens.css` and mirrored in a TypeScript object for the map layers. Components must not hard-code colours, spacing or font sizes.

### 2.1 Colour

| Token | Light | Dark | Use |
|---|---|---|---|
| --color-bg | #FFFFFF | #0F1419 | Page background |
| --color-surface | #F6F8FA | #161B22 | Cards, panels |
| --color-text | #1F2A37 | #E6EDF3 | Body text |
| --color-text-muted | #5B6675 | #9AA4AF | Secondary text, timestamps |
| --color-border | #D0D7DE | #30363D | Dividers, inputs |
| --color-brand | #0F6E6E | #3FB8B0 | Primary actions, links, active route |
| --color-success | #1A7F37 | #3FB950 | Validation pass |
| --color-warning | #9A6700 | #D29922 | Soft issues, stale data, assumptions |
| --color-danger | #CF222E | #F85149 | Hard violations, errors |
| --color-info | #0969DA | #58A6FF | Neutral notices, agent activity |

#### Change-state tokens (used in lists and on the map)

| Token | Colour | Icon | Label | Map style |
|---|---|---|---|---|
| --change-added | success | plus | Added | Solid green outline marker |
| --change-replaced | info | swap arrows | Replaced | Blue marker with swap badge; new leg dashed |
| --change-moved | warning | clock arrow | Moved | Amber marker with time badge |
| --change-removed | danger | minus | Removed | Grey hollow marker, struck label |
| --change-preserved | text-muted | check | Kept | Unchanged marker and leg |

#### Experience-category tokens (map pins and chips)

Eight categories share a colour-blind-safe palette; each also has an icon so pins are distinguishable in greyscale: food, cafe, nature, culture, shopping, nightlife, event, landmark. Local favourites add a small "local" badge; tourist landmarks use the landmark icon.

### 2.2 Typography, spacing, shape, motion

| Group | Tokens |
|---|---|
| Font family | --font-sans: Inter, system-ui, sans-serif; --font-mono: JetBrains Mono, Consolas, monospace (trace panel) |
| Type scale | --text-xs 12px, --text-sm 14px, --text-md 16px (body), --text-lg 20px, --text-xl 24px, --text-2xl 32px; line-height 1.5 body, 1.25 headings |
| Weights | 400 regular, 500 medium (labels), 600 semibold (headings) |
| Spacing (4px base) | --space-1 4, --space-2 8, --space-3 12, --space-4 16, --space-6 24, --space-8 32, --space-12 48 |
| Radius | --radius-sm 4px (chips), --radius-md 8px (cards, inputs), --radius-lg 16px (dialogs) |
| Elevation | --shadow-1 cards, --shadow-2 popovers, --shadow-3 dialogs |
| Motion | --dur-fast 120ms, --dur-base 200ms, --dur-slow 320ms; ease-out; respect prefers-reduced-motion |
| Breakpoints | sm 640, md 768, lg 1024, xl 1280. Below lg the map collapses into a tab. |

## 3. Layout

```
Desktop (>= 1024px)
+--------------------------------------------------------------------------+
| TripAgent   Seattle, Oct 12-14   [Adjust trip]   [Trace]      v3  Undo   |
+----------------------------+---------------------------------------------+
| Day tabs: 1 | 2 | 3         |                                             |
| Validation summary          |               MAP                           |
| ActivityCard                |   pins by category, route legs with times   |
|   -- leg: 12 min transit -- |   changed legs highlighted after a replan   |
| ActivityCard                |                                             |
| ...                         |                                             |
+----------------------------+---------------------------------------------+
Mobile: header + tabs [Plan | Map | Trace]; Adjust trip is a bottom sheet.
```

## 4. Components

### 4.1 Inventory

| Component | Purpose | Key variants / states |
|---|---|---|
| TripForm | Destination, dates, budget, mode, pace, travel limit | default, validating, error, submitting |
| TellUsMoreField | Large free-text box with example prompt and counter | empty, typing, over-limit |
| PreferenceChips | Extracted preferences with provenance | from-text, assumed, edited; removable |
| TouristLocalSlider | Sets tourist vs local balance | 0-100%, labelled ends |
| ClarifyCard | Up to 3 questions from the agent | unanswered, answered, skipped |
| RunProgress | Shows agent steps while planning | running, done, failed, degraded |
| DayTabs | Switch days | default, active, has-issue badge |
| ActivityCard | One scheduled activity | default, locked, done, has-warning, changed (by change type) |
| LegRow | Travel between activities | ok, over-limit, recalculated |
| BackupDrawer | Backups inside ActivityCard | collapsed, expanded, none-found, swapping |
| FreshnessLabel | Retrieved date on time-sensitive data | fresh, stale (with refresh) |
| ValidationBadge | Pass / warning / violation | pass, soft, hard, unknown-data |
| AdjustTripDialog | Submit a change by text or quick actions | idle, interpreting, needs-clarification, running |
| ChangeSummaryPanel | Diff after replan | grouped by change type; undo; approval mode (P1) |
| MapView | Pins, legs, diff layer, legend | plan, diff, focus-activity |
| AgentTrace | Timeline of nodes, tools, loop iterations | collapsed, expanded, filtered |
| InfeasibleNotice | Explains why no plan fits | with suggested relaxations as buttons |

### 4.2 Component spec: ActivityCard

The card for one scheduled activity. Most user attention lands here, so it carries time, place, cost, reason and backups.

| Property | Type | Default | Description |
|---|---|---|---|
| activity | Activity | required | Place, times, cost, purpose tags, status |
| changeType | 'added' \| 'replaced' \| 'moved' \| 'removed' \| 'kept' \| null | null | Shown after a replan |
| warnings | ValidationResult[] | [] | Soft and data-gap issues for this activity |
| backups | Backup[] | [] | Rendered in BackupDrawer |
| onSwap | (backupId) => void | none | Manual swap; disabled when locked |
| onLockToggle | () => void | none | Lock keeps the activity during replans |

| State | Visual | Behaviour |
|---|---|---|
| Default | Surface card, category icon, time, name, cost, one-line reason | Click focuses map pin |
| Locked | Lock icon + "Locked" text | Excluded from repair; swap disabled |
| Done | Muted text, check icon, "Done" | Read-only |
| Has warning | Amber left border + warning text | Warning expands on click |
| Changed | Change-state icon, label and colour; "Why?" link | Why opens the reason |
| Swapping | Inline spinner "Checking this option..." | Other actions disabled |

#### Accessibility

- Role: `article` with `aria-labelledby` on the activity name.
- Keyboard: Tab to card, Enter to expand backups, L to lock (with visible shortcut hint).
- Screen reader: "Replaced. Pike Place Market, 11:00 to 12:30, about $15. Replaced because the budget changed."
- Change state announced through a polite live region after replans.

| Do | Don't |
|---|---|
| Show the reason for the activity in one line. | Show long AI-generated paragraphs on the card. |
| Show "Cost unknown" when no data exists. | Display $0 for unknown costs. |
| Pair every colour with an icon and word. | Use red/green alone for removed/added. |

### 4.3 Component spec: ChangeSummaryPanel

Appears after every replan. Groups changes in a fixed order: Replaced, Moved, Added, Removed, Kept (collapsed count). Top line states the trigger in the user's terms; each item has a one-sentence reason from the Explainer. Actions: **Undo changes** and **Close**. In approval mode (P1) the actions are **Apply changes** and **Keep my plan**, and the map shows the proposal in the diff layer.

### 4.4 Component spec: MapView legend and diff layer

- Legend always visible on desktop; collapsible chip on mobile.
- Legs show minutes on hover or focus, and in the LegRow list for non-pointer users.
- After a replan, changed legs animate once (skipped with reduced motion) and keep a dashed style until the user closes the summary.
- A "Show whole trip / Show this day" toggle keeps clustered days readable.

## 5. UX Copy Guide

### 5.1 Voice and tone

TripAgent sounds like a well-organized friend who knows the city: clear, warm, brief, never robotic, never salesy. It admits uncertainty plainly. Tone shifts by moment: calm and specific for problems, lightly upbeat for success, neutral for status.

### 5.2 Terminology (use exactly these words)

| Say | Not | Meaning |
|---|---|---|
| Trip | Journey, project | The whole thing the user creates |
| Plan / itinerary | Schedule, agenda | Days and activities |
| Activity | Item, stop, event | One scheduled thing (an Event is a type of activity) |
| Backup | Alternative, plan B option | A ready replacement for an activity |
| Adjust trip | Replan, regenerate, edit | The user action to change something |
| Kept | Preserved, unchanged | Activities not touched by an adjustment |
| Checked | Retrieved, fetched | When time-sensitive info was last verified |
| Travel time | Commute, transit duration | Minutes between activities for the chosen mode |

Internal terms (replan, validator, node, agent) appear only in the Trace panel.

### 5.3 Key screens

#### Trip setup

| Element | Copy |
|---|---|
| Page title | Plan a trip |
| Free-text label | Tell us more about your trip |
| Free-text placeholder | For example: First time in Seattle. I love coffee, bookstores and photography, want places locals enjoy, I'm vegetarian, and I'd rather not travel more than 30 minutes between stops. |
| Helper text | The more you share, the more personal your plan. You can edit everything we pick up. |
| Slider ends | Famous sights  -  Local favourites |
| Primary CTA | Build my plan |

#### Extracted preferences

| Element | Copy |
|---|---|
| Section title | Here's what we understood |
| Chip provenance (from text) | From your note |
| Chip provenance (assumed) | We assumed this. Tap to change. |
| Clarification intro | A quick question before we plan |
| Contradiction example | You picked driving, but your note says you won't have a car. How will you get around? |

#### Planning in progress (RunProgress)

Step messages set expectations and map to real graph nodes: "Reading your trip details", "Finding places that match you", "Checking travel times", "Arranging your days", "Preparing backups", "Double-checking hours and budget". If a step is slow: "Still working. Checking travel times takes longer for bigger trips."

#### Itinerary and activities

| Element | Copy |
|---|---|
| Validation pass | Everything fits: hours, travel times and budget. |
| Soft warning | Day 2 has three cafés in a row. Want more variety?  [Mix it up] |
| Unknown cost | Cost unknown |
| Estimated cost | About $15-35  (tooltip: Estimated from the price level. Actual prices may vary.) |
| Local signal badges | Local pick  \|  Popular sight  \|  Hidden gem  (tooltip: Based on ratings and review patterns, not an official label.) |
| Attribution | Powered by Foursquare  (shown in place details and map attribution) |
| Unknown hours | Hours not listed. Check before you go. |
| Fresh label | Checked today, 9:40 AM |
| Stale label | Checked 3 days ago. Details may have changed.  [Check again] |
| Backups header | Backups (same vibe) |
| No backups (empty state) | No backup found nearby yet. We'll search again if this falls through. |
| Lock tooltip | Keep this activity no matter what changes. |

#### Adjust trip

| Element | Copy |
|---|---|
| Dialog title | What changed? |
| Placeholder | For example: I'm running 90 minutes late, or my budget is now $300. |
| Quick actions | Running late  \|  Lower budget  \|  Switch to walking  \|  Skip something |
| CTA | Adjust my trip |
| Working | Adjusting only what's affected... |

#### Change summary

| Element | Copy template |
|---|---|
| Title | Your trip is updated |
| Trigger line | Because {trigger in user words}, we changed {n} activities and kept {m}. |
| Replaced | Replaced {old} with {new}: {reason}. (for example "Replaced the cooking class with Pike Place food walk: similar food and culture, $25 cheaper.") |
| Moved | Moved {activity} to {time}: {reason}. |
| Removed | Removed {activity}: {reason}. |
| Kept | Kept {m} activities as planned. |
| Actions | Undo changes  \|  Looks good |
| Approval mode (P1) | Apply changes  \|  Keep my plan |

#### Errors and infeasibility

| Situation | Copy (what happened + why + how to fix) |
|---|---|
| No feasible plan | We couldn't fit this trip. Your $150 budget is below the known cost of any full day in {city}. Try raising the budget, shortening the trip, or allowing free activities only.  [Allow free-only days] [Change budget] |
| Travel limit too strict | Some days can't stay under 15 minutes between stops. Allow up to 25 minutes, or plan fewer areas per day? |
| Provider down (degraded) | Live travel times are unavailable right now, so we used recent estimates. We'll refresh them when the service is back. |
| Unknown failure | Something went wrong while planning. Your trip is saved. Try again in a moment.  [Try again] |
| Change not understood | We didn't catch what changed. Try something like "I'm 1 hour late" or "skip museums". |

### 5.4 Localization notes

- Store all strings in `frontend/src/copy/en.json`; no inline text in components.
- Use ICU plural rules for counts ("1 activity" / "3 activities").
- Format money, time and dates with Intl APIs from the trip locale; never concatenate currency symbols.
- Allow 30% text expansion in buttons and chips.

## 6. Design System Governance

- New component? Write a short "extend" proposal (problem, existing components considered, props, states, tokens, accessibility) and get one review from Frontend & Maps Eng. plus one engineer.
- Sprint 4 includes a design-system audit: hard-coded colours or spacing found in code become cleanup tasks.
- Every component documents: variants, states, props, accessibility, do and don't.
