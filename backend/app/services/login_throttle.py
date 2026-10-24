"""In-memory throttle for failed logins (US-01).

Kept in memory on purpose: fine for a single-process MVP. It resets when the backend
restarts (noted in the Project Report).
"""

from __future__ import annotations

import math
import threading
import time
from collections import deque
from typing import Callable


class LoginThrottle:
    """Block a key (the lower-cased email) after too many failures inside a time window."""

    def __init__(
        self,
        max_failures: int,
        window_seconds: float,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        """Set the limits. ``clock`` is injectable so tests do not need to sleep."""
        self._max_failures = max_failures
        self._window_seconds = window_seconds
        self._clock = clock
        self._failures: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def _recent_failures(self, key: str) -> deque[float]:
        """Drop failures older than the window; remove the key when none are left."""
        failures = self._failures.get(key)
        if failures is None:
            return deque()
        cutoff = self._clock() - self._window_seconds
        while failures and failures[0] <= cutoff:
            failures.popleft()
        if not failures:
            del self._failures[key]  # keeps memory bounded
        return failures

    def is_blocked(self, key: str) -> bool:
        """Return True when the key has reached the failure limit inside the window."""
        with self._lock:
            return len(self._recent_failures(key)) >= self._max_failures

    def retry_after_seconds(self, key: str) -> int:
        """Return the whole seconds until the oldest counted failure expires (min 1)."""
        with self._lock:
            failures = self._recent_failures(key)
            if not failures:
                return 0
            remaining = failures[0] + self._window_seconds - self._clock()
            return max(1, math.ceil(remaining))

    def record_failure(self, key: str) -> None:
        """Count one failed attempt for the key."""
        with self._lock:
            self._recent_failures(key)
            self._failures.setdefault(key, deque()).append(self._clock())

    def reset(self, key: str) -> None:
        """Forget the failures for the key after a successful login."""
        with self._lock:
            self._failures.pop(key, None)
