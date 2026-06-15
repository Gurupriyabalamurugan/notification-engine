from app.providers.mock_base import MockNotificationProvider


class MockSMSProvider(MockNotificationProvider):
    def __init__(
        self,
        *,
        failure_rate: float = 0.0,
        is_down: bool = False,
        latency_ms: int = 0,
        rng=None,
    ) -> None:
        super().__init__(
            "sms",
            failure_rate=failure_rate,
            is_down=is_down,
            latency_ms=latency_ms,
            rng=rng,
        )
