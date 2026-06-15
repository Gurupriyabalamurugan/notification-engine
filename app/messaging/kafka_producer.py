import json
import logging

from aiokafka import AIOKafkaProducer

from app.config import Settings, get_settings
from app.core.priority import topic_for_priority
from app.domain.models import Notification, NotificationDelivery
from app.messaging.messages import encode_notification_message
from app.messaging.topics import TOPIC_DLQ

logger = logging.getLogger(__name__)


class NotificationKafkaProducer:
    def __init__(
        self,
        *,
        bootstrap_servers: str,
        client_id: str,
    ) -> None:
        self._bootstrap_servers = bootstrap_servers
        self._client_id = client_id
        self._producer: AIOKafkaProducer | None = None

    @classmethod
    def from_settings(cls, settings: Settings | None = None) -> "NotificationKafkaProducer":
        settings = settings or get_settings()
        return cls(
            bootstrap_servers=settings.kafka_bootstrap_servers,
            client_id=settings.kafka_client_id,
        )

    async def start(self) -> None:
        if self._producer is not None:
            return
        self._producer = AIOKafkaProducer(
            bootstrap_servers=self._bootstrap_servers,
            client_id=self._client_id,
        )
        await self._producer.start()
        logger.info("Kafka producer started")

    async def stop(self) -> None:
        if self._producer is None:
            return
        await self._producer.stop()
        self._producer = None
        logger.info("Kafka producer stopped")

    async def publish(self, notification: Notification) -> None:
        if self._producer is None:
            raise RuntimeError("Kafka producer is not started")

        topic = topic_for_priority(notification.priority)
        payload = encode_notification_message(notification)
        await self._producer.send_and_wait(
            topic,
            payload,
            key=notification.idempotency_key.encode("utf-8"),
        )
        logger.debug(
            "Published notification %s to topic %s",
            notification.id,
            topic,
        )

    async def publish_raw(self, topic: str, payload: bytes, *, key: bytes | None = None) -> None:
        if self._producer is None:
            raise RuntimeError("Kafka producer is not started")
        await self._producer.send_and_wait(topic, payload, key=key)

    async def publish_to_dlq(
        self,
        notification: Notification,
        delivery: NotificationDelivery,
        *,
        reason: str,
    ) -> None:
        if self._producer is None:
            raise RuntimeError("Kafka producer is not started")

        payload = json.dumps(
            {
                "notification_id": str(notification.id),
                "delivery_id": str(delivery.id),
                "channel": delivery.channel.value,
                "reason": reason,
                "attempt_count": delivery.attempt_count,
                "last_error": delivery.last_error,
            }
        ).encode("utf-8")
        await self._producer.send_and_wait(
            TOPIC_DLQ,
            payload,
            key=notification.idempotency_key.encode("utf-8"),
        )
        logger.warning(
            "Published notification %s delivery %s to DLQ: %s",
            notification.id,
            delivery.id,
            reason,
        )
