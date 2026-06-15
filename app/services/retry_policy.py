from datetime import timedelta


def next_delay(attempt: int, backoffs: list[int] | None = None) -> timedelta:
    """Return backoff delay after a failed attempt (1-indexed)."""
    schedule = backoffs or [30, 120, 600, 1800, 7200]
    if attempt < 1:
        raise ValueError("attempt must be >= 1")
    index = min(attempt - 1, len(schedule) - 1)
    return timedelta(seconds=schedule[index])
