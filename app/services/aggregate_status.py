from app.domain.enums import DeliveryStatus, NotificationStatus
from app.domain.models import NotificationDelivery


def aggregate_notification_status(
    deliveries: list[NotificationDelivery],
) -> NotificationStatus:
    if not deliveries:
        return NotificationStatus.PENDING

    statuses = {delivery.status for delivery in deliveries}

    if statuses == {DeliveryStatus.SENT}:
        return NotificationStatus.SENT

    if statuses == {DeliveryStatus.FAILED}:
        return NotificationStatus.FAILED

    if DeliveryStatus.SENT in statuses:
        return NotificationStatus.PARTIALLY_SENT

    if statuses == {DeliveryStatus.RETRYING}:
        return NotificationStatus.RETRYING

    if DeliveryStatus.RETRYING in statuses or DeliveryStatus.PENDING in statuses:
        return NotificationStatus.RETRYING

    return NotificationStatus.FAILED
