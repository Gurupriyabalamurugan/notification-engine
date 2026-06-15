from datetime import timedelta

import pytest

from app.services.retry_policy import next_delay


def test_attempt_1_backoff_is_30_seconds() -> None:
    assert next_delay(1) == timedelta(seconds=30)


def test_attempt_3_backoff_is_10_minutes() -> None:
    assert next_delay(3) == timedelta(seconds=600)


def test_attempt_beyond_schedule_uses_last_value() -> None:
    assert next_delay(99) == timedelta(seconds=7200)


def test_attempt_must_be_positive() -> None:
    with pytest.raises(ValueError, match="attempt must be >= 1"):
        next_delay(0)
