"""Resilience primitives: exponential-backoff retry and a persisted circuit breaker.

The breaker state lives in SQLite, so a failing provider stays "open" across
separate CLI invocations and cron runs instead of being rediscovered every time.
"""

from __future__ import annotations

import random
import time
from collections.abc import Callable
from datetime import UTC, datetime
from typing import TypeVar

from gtm_forge.core.state import StateStore

T = TypeVar("T")


class CircuitOpenError(RuntimeError):
    """Raised when a call is attempted while the circuit is open."""


def retry_call(
    fn: Callable[[], T],
    *,
    retries: int = 3,
    base_s: float = 0.5,
    max_s: float = 8.0,
    retryable: tuple[type[BaseException], ...] = (Exception,),
    sleeper: Callable[[float], None] = time.sleep,
) -> T:
    """Call fn with exponential backoff and full jitter. Retries come *after* the first attempt."""
    attempt = 0
    while True:
        try:
            return fn()
        except retryable:
            attempt += 1
            if attempt > retries:
                raise
            delay = min(max_s, base_s * (2 ** (attempt - 1)))
            sleeper(random.uniform(0, delay))


class CircuitBreaker:
    """Three-state breaker (closed -> open -> half-open) persisted in StateStore."""

    def __init__(self, state: StateStore, name: str, *, threshold: int = 5, cooldown_s: float = 60.0) -> None:
        self._state = state
        self.name = name
        self.threshold = threshold
        self.cooldown_s = cooldown_s

    def _row(self) -> dict[str, object]:
        return self._state.breaker_get(self.name)

    def is_open(self) -> bool:
        row = self._row()
        if row["state"] != "open":
            return False
        opened_at = row.get("opened_at")
        if not opened_at:
            return True
        elapsed = (datetime.now(UTC) - datetime.fromisoformat(str(opened_at))).total_seconds()
        if elapsed >= self.cooldown_s:
            # Half-open: allow a single trial call through.
            self._state.breaker_set(self.name, "half-open", int(str(row["failures"])), str(opened_at))
            return False
        return True

    def record_success(self) -> None:
        self._state.breaker_set(self.name, "closed", 0, None)

    def record_failure(self) -> None:
        row = self._row()
        failures = int(str(row["failures"])) + 1
        # A failed trial call while half-open reopens the circuit immediately.
        if row["state"] == "half-open" or failures >= self.threshold:
            self._state.breaker_set(self.name, "open", failures, datetime.now(UTC).isoformat())
        else:
            self._state.breaker_set(self.name, "closed", failures, None)

    def guard(self, fn: Callable[[], T]) -> T:
        """Run fn through the breaker, recording the outcome."""
        if self.is_open():
            raise CircuitOpenError(
                f"Circuit '{self.name}' is open. Retry after {self.cooldown_s}s or check the provider."
            )
        try:
            result = fn()
        except Exception:
            self.record_failure()
            raise
        self.record_success()
        return result
