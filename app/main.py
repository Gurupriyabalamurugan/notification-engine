from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import health, notifications
from app.config import get_settings
from app.db.redis import close_redis_client
from app.db.session import dispose_engine
from app.messaging.kafka_producer import NotificationKafkaProducer


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    producer = NotificationKafkaProducer.from_settings(settings)
    await producer.start()
    app.state.kafka_producer = producer

    try:
        yield
    finally:
        await producer.stop()
        await close_redis_client()
        await dispose_engine()


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        debug=settings.debug,
        lifespan=lifespan,
    )

    app.include_router(health.router)
    app.include_router(notifications.router)

    return app


app = create_app()
