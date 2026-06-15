import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from app.domain.enums import ChannelType, DeliveryStatus, NotificationStatus, PriorityLevel
from app.domain.models import Notification, NotificationDelivery
from app.services.retry_scheduler import RetryScheduler


@pytest.fixture
def mock_repository() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def mock_producer() -> AsyncMock:
    producer = AsyncMock()
    producer.publish = AsyncMock()
    producer.publish_to_dlq = AsyncMock()
    return producer


def _notification(notification_id: uuid.UUID | None = None) -> Notification:
    notification_id = notification_id or uuid.uuid4()
    return Notification(
        id=notification_id,
        idempotency_key="retry-1",
        source_service="payment",
        event_type="otp",
        priority=PriorityLevel.CRITICAL,
        user_id="user-1",
        payload={"code": "123456"},
        channels=[ChannelType.SMS],
        status=NotificationStatus.RETRYING,
    )


def _delivery(
    notification: Notification,
    *,
    attempt_count: int = 1,
    max_attempts: int = 5,
) -> NotificationDelivery:
    delivery = NotificationDelivery(
        id=uuid.uuid4(),
        notification_id=notification.id,
        channel=ChannelType.SMS,
        status=DeliveryStatus.RETRYING,
        attempt_count=attempt_count,
        max_attempts=max_attempts,
        next_retry_at=datetime.now(UTC),
    )
    delivery.notification = notification
    notification.deliveries = [delivery]
    return delivery


@pytest.mark.asyncio
async def test_republishes_due_delivery(mock_repository: AsyncMock, mock_producer: AsyncMock) -> None:
    notification = _notification()
    delivery = _delivery(notification)
    mock_repository.get_retryable_deliveries.return_value = [delivery]
    mock_repository.get_by_id.return_value = notification

    scheduler = RetryScheduler(mock_repository, mock_producer)
    processed = await scheduler.process_due_retries(as_of=datetime.now(UTC))

    assert processed == 1
    mock_producer.publish.assert_awaited_once_with(notification)
    mock_producer.publish_to_dlq.assert_not_awaited()


@pytest.mark.asyncio
async def test_sends_to_dlq_when_max_attempts_reached(
    mock_repository: AsyncMock,
    mock_producer: AsyncMock,
) -> None:
    notification = _notification()
    delivery = _delivery(notification, attempt_count=5, max_attempts=5)
    mock_repository.get_retryable_deliveries.return_value = [delivery]
    mock_repository.get_by_id.return_value = notification

    scheduler = RetryScheduler(mock_repository, mock_producer)
    processed = await scheduler.process_due_retries(as_of=datetime.now(UTC))

    assert processed == 1
    mock_producer.publish.assert_not_awaited()
    mock_producer.publish_to_dlq.assert_awaited_once()
    mock_repository.update_delivery_status.assert_awaited()
