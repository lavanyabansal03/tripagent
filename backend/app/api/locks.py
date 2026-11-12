"""One lock per trip, shared by planning (POST /plan) and changes (POST /changes etc.).

Only one of them may work on a trip at a time; otherwise two requests could both save
itinerary version N and the second would crash. The locks live in this process, which
is right for one server (Render's free plan runs one).
"""

import threading

_locks: dict[str, threading.Lock] = {}
_locks_guard = threading.Lock()


def lock_for(trip_id: str) -> threading.Lock:
    """The lock for this trip (created on first use)."""
    with _locks_guard:
        return _locks.setdefault(trip_id, threading.Lock())
