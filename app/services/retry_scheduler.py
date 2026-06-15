import logging
import uuid
from collections.abc import Callable
from datetime import UTC, datetime

from app.db.repository import NotificationRepository
from app.domain.enums import DeliveryStatus
from app.messaging.kafka_producer import NotificationKafkaProducer
from app.services.aggregate_status import aggregate_notification_status

logger = logging.getLogger(__name__)


class RetryScheduler:
    def __init__(
        self,
        repository: NotificationRepository,
        producer: NotificationKafkaProducer,
        *,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self._repository = repository
        self._producer = producer
        self._now = now or (lambda: datetime.now(UTC))

    async def process_due_retries(self, *, as_of: datetime | None = None) -> int:
        as_of = as_of or self._now()
        deliveries = await self._repository.get_retryable_deliveries(as_of=as_of)
        if not deliveries:
            return 0

        republished: set[uuid.UUID] = set()
        affected_notifications: set[uuid.UUID] = set()

        for delivery in deliveries:
            notification = delivery.notification
            affected_notifications.add(notification.id)

            if delivery.attempt_count >= delivery.max_attempts:
                await self._producer.publish_to_dlq(
                    notification,
                    delivery,
                    reason="Max delivery attempts exceeded during retry scheduling",
                )
                await self._repository.update_delivery_status(
                    delivery.id,
                    status=DeliveryStatus.FAILED,
                    last_error=delivery.last_error or "Max delivery attempts exceeded",
                    next_retry_at=None,
                )
                continue

            if notification.id not in republished:
                await self._producer.publish(notification)
                republished.add(notification.id)
                logger.info("Re-published notification %s for retry", notification.id)

        for notification_id in affected_notifications:
            notification = await self._repository.get_by_id(notification_id)
            if notification is None:
                continue
            aggregate = aggregate_notification_status(notification.deliveries)
            await self._repository.update_notification_status(notification_id, aggregate)

        return len(deliveries)
