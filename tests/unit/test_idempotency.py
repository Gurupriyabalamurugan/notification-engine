import uuid
from unittest.mock import AsyncMock

import pytest

from app.domain.enums import ChannelType
from app.domain.schemas import CreateNotificationRequest
from app.services.idempotency import IdempotencyService
from app.services.notification_service import NotificationService


class FakeRedis:
    def __init__(self) -> None:
        self._store: dict[str, str] = {}

    async def set(self, key: str, value: str, *, nx: bool = False, ex: int | None = None) -> bool:
        if nx and key in self._store:
            return False
        self._store[key] = value
        return True

    async def delete(self, key: str) -> None:
        self._store.pop(key, None)


@pytest.fixture
def fake_redis() -> FakeRedis:
    return FakeRedis()


@pytest.fixture
def mock_publisher() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def notification_service(
    repository,
    fake_redis: FakeRedis,
    mock_publisher: AsyncMock,
) -> NotificationService:
    idempotency = IdempotencyService(fake_redis, ttl_seconds=86400)
    return NotificationService(repository, idempotency, mock_publisher)


def _request(key: str = "pay-otp-abc") -> CreateNotificationRequest:
    return CreateNotificationRequest(
        idempotency_key=key,
        source_service="payment",
        event_type="otp",
        user_id="user-42",
        channels=[ChannelType.SMS],
        payload={"code": "123456"},
    )


@pytest.mark.asyncio
async def test_create_persists_and_publishes_once(
    notification_service: NotificationService,
    mock_publisher: AsyncMock,
    db_session,
    migrated_db: None,
    clean_tables: None,
) -> None:
    result = await notification_service.create(_request())
    await db_session.commit()

    assert result.created is True
    assert result.notification.status.value == "Pending"
    mock_publisher.publish.assert_awaited_once_with(result.notification)


@pytest.mark.asyncio
async def test_duplicate_key_returns_same_id_without_republishing(
    notification_service: NotificationService,
    mock_publisher: AsyncMock,
    db_session,
    migrated_db: None,
    clean_tables: None,
) -> None:
    first = await notification_service.create(_request("dup-key-1"))
    await db_session.commit()

    second = await notification_service.create(_request("dup-key-1"))
    await db_session.commit()

    assert first.created is True
    assert second.created is False
    assert second.notification.id == first.notification.id
    mock_publisher.publish.assert_awaited_once()


@pytest.mark.asyncio
async def test_idempotency_service_claim_and_release(fake_redis: FakeRedis) -> None:
    service = IdempotencyService(fake_redis, ttl_seconds=60)

    assert await service.claim("key-1") is True
    assert await service.claim("key-1") is False

    await service.release("key-1")
    assert await service.claim("key-1") is True
