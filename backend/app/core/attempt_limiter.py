"""Caps repeated failed attempts at something guessable, per key.

In memory, like auth_service's failed-login tracker: it only has to slow
down guessing within one running server, and forgetting on restart is
harmless. The key is whoever is asking (a signed-in user id), so one person
can't walk the code space, and one person's misses don't lock out another.
"""

from datetime import UTC, datetime, timedelta

from app.core.exceptions import RateLimitedError


class AttemptLimiter:
    def __init__(
        self,
        max_failures: int,
        window: timedelta,
        message: str,
        max_tracked: int = 10_000,
    ) -> None:
        self._max_failures = max_failures
        self._window = window
        self._message = message
        self._max_tracked = max_tracked
        self._failures: dict[str, list[datetime]] = {}

    def _recent(self, key: str, now: datetime) -> list[datetime]:
        attempts = [t for t in self._failures.get(key, []) if now - t < self._window]
        if attempts:
            self._failures[key] = attempts
        else:
            self._failures.pop(key, None)
        return attempts

    def failure_count(self, key: str, now: datetime | None = None) -> int:
        return len(self._recent(key, now or datetime.now(UTC)))

    def check(self, key: str, now: datetime | None = None) -> None:
        """Raises RateLimitedError once the key has failed too often recently."""
        reference = now or datetime.now(UTC)
        if len(self._recent(key, reference)) >= self._max_failures:
            raise RateLimitedError(self._message)

    def record_failure(self, key: str, now: datetime | None = None) -> None:
        reference = now or datetime.now(UTC)
        if len(self._failures) >= self._max_tracked and key not in self._failures:
            self._failures.clear()
        self._failures.setdefault(key, []).append(reference)

    def reset(self, key: str | None = None) -> None:
        if key is None:
            self._failures.clear()
        else:
            self._failures.pop(key, None)
