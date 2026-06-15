from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ProviderResult:
    success: bool
    provider_ref: str | None = None
    error: str | None = None
    latency_ms: int = 0


class NotificationProvider(ABC):
    channel: str

    @abstractmethod
    async def send(self, *, user_id: str, payload: dict) -> ProviderResult: ...

    @abstractmethod
    async def health_check(self) -> bool: ...
