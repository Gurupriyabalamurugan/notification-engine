import uuid
from collections.abc import AsyncGenerator

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.redis import get_redis_client
from app.db.repository import NotificationRepository
from app.db.session import get_session_factory
from app.messaging.kafka_producer import NotificationKafkaProducer
from app.services.idempotency import IdempotencyService
from app.services.notification_service import NotificationService


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def get_kafka_producer(request: Request) -> NotificationKafkaProducer:
    return request.app.state.kafka_producer


async def get_notification_service(
    session: AsyncSession = Depends(get_db_session),
    producer: NotificationKafkaProducer = Depends(get_kafka_producer),
) -> NotificationService:
    settings = get_settings()
    repository = NotificationRepository(session)
    idempotency = IdempotencyService(
        get_redis_client(settings),
        ttl_seconds=settings.idempotency_ttl_seconds,
    )
    return NotificationService(repository, idempotency, producer)


async def get_repository(
    session: AsyncSession = Depends(get_db_session),
) -> NotificationRepository:
    return NotificationRepository(session)
