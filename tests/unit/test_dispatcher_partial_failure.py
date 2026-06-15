from datetime import UTC, datetime

import pytest

from app.domain.enums import (
    ChannelType,
    DeliveryStatus,
    NotificationStatus,
    PriorityLevel,
)
from app.providers.mock_email import MockEmailProvider
from app.providers.mock_sms import MockSMSProvider
from app.providers.registry import ProviderRegistry
from app.services.circuit_breaker import CircuitBreakerRegistry
from app.services.dispatcher import NotificationDispatcher

pytestmark = pytest.mark.usefixtures("migrated_db", "clean_tables")


@pytest.mark.asyncio
async def test_dispatcher_partial_failure(
    repository,
    db_session,
) -> None:
    registry = ProviderRegistry(
        {
            ChannelType.EMAIL: MockEmailProvider(failure_rate=0.0),
            ChannelType.SMS: MockSMSProvider(is_down=True),
        }
    )
    dispatcher = NotificationDispatcher(
        repository,
        registry,
        CircuitBreakerRegistry(failure_threshold=5, open_duration_seconds=60),
        now=lambda: datetime(2026, 6, 14, 12, 0, tzinfo=UTC),
    )

    notification, _ = await repository.create_notification(
        idempotency_key="partial-1",
        source_service="order",
        event_type="confirmed",
        priority=PriorityLevel.HIGH,
        user_id="user-1",
        payload={"order_id": "O-1"},
        channels=[ChannelType.EMAIL, ChannelType.SMS],
    )
    await db_session.commit()

    result = await dispatcher.dispatch(notification.id)
    await db_session.commit()

    assert result is not None
    assert result.status == NotificationStatus.PARTIALLY_SENT

    by_channel = {delivery.channel: delivery for delivery in result.deliveries}
    assert by_channel[ChannelType.EMAIL].status == DeliveryStatus.SENT
    assert by_channel[ChannelType.SMS].status == DeliveryStatus.RETRYING
    assert by_channel[ChannelType.SMS].last_error == "sms provider is down"


@pytest.mark.asyncio
async def test_dispatcher_all_channels_sent(
    repository,
    db_session,
) -> None:
    from app.providers.mock_push import MockPushProvider

    registry = ProviderRegistry(
        {
            ChannelType.EMAIL: MockEmailProvider(failure_rate=0.0),
            ChannelType.PUSH: MockPushProvider(failure_rate=0.0),
        }
    )
    dispatcher = NotificationDispatcher(
        repository,
        registry,
        CircuitBreakerRegistry(),
        now=lambda: datetime(2026, 6, 14, 12, 0, tzinfo=UTC),
    )

    notification, _ = await repository.create_notification(
        idempotency_key="all-sent-1",
        source_service="order",
        event_type="confirmed",
        priority=PriorityLevel.HIGH,
        user_id="user-2",
        payload={"order_id": "O-2"},
        channels=[ChannelType.EMAIL, ChannelType.PUSH],
    )
    await db_session.commit()

    result = await dispatcher.dispatch(notification.id)
    await db_session.commit()

    assert result is not None
    assert result.status == NotificationStatus.SENT
    assert all(delivery.status == DeliveryStatus.SENT for delivery in result.deliveries)


@pytest.mark.asyncio
async def test_dispatcher_marks_failed_after_max_attempts(
    repository,
    db_session,
) -> None:
    registry = ProviderRegistry({ChannelType.SMS: MockSMSProvider(is_down=True)})
    dispatcher = NotificationDispatcher(
        repository,
        registry,
        CircuitBreakerRegistry(),
        now=lambda: datetime(2026, 6, 14, 12, 0, tzinfo=UTC),
    )

    notification, _ = await repository.create_notification(
        idempotency_key="max-attempts-1",
        source_service="payment",
        event_type="otp",
        priority=PriorityLevel.CRITICAL,
        user_id="user-3",
        payload={"code": "111111"},
        channels=[ChannelType.SMS],
        max_attempts=2,
    )
    await db_session.commit()

    await dispatcher.dispatch(notification.id)
    await db_session.commit()
    await dispatcher.dispatch(notification.id)
    await db_session.commit()

    result = await repository.get_by_id(notification.id)
    assert result is not None
    assert result.status == NotificationStatus.FAILED
    assert result.deliveries[0].status == DeliveryStatus.FAILED
    assert result.deliveries[0].attempt_count == 2
