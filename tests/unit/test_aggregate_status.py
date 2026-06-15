import uuid

from app.domain.enums import ChannelType, DeliveryStatus, NotificationStatus
from app.domain.models import NotificationDelivery
from app.services.aggregate_status import aggregate_notification_status


def _delivery(status: DeliveryStatus) -> NotificationDelivery:
    return NotificationDelivery(
        id=uuid.uuid4(),
        notification_id=uuid.uuid4(),
        channel=ChannelType.EMAIL,
        status=status,
    )


def test_all_sent_returns_sent() -> None:
    deliveries = [_delivery(DeliveryStatus.SENT), _delivery(DeliveryStatus.SENT)]

    assert aggregate_notification_status(deliveries) == NotificationStatus.SENT


def test_all_failed_returns_failed() -> None:
    deliveries = [_delivery(DeliveryStatus.FAILED), _delivery(DeliveryStatus.FAILED)]

    assert aggregate_notification_status(deliveries) == NotificationStatus.FAILED


def test_mixed_sent_and_retrying_returns_partially_sent() -> None:
    deliveries = [
        _delivery(DeliveryStatus.SENT),
        _delivery(DeliveryStatus.RETRYING),
    ]

    assert aggregate_notification_status(deliveries) == NotificationStatus.PARTIALLY_SENT


def test_mixed_sent_and_failed_returns_partially_sent() -> None:
    deliveries = [
        _delivery(DeliveryStatus.SENT),
        _delivery(DeliveryStatus.FAILED),
    ]

    assert aggregate_notification_status(deliveries) == NotificationStatus.PARTIALLY_SENT


def test_all_retrying_returns_retrying() -> None:
    deliveries = [_delivery(DeliveryStatus.RETRYING), _delivery(DeliveryStatus.RETRYING)]

    assert aggregate_notification_status(deliveries) == NotificationStatus.RETRYING
