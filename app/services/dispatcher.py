import asyncio
import uuid
from collections.abc import Callable
from datetime import UTC, datetime

from app.config import Settings, get_settings
from app.db.repository import NotificationRepository
from app.domain.enums import DeliveryStatus
from app.domain.models import DeliveryAttempt, Notification, NotificationDelivery
from app.messaging.kafka_producer import NotificationKafkaProducer
from app.providers.registry import ProviderRegistry
from app.services.aggregate_status import aggregate_notification_status
from app.services.circuit_breaker import CircuitBreakerRegistry
from app.services.retry_policy import next_delay


class NotificationDispatcher:
    def __init__(
        self,
        repository: NotificationRepository,
        registry: ProviderRegistry,
        circuit_breakers: CircuitBreakerRegistry,
        *,
        backoffs: list[int] | None = None,
        now: Callable[[], datetime] | None = None,
        dlq_publisher: NotificationKafkaProducer | None = None,
    ) -> None:
        self._repository = repository
        self._registry = registry
        self._circuit_breakers = circuit_breakers
        self._backoffs = backoffs
        self._now = now or (lambda: datetime.now(UTC))
        self._dlq_publisher = dlq_publisher

    @classmethod
    def from_settings(
        cls,
        repository: NotificationRepository,
        registry: ProviderRegistry | None = None,
        circuit_breakers: CircuitBreakerRegistry | None = None,
        settings: Settings | None = None,
        dlq_publisher: NotificationKafkaProducer | None = None,
    ) -> "NotificationDispatcher":
        settings = settings or get_settings()
        return cls(
            repository,
            registry or ProviderRegistry.from_settings(settings),
            circuit_breakers
            or CircuitBreakerRegistry(
                failure_threshold=settings.circuit_breaker_failure_threshold,
                open_duration_seconds=settings.circuit_breaker_open_seconds,
            ),
            backoffs=settings.retry_backoff_seconds,
            dlq_publisher=dlq_publisher,
        )

    async def dispatch(self, notification_id: uuid.UUID) -> Notification | None:
        notification = await self._repository.get_by_id(notification_id)
        if notification is None:
            return None

        dispatchable = [
            delivery
            for delivery in notification.deliveries
            if delivery.status in (DeliveryStatus.PENDING, DeliveryStatus.RETRYING)
        ]

        if dispatchable:
            await asyncio.gather(
                *(self._dispatch_delivery(notification, delivery) for delivery in dispatchable),
                return_exceptions=True,
            )

        refreshed = await self._repository.get_by_id(notification_id)
        if refreshed is None:
            return None

        aggregate = aggregate_notification_status(refreshed.deliveries)
        await self._repository.update_notification_status(notification_id, aggregate)
        return await self._repository.get_by_id(notification_id)

    async def _dispatch_delivery(
        self,
        notification: Notification,
        delivery: NotificationDelivery,
    ) -> None:
        provider = self._registry.get(delivery.channel)
        breaker = self._circuit_breakers.get(provider.channel)
        now = self._now()
        attempt_num = delivery.attempt_count + 1

        if not breaker.allow_request(now):
            await self._repository.update_delivery_status(
                delivery.id,
                status=DeliveryStatus.RETRYING,
                attempt_count=delivery.attempt_count,
                last_error="Circuit breaker open",
                next_retry_at=now + next_delay(attempt_num, self._backoffs),
            )
            return

        result = await provider.send(
            user_id=notification.user_id,
            payload=notification.payload,
        )

        attempt = DeliveryAttempt(
            delivery_id=delivery.id,
            attempt_num=attempt_num,
            success=result.success,
            error=result.error,
            latency_ms=result.latency_ms,
        )

        if result.success:
            breaker.record_success()
            await self._repository.update_delivery_status(
                delivery.id,
                status=DeliveryStatus.SENT,
                attempt_count=attempt_num,
                provider_ref=result.provider_ref,
                sent_at=now,
                last_error=None,
                next_retry_at=None,
                record_attempt=attempt,
            )
            return

        breaker.record_failure(now)
        if attempt_num >= delivery.max_attempts:
            if self._dlq_publisher is not None:
                await self._dlq_publisher.publish_to_dlq(
                    notification,
                    delivery,
                    reason="Max delivery attempts exceeded",
                )
            await self._repository.update_delivery_status(
                delivery.id,
                status=DeliveryStatus.FAILED,
                attempt_count=attempt_num,
                last_error=result.error,
                next_retry_at=None,
                record_attempt=attempt,
            )
            return

        await self._repository.update_delivery_status(
            delivery.id,
            status=DeliveryStatus.RETRYING,
            attempt_count=attempt_num,
            last_error=result.error,
            next_retry_at=now + next_delay(attempt_num, self._backoffs),
            record_attempt=attempt,
        )
