import uuid

from app.domain.enums import ChannelType, PriorityLevel
from app.messaging.messages import (
    decode_notification_message,
    encode_notification_message,
    notification_message_payload,
)


def _notification():
    from app.domain.models import Notification

    notification_id = uuid.uuid4()
    return Notification(
        id=notification_id,
        idempotency_key="ord-1",
        source_service="order",
        event_type="confirmed",
        priority=PriorityLevel.HIGH,
        user_id="user-1",
        payload={"order_id": "O-1"},
        channels=[ChannelType.EMAIL],
    )


def test_notification_message_payload_fields() -> None:
    notification = _notification()
    payload = notification_message_payload(notification)

    assert payload["notification_id"] == str(notification.id)
    assert payload["idempotency_key"] == "ord-1"
    assert payload["priority"] == "high"


def test_encode_decode_roundtrip() -> None:
    notification = _notification()
    raw = encode_notification_message(notification)

    assert decode_notification_message(raw) == notification.id
