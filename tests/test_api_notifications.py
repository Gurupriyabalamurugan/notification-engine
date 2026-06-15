from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import create_app


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


pytestmark = pytest.mark.usefixtures("migrated_db", "clean_tables")


@pytest.fixture
def fake_redis() -> FakeRedis:
    return FakeRedis()


@pytest.fixture
def api_kafka_producer(mock_kafka_lifecycle: AsyncMock, monkeypatch, fake_redis: FakeRedis) -> AsyncMock:
    monkeypatch.setattr("app.api.deps.get_redis_client", lambda settings=None: fake_redis)
    return mock_kafka_lifecycle


@pytest_asyncio.fixture
async def api_client(api_kafka_producer: AsyncMock):
    app = create_app()
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client, api_kafka_producer


@pytest.mark.asyncio
async def test_create_notification_returns_202(api_client) -> None:
    client, producer = api_client
    payload = {
        "idempotency_key": "api-otp-1",
        "source_service": "payment",
        "event_type": "otp",
        "user_id": "user-1",
        "channels": ["sms"],
        "payload": {"code": "123456"},
    }

    response = await client.post("/v1/notifications", json=payload)

    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "Pending"
    assert body["created"] is True
    producer.publish.assert_awaited_once()


@pytest.mark.asyncio
async def test_duplicate_notification_returns_200(api_client) -> None:
    client, producer = api_client
    payload = {
        "idempotency_key": "api-dup-1",
        "source_service": "order",
        "event_type": "confirmed",
        "user_id": "user-2",
        "channels": ["email"],
        "payload": {"order_id": "O-1"},
    }

    first = await client.post("/v1/notifications", json=payload)
    second = await client.post("/v1/notifications", json=payload)

    assert first.status_code == 202
    assert second.status_code == 200
    assert second.json()["notification_id"] == first.json()["notification_id"]
    assert producer.publish.await_count == 1


@pytest.mark.asyncio
async def test_get_notification_returns_delivery_status(api_client) -> None:
    client, _producer = api_client
    payload = {
        "idempotency_key": "api-get-1",
        "source_service": "order",
        "event_type": "confirmed",
        "user_id": "user-3",
        "channels": ["email", "push"],
        "payload": {"order_id": "O-99"},
    }

    created = await client.post("/v1/notifications", json=payload)
    notification_id = created.json()["notification_id"]

    response = await client.get(f"/v1/notifications/{notification_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["notification_id"] == notification_id
    assert len(body["deliveries"]) == 2
    assert {delivery["channel"] for delivery in body["deliveries"]} == {"email", "push"}


@pytest.mark.asyncio
async def test_get_notification_not_found(api_client) -> None:
    client, _producer = api_client
    response = await client.get(
        "/v1/notifications/00000000-0000-0000-0000-000000000099"
    )
    assert response.status_code == 404
