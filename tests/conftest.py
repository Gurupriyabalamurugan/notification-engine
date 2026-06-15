import asyncio
from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings
from app.db.repository import NotificationRepository
from app.db.session import dispose_engine


def _run_migrations() -> None:
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")


async def _postgres_is_available() -> bool:
    settings = get_settings()
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
    finally:
        await engine.dispose()


@pytest.fixture(scope="session")
def postgres_available() -> bool:
    return asyncio.run(_postgres_is_available())


@pytest.fixture(scope="session")
def migrated_db(postgres_available: bool) -> None:
    if not postgres_available:
        pytest.skip("PostgreSQL is not available — start with: docker compose up -d postgres")
    _run_migrations()


@pytest_asyncio.fixture
async def db_session(migrated_db: None) -> AsyncGenerator[AsyncSession, None]:
    settings = get_settings()
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session:
        yield session
        await session.rollback()

    await engine.dispose()
    await dispose_engine()


@pytest_asyncio.fixture
async def clean_tables(db_session: AsyncSession) -> AsyncGenerator[None, None]:
    yield
    await db_session.execute(text("DELETE FROM delivery_attempts"))
    await db_session.execute(text("DELETE FROM notification_deliveries"))
    await db_session.execute(text("DELETE FROM notifications"))
    await db_session.commit()


@pytest_asyncio.fixture
async def repository(db_session: AsyncSession) -> NotificationRepository:
    return NotificationRepository(db_session)


@pytest.fixture
def mock_kafka_lifecycle(monkeypatch) -> AsyncMock:
    """Patch Kafka/Redis/DB teardown for API tests without a broker."""
    producer = AsyncMock()
    producer.start = AsyncMock()
    producer.stop = AsyncMock()
    producer.publish = AsyncMock()
    monkeypatch.setattr(
        "app.main.NotificationKafkaProducer.from_settings",
        lambda settings=None: producer,
    )
    monkeypatch.setattr("app.db.redis.close_redis_client", AsyncMock())
    monkeypatch.setattr("app.db.session.dispose_engine", AsyncMock())
    return producer
