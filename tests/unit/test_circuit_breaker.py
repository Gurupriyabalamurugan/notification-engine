from datetime import UTC, datetime, timedelta

import pytest

from app.services.circuit_breaker import CircuitBreaker, CircuitBreakerRegistry


def test_opens_after_consecutive_failures() -> None:
    breaker = CircuitBreaker(failure_threshold=5, open_duration_seconds=60)
    now = datetime(2026, 1, 1, tzinfo=UTC)

    for _ in range(4):
        breaker.record_failure(now)
        assert breaker.allow_request(now) is True

    breaker.record_failure(now)
    assert breaker.is_open(now) is True
    assert breaker.allow_request(now) is False


def test_success_resets_failure_count() -> None:
    breaker = CircuitBreaker(failure_threshold=5)
    now = datetime(2026, 1, 1, tzinfo=UTC)

    for _ in range(4):
        breaker.record_failure(now)

    breaker.record_success()
    assert breaker.consecutive_failures == 0
    assert breaker.allow_request(now) is True


def test_closes_after_open_duration() -> None:
    breaker = CircuitBreaker(failure_threshold=1, open_duration_seconds=60)
    opened_at = datetime(2026, 1, 1, tzinfo=UTC)

    breaker.record_failure(opened_at)
    assert breaker.allow_request(opened_at) is False

    later = opened_at + timedelta(seconds=61)
    assert breaker.allow_request(later) is True


def test_registry_returns_breaker_per_provider() -> None:
    registry = CircuitBreakerRegistry(failure_threshold=3, open_duration_seconds=30)

    email_breaker = registry.get("email")
    sms_breaker = registry.get("sms")

    assert email_breaker is not sms_breaker
    assert registry.get("email") is email_breaker
