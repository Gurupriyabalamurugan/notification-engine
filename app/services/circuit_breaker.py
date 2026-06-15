from datetime import UTC, datetime, timedelta


class CircuitBreaker:
    def __init__(
        self,
        *,
        failure_threshold: int = 5,
        open_duration_seconds: int = 60,
    ) -> None:
        self.failure_threshold = failure_threshold
        self.open_duration = timedelta(seconds=open_duration_seconds)
        self._consecutive_failures = 0
        self._opened_at: datetime | None = None

    @property
    def consecutive_failures(self) -> int:
        return self._consecutive_failures

    def is_open(self, now: datetime | None = None) -> bool:
        now = now or datetime.now(UTC)
        if self._opened_at is None:
            return False
        if now - self._opened_at >= self.open_duration:
            self._opened_at = None
            self._consecutive_failures = 0
            return False
        return True

    def allow_request(self, now: datetime | None = None) -> bool:
        return not self.is_open(now)

    def record_success(self) -> None:
        self._consecutive_failures = 0
        self._opened_at = None

    def record_failure(self, now: datetime | None = None) -> None:
        now = now or datetime.now(UTC)
        self._consecutive_failures += 1
        if self._consecutive_failures >= self.failure_threshold:
            self._opened_at = now

    def seconds_until_half_open(self, now: datetime | None = None) -> int:
        now = now or datetime.now(UTC)
        if self._opened_at is None:
            return 0
        elapsed = now - self._opened_at
        remaining = self.open_duration - elapsed
        return max(0, int(remaining.total_seconds()))


class CircuitBreakerRegistry:
    def __init__(
        self,
        *,
        failure_threshold: int = 5,
        open_duration_seconds: int = 60,
    ) -> None:
        self._failure_threshold = failure_threshold
        self._open_duration_seconds = open_duration_seconds
        self._breakers: dict[str, CircuitBreaker] = {}

    def get(self, provider_key: str) -> CircuitBreaker:
        if provider_key not in self._breakers:
            self._breakers[provider_key] = CircuitBreaker(
                failure_threshold=self._failure_threshold,
                open_duration_seconds=self._open_duration_seconds,
            )
        return self._breakers[provider_key]
