"""Retry-with-jitter and the SQLite-persisted circuit breaker."""

from __future__ import annotations

import pytest

from gtm_forge.core.breaker import CircuitBreaker, CircuitOpenError, retry_call


def _no_sleep(_seconds: float) -> None:
    return None


def test_retry_returns_on_first_success() -> None:
    calls = 0

    def fn() -> str:
        nonlocal calls
        calls += 1
        return "ok"

    assert retry_call(fn, retries=3, sleeper=_no_sleep) == "ok"
    assert calls == 1


def test_retry_succeeds_after_transient_failures() -> None:
    attempts = 0

    def flaky() -> str:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise ConnectionError("blip")
        return "recovered"

    assert retry_call(flaky, retries=3, sleeper=_no_sleep) == "recovered"
    assert attempts == 3


def test_retry_gives_up_after_exhausting_attempts() -> None:
    attempts = 0

    def always_fails() -> None:
        nonlocal attempts
        attempts += 1
        raise TimeoutError("nope")

    with pytest.raises(TimeoutError):
        retry_call(always_fails, retries=2, sleeper=_no_sleep)
    assert attempts == 3  # first attempt + 2 retries


def test_non_retryable_exception_propagates_immediately() -> None:
    def fn() -> None:
        raise ValueError("not retryable here")

    with pytest.raises(ValueError):
        retry_call(fn, retries=5, retryable=(KeyError,), sleeper=_no_sleep)


def test_breaker_opens_at_threshold_and_blocks_calls(state) -> None:
    breaker = CircuitBreaker(state, "test-open", threshold=3, cooldown_s=600.0)
    for _ in range(3):
        breaker.record_failure()
    assert breaker.is_open() is True
    with pytest.raises(CircuitOpenError):
        breaker.guard(lambda: "should not run")


def test_breaker_resets_on_success(state) -> None:
    breaker = CircuitBreaker(state, "test-reset", threshold=2, cooldown_s=600.0)
    breaker.record_failure()
    breaker.record_success()
    breaker.record_failure()  # 1 < threshold: still closed
    assert breaker.is_open() is False
    assert breaker.guard(lambda: "fine") == "fine"


def test_breaker_half_open_after_cooldown_and_recovers(state) -> None:
    breaker = CircuitBreaker(state, "test-half-open", threshold=1, cooldown_s=0.0)
    breaker.record_failure()  # opens immediately (threshold 1)
    assert breaker.is_open() is False  # cooldown 0 -> trial call allowed (half-open)
    row = state.breaker_get("test-half-open")
    assert row["state"] == "half-open"
    # Successful trial call closes the circuit.
    assert breaker.guard(lambda: "back") == "back"
    assert state.breaker_get("test-half-open")["state"] == "closed"


def test_half_open_failure_reopens_immediately(state) -> None:
    breaker = CircuitBreaker(state, "test-reopen", threshold=5, cooldown_s=0.0)
    breaker.record_failure()
    assert state.breaker_get("test-reopen")["state"] == "closed"
    state.breaker_set("test-reopen", "open", 5, "2000-01-01T00:00:00+00:00")
    assert breaker.is_open() is False  # stale open -> half-open

    def boom() -> None:
        raise RuntimeError("still broken")

    with pytest.raises(RuntimeError):
        breaker.guard(boom)
    row = state.breaker_get("test-reopen")
    assert row["state"] == "open"
    assert int(str(row["failures"])) == 6


def test_breaker_state_persists_across_instances(state) -> None:
    first = CircuitBreaker(state, "shared", threshold=1, cooldown_s=600.0)
    first.record_failure()
    second = CircuitBreaker(state, "shared", threshold=1, cooldown_s=600.0)
    assert second.is_open() is True
