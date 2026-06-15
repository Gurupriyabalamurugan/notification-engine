import asyncio
import logging

from app.config import get_settings
from app.db.repository import NotificationRepository
from app.db.session import get_session_factory
from app.messaging.kafka_producer import NotificationKafkaProducer
from app.services.retry_scheduler import RetryScheduler

logger = logging.getLogger(__name__)


async def run_retry_worker(*, poll_interval_seconds: float | None = None) -> None:
    settings = get_settings()
    poll_interval_seconds = poll_interval_seconds or settings.retry_worker_poll_seconds
    producer = NotificationKafkaProducer.from_settings(settings)
    session_factory = get_session_factory()

    await producer.start()
    logger.info("Retry worker started (poll every %ss)", poll_interval_seconds)

    try:
        while True:
            async with session_factory() as session:
                repository = NotificationRepository(session)
                scheduler = RetryScheduler(repository, producer)
                processed = await scheduler.process_due_retries()
                await session.commit()
                if processed:
                    logger.info("Scheduled %s retry delivery(ies)", processed)

            await asyncio.sleep(poll_interval_seconds)
    finally:
        await producer.stop()


def main() -> None:
    logging.basicConfig(level=get_settings().log_level)
    asyncio.run(run_retry_worker())


if __name__ == "__main__":
    main()
