"""Repair Agent (A6), deterministic first version: fix only what broke.

Given a plan whose checks found hard problems, patch just the activities that
cause them (FR-14 "minimal change"). Everything else keeps its place, time and
id. Done and locked activities are never touched (CLAUDE.md).

For each broken activity, in this order (FR-42):
1. its stored backups, then 2. unused places from the search, nearest first,
   with the same purpose, that pass the checks in the same time slot;
3. if none fits, the activity is removed and the reason is recorded.

Problems handled: closed at that time, avoid-list match, overlap, not enough
travel time between stops, and over budget. Soft problems are not repaired;
they are shown to the user (docs/03 section 5.3).
"""

from datetime import datetime, time, timedelta
from typing import Any

from app.tools.base import LatLng
from app.tools.mock_places import distance_km
from app.validation.avoid import check_avoid_list
from app.validation.budget import check_budget
from app.validation.opening_hours import check_opening_hours
from app.validation.overlap import check_overlap
from app.validation.travel_time import check_travel_time

PROTECTED_STATUSES = {"done", "locked", "cancelled"}
GAP_AFTER_MOVE = timedelta(minutes=15)


def hard_failures(checks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [c for c in checks if not c["passed"] and c["severity"] == "hard"]


def violation_score(checks: list[dict[str, Any]]) -> int:
    """docs/03 5.3: 100 x hard violations + soft penalty. Lower is better."""
    hard = sum(1 for c in checks if not c["passed"] and c["severity"] == "hard")
    soft = sum(1 for c in checks if not c["passed"] and c["severity"] == "soft")
    return 100 * hard + soft


def repair_itinerary(
    trip: dict[str, Any], itinerary: dict[str, Any], places: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Patch the itinerary in place. Returns the list of changes made (empty if none)."""
    repair = _Repair(trip, itinerary, places)
    repair.fix_closed_places()
    repair.fix_avoid_list()
    repair.fix_overlaps()
    repair.fix_travel_time()
    repair.fix_budget()
    return repair.changes


class _Repair:
    def __init__(self, trip, itinerary, places):
        self.trip = trip
        self.itinerary = itinerary
        self.places = places
        self.mode = trip.get("mode", "walking")
        self.trip_id = str(itinerary.get("trip_id", "unknown"))
        self.version = itinerary.get("version", 0)
        self.changes: list[dict[str, Any]] = []
        # Places that already failed are never tried again (stops A -> B -> A swaps).
        self.rejected_place_ids = {
            change["old_place_id"] for change in itinerary.get("repairs", [])
        }

    # --- the five problems -------------------------------------------------

    def fix_closed_places(self) -> None:
        for day, activity in self._editable():
            result = self._hours_check(activity, activity["place"])
            if not result.passed and result.severity == "hard":
                self._replace_or_remove(day, activity, "opening_hours", "It is closed then.")

    def fix_avoid_list(self) -> None:
        avoid = self.trip.get("avoid", [])
        for day, activity in self._editable():
            result = check_avoid_list([activity], avoid, self.trip_id, self.version)
            if not result.passed and result.severity == "hard":
                self._replace_or_remove(day, activity, "avoid", "It matches your avoid list.")

    def fix_overlaps(self) -> None:
        for day in self.itinerary.get("days", []):
            for first, second in _pairs(day):
                result = check_overlap([first, second], self.trip_id, self.version)
                if result.passed or second.get("status") in PROTECTED_STATUSES:
                    continue
                self._move_after(day, first, second)

    def fix_travel_time(self) -> None:
        for day in self.itinerary.get("days", []):
            for first, second in _pairs(day):
                if self._travel_is_hard([first, second]):
                    if second.get("status") not in PROTECTED_STATUSES:
                        self._replace_or_remove(
                            day, second, "travel_time", "There is not enough time to get there."
                        )
                    elif first.get("status") not in PROTECTED_STATUSES:
                        self._replace_or_remove(
                            day, first, "travel_time", "There is not enough time to get there."
                        )

    def fix_budget(self) -> None:
        budget = self.trip.get("budget", self.trip.get("budget_max"))
        if budget is None:
            return
        # Each round changes one activity, so the loop ends after at most that many rounds.
        for _ in range(len(self._active())):
            result = check_budget(
                self._active(),
                budget,
                self.trip.get("budget_strictness", "strict"),
                self.trip_id,
                self.version,
            )
            if result.passed or result.severity != "hard":
                return
            priced = [
                (day, activity)
                for day, activity in self._editable()
                if not activity.get("splurge") and (activity.get("est_cost") or 0) > 0
            ]
            if not priced:
                return
            day, activity = max(priced, key=lambda item: item[1]["est_cost"])
            self._replace_or_remove(
                day,
                activity,
                "budget",
                "The plan was over budget.",
                cheaper_than=activity["est_cost"],
            )

    # --- replace, remove, move ---------------------------------------------

    def _replace_or_remove(self, day, activity, rule, reason, cheaper_than=None) -> None:
        replacement = self._find_replacement(day, activity, cheaper_than)
        old_place = activity["place"]
        self.rejected_place_ids.add(old_place.get("id"))
        if replacement is None:
            day["activities"].remove(activity)
            self._record(activity, "removed", rule, reason, old_place, None)
            return
        activity.update(
            {
                "place_id": replacement["id"],
                "place": replacement,
                "est_cost": replacement.get("est_cost_low"),
                "cost_basis": replacement.get("cost_basis", "unknown"),
                "change_type": "replaced",
                "reason": f"Replaced {old_place.get('name')}: {reason}",
                "backups": [],  # the old place's backups no longer apply
            }
        )
        self._record(activity, "replaced", rule, reason, old_place, replacement)

    def _move_after(self, day, first, second) -> None:
        start = datetime.fromisoformat(second["start"])
        length = datetime.fromisoformat(second["end"]) - start
        new_start = datetime.fromisoformat(first["end"]) + GAP_AFTER_MOVE
        new_end = new_start + length
        if new_end.timetz().replace(tzinfo=None) > self._daily_end():
            day["activities"].remove(second)
            self._record(
                second, "removed", "overlap", "It no longer fits in the day.", second["place"], None
            )
            return
        second["start"], second["end"] = new_start.isoformat(), new_end.isoformat()
        second["change_type"] = "moved"
        second["reason"] = f"Moved to {new_start:%H:%M} so it does not overlap."
        self._record(second, "moved", "overlap", "It overlapped the stop before.", None, None)

    def _find_replacement(self, day, activity, cheaper_than=None) -> dict[str, Any] | None:
        purpose = {str(tag).lower() for tag in activity.get("purpose_tags") or []}
        original = activity["place"]
        used = {a["place"].get("id") for _, a in self._all()}
        stored = [b.get("place") for b in activity.get("backups") or [] if b.get("place")]
        pool = sorted(self.places, key=lambda place: _distance(original, place))

        for candidate in [*stored, *pool]:
            place_id = candidate.get("id")
            if not place_id or place_id in used or place_id in self.rejected_place_ids:
                continue
            types = {str(t).lower() for t in candidate.get("experience_types") or []}
            if purpose and not purpose & types:
                continue  # keep the activity's purpose (FR-41/42)
            cost = candidate.get("est_cost_low")
            if cheaper_than is not None and (cost is None or cost >= cheaper_than):
                continue
            if self._fits(day, activity, candidate):
                return candidate
        return None

    def _fits(self, day, activity, candidate) -> bool:
        """Would the candidate pass the hard checks in this activity's time slot?"""
        trial = {**activity, "place_id": candidate["id"], "place": candidate}
        hours = self._hours_check(trial, candidate)
        if not hours.passed and hours.severity == "hard":
            return False
        avoid = check_avoid_list([trial], self.trip.get("avoid", []), self.trip_id, self.version)
        if not avoid.passed and avoid.severity == "hard":
            return False
        stops = [a for a in _sorted(day) if a.get("status") != "cancelled"]
        index = next(i for i, a in enumerate(stops) if a is activity)
        path = [*stops[max(index - 1, 0) : index], trial, *stops[index + 1 : index + 2]]
        return not self._travel_is_hard(path)

    # --- helpers -----------------------------------------------------------

    def _hours_check(self, activity, place):
        hours = place.get("hours")
        return check_opening_hours(
            activity["start"],
            activity["end"],
            hours if isinstance(hours, list) else None,
            trip_id=self.trip_id,
            version=self.version,
            activity_id=activity.get("id"),
        )

    def _travel_is_hard(self, stops) -> bool:
        if len(stops) < 2:
            return False
        result = check_travel_time(
            stops, self.mode, self.trip.get("max_travel_min"), self.trip_id, self.version
        )
        return not result.passed and result.severity == "hard"

    def _daily_end(self) -> time:
        try:
            return time.fromisoformat(self.trip.get("daily_end", "20:00"))
        except ValueError:
            return time(20, 0)

    def _all(self):
        return [(day, a) for day in self.itinerary.get("days", []) for a in day["activities"]]

    def _active(self):
        return [a for _, a in self._all() if a.get("status") != "cancelled"]

    def _editable(self):
        """Activities the repair may change (a copy, so removing while looping is safe)."""
        return [(day, a) for day, a in self._all() if a.get("status") not in PROTECTED_STATUSES]

    def _record(self, activity, change, rule, reason, old_place, new_place) -> None:
        self.changes.append(
            {
                "activity_id": activity.get("id"),
                "day": activity.get("day"),
                "change": change,
                "rule": rule,
                "reason": reason,
                "old_place_id": (old_place or activity["place"]).get("id"),
                "old_place": (old_place or activity["place"]).get("name"),
                "new_place": new_place.get("name") if new_place else None,
            }
        )


def _sorted(day) -> list[dict[str, Any]]:
    return sorted(day["activities"], key=lambda a: datetime.fromisoformat(a["start"]))


def _pairs(day):
    """Consecutive stops in one day, re-read each time so changes are seen."""
    stops = [a for a in _sorted(day) if a.get("status") != "cancelled"]
    return list(zip(stops, stops[1:]))


def _distance(a: dict[str, Any], b: dict[str, Any]) -> float:
    if any(place.get(key) is None for place in (a, b) for key in ("lat", "lng")):
        return float("inf")
    return distance_km(LatLng(lat=a["lat"], lng=a["lng"]), b["lat"], b["lng"])
