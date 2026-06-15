import asyncio
import random
import uuid

from app.providers.base import NotificationProvider, ProviderResult


class MockNotificationProvider(NotificationProvider):
    def __init__(
        self,
        channel: str,
        *,
        failure_rate: float = 0.0,
        is_down: bool = False,
        latency_ms: int = 0,
        rng: random.Random | None = None,
    ) -> None:
        self.channel = channel
        self.failure_rate = failure_rate
        self.is_down = is_down
        self.latency_ms = latency_ms
        self._rng = rng or random.Random()

    async def send(self, *, user_id: str, payload: dict) -> ProviderResult:
        if self.latency_ms > 0:
            await asyncio.sleep(self.latency_ms / 1000)

        if self.is_down:
            return ProviderResult(
                success=False,
                error=f"{self.channel} provider is down",
                latency_ms=self.latency_ms,
            )

        if self._rng.random() < self.failure_rate:
            return ProviderResult(
                success=False,
                error=f"{self.channel} simulated failure",
                latency_ms=self.latency_ms,
            )

        return ProviderResult(
            success=True,
            provider_ref=f"{self.channel}-{uuid.uuid4()}",
            latency_ms=self.latency_ms,
        )

    async def health_check(self) -> bool:
        return not self.is_down
