import asyncio
import logging

from app.config import get_settings
from app.db.repository import NotificationRepository
from app.db.session import get_session_factory
from app.messaging.kafka_consumer import PriorityKafkaConsumer
from app.messaging.kafka_producer import NotificationKafkaProducer
from app.messaging.messages import decode_notification_message
from app.services.dispatcher import NotificationDispatcher

logger = logging.getLogger(__name__)


async def run_worker(*, poll_interval_seconds: float = 0.1) -> None:
    settings = get_settings()
    consumer = PriorityKafkaConsumer.from_settings(settings)
    producer = NotificationKafkaProducer.from_settings(settings)
    session_factory = get_session_factory()

    await consumer.start()
    await producer.start()
    logger.info("Dispatcher worker started")

    try:
        while True:
            records = await consumer.poll(batch_size=100, timeout_ms=1000)
            if not records:
                await asyncio.sleep(poll_interval_seconds)
                continue

            async with session_factory() as session:
                repository = NotificationRepository(session)
                dispatcher = NotificationDispatcher.from_settings(
                    repository,
                    dlq_publisher=producer,
                )

                for record in records:
                    notification_id = decode_notification_message(record.value)
                    try:
                        result = await dispatcher.dispatch(notification_id)
                        if result is None:
                            logger.warning(
                                "Notification %s not found; committing offset",
                                notification_id,
                            )
                    except Exception:
                        await session.rollback()
                        logger.exception(
                            "Failed to dispatch notification %s",
                            notification_id,
                        )
                        raise

                await session.commit()

            await consumer.commit(records)
            logger.info("Processed %s notification(s)", len(records))
    finally:
        await consumer.stop()
        await producer.stop()


def main() -> None:
    logging.basicConfig(level=get_settings().log_level)
    asyncio.run(run_worker())


if __name__ == "__main__":
    main()
