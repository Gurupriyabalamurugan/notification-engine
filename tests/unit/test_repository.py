from datetime import UTC, datetime, timedelta

import pytest

from app.domain.enums import ChannelType, DeliveryStatus, NotificationStatus, PriorityLevel
from app.domain.models import DeliveryAttempt
from app.db.repository import NotificationRepository

pytestmark = pytest.mark.usefixtures("migrated_db", "clean_tables")


@pytest.mark.asyncio
async def test_create_notification_persists_parent_and_deliveries(
    repository: NotificationRepository,
    db_session,
) -> None:
    notification, created = await repository.create_notification(
        idempotency_key="ord-1",
        source_service="order",
        event_type="confirmed",
        priority=PriorityLevel.HIGH,
        user_id="user-1",
        payload={"order_id": "O-99"},
        channels=[ChannelType.EMAIL, ChannelType.PUSH],
    )
    await db_session.commit()

    assert created is True
    assert notification.status == NotificationStatus.PENDING
    assert len(notification.deliveries) == 2
    assert {delivery.channel for delivery in notification.deliveries} == {
        ChannelType.EMAIL,
        ChannelType.PUSH,
    }


@pytest.mark.asyncio
async def test_create_notification_idempotent(
    repository: NotificationRepository,
    db_session,
) -> None:
    first, first_created = await repository.create_notification(
        idempotency_key="pay-otp-1",
        source_service="payment",
        event_type="otp",
        priority=PriorityLevel.CRITICAL,
        user_id="user-1",
        payload={"code": "123456"},
        channels=[ChannelType.SMS],
    )
    await db_session.commit()

    second, second_created = await repository.create_notification(
        idempotency_key="pay-otp-1",
        source_service="payment",
        event_type="otp",
        priority=PriorityLevel.CRITICAL,
        user_id="user-1",
        payload={"code": "123456"},
        channels=[ChannelType.SMS],
    )
    await db_session.commit()

    assert first_created is True
    assert second_created is False
    assert second.id == first.id
    assert len(second.deliveries) == 1


@pytest.mark.asyncio
async def test_get_by_idempotency_key(repository: NotificationRepository, db_session) -> None:
    await repository.create_notification(
        idempotency_key="ship-1",
        source_service="shipping",
        event_type="delivered",
        priority=PriorityLevel.HIGH,
        user_id="user-2",
        payload={"tracking_id": "T-1"},
        channels=[ChannelType.SMS],
    )
    await db_session.commit()

    found = await repository.get_by_idempotency_key("ship-1")

    assert found is not None
    assert found.user_id == "user-2"
    assert found.event_type == "delivered"


@pytest.mark.asyncio
async def test_update_delivery_status(repository: NotificationRepository, db_session) -> None:
    notification, _ = await repository.create_notification(
        idempotency_key="upd-1",
        source_service="order",
        event_type="confirmed",
        priority=PriorityLevel.NORMAL,
        user_id="user-3",
        payload={"order_id": "O-1"},
        channels=[ChannelType.EMAIL],
    )
    await db_session.commit()

    delivery = notification.deliveries[0]
    sent_at = datetime.now(UTC)
    updated = await repository.update_delivery_status(
        delivery.id,
        status=DeliveryStatus.SENT,
        attempt_count=1,
        provider_ref="email-msg-1",
        sent_at=sent_at,
        record_attempt=DeliveryAttempt(
            attempt_num=1,
            success=True,
            latency_ms=42,
        ),
    )
    await db_session.commit()

    assert updated is not None
    assert updated.status == DeliveryStatus.SENT
    assert updated.provider_ref == "email-msg-1"
    assert updated.attempt_count == 1


@pytest.mark.asyncio
async def test_get_retryable_deliveries(repository: NotificationRepository, db_session) -> None:
    notification, _ = await repository.create_notification(
        idempotency_key="retry-1",
        source_service="payment",
        event_type="otp",
        priority=PriorityLevel.CRITICAL,
        user_id="user-4",
        payload={"code": "999999"},
        channels=[ChannelType.SMS, ChannelType.EMAIL],
    )
    await db_session.commit()

    due_at = datetime.now(UTC) - timedelta(minutes=1)
    future_at = datetime.now(UTC) + timedelta(hours=1)

    sms_delivery = next(
        delivery for delivery in notification.deliveries if delivery.channel == ChannelType.SMS
    )
    email_delivery = next(
        delivery for delivery in notification.deliveries if delivery.channel == ChannelType.EMAIL
    )

    await repository.update_delivery_status(
        sms_delivery.id,
        status=DeliveryStatus.RETRYING,
        next_retry_at=due_at,
    )
    await repository.update_delivery_status(
        email_delivery.id,
        status=DeliveryStatus.RETRYING,
        next_retry_at=future_at,
    )
    await db_session.commit()

    retryable = await repository.get_retryable_deliveries(as_of=datetime.now(UTC))

    assert len(retryable) == 1
    assert retryable[0].channel == ChannelType.SMS
    assert retryable[0].notification.id == notification.id
