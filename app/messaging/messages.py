import json
import uuid
from typing import Protocol

from app.domain.models import Notification


class NotificationPublisher(Protocol):
    async def publish(self, notification: Notification) -> None: ...


def notification_message_payload(notification: Notification) -> dict:
    return {
        "notification_id": str(notification.id),
        "idempotency_key": notification.idempotency_key,
        "priority": notification.priority.value,
        "source_service": notification.source_service,
        "event_type": notification.event_type,
    }


def encode_notification_message(notification: Notification) -> bytes:
    return json.dumps(notification_message_payload(notification)).encode("utf-8")


def decode_notification_message(raw: bytes) -> uuid.UUID:
    data = json.loads(raw.decode("utf-8"))
    return uuid.UUID(data["notification_id"])
