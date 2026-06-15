import asyncio
import logging
import sys
from pathlib import Path

from aiokafka.admin import AIOKafkaAdminClient, NewTopic

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import get_settings
from app.messaging.topics import (
    TOPIC_CRITICAL,
    TOPIC_DLQ,
    TOPIC_HIGH,
    TOPIC_LOW,
    TOPIC_NORMAL,
)

logging.basicConfig(level=get_settings().log_level)
logger = logging.getLogger(__name__)

TOPICS = [TOPIC_CRITICAL, TOPIC_HIGH, TOPIC_NORMAL, TOPIC_LOW, TOPIC_DLQ]


async def init_topics() -> None:
    settings = get_settings()
    admin = AIOKafkaAdminClient(bootstrap_servers=settings.kafka_bootstrap_servers)
    await admin.start()

    try:
        for topic in TOPICS:
            try:
                await admin.create_topics(
                    [
                        NewTopic(
                            name=topic,
                            num_partitions=settings.kafka_topic_partitions,
                            replication_factor=1,
                        )
                    ]
                )
                logger.info("Created topic %s", topic)
            except Exception as exc:
                if "already exists" in str(exc).lower():
                    logger.info("Topic %s already exists", topic)
                else:
                    raise
    finally:
        await admin.close()


if __name__ == "__main__":
    asyncio.run(init_topics())
