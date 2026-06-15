import logging
from collections.abc import Iterable

from aiokafka import AIOKafkaConsumer
from aiokafka.structs import ConsumerRecord, TopicPartition

from app.config import Settings, get_settings
from app.messaging.topics import (
    TOPIC_CRITICAL,
    TOPIC_DLQ,
    TOPIC_HIGH,
    TOPIC_LOW,
    TOPIC_NORMAL,
)

logger = logging.getLogger(__name__)

ALL_NOTIFICATION_TOPICS = [
    TOPIC_CRITICAL,
    TOPIC_HIGH,
    TOPIC_NORMAL,
    TOPIC_LOW,
]


class PriorityKafkaConsumer:
    """Poll Kafka with strict priority: critical → high → normal → low."""

    def __init__(
        self,
        *,
        bootstrap_servers: str,
        group_id: str,
        client_id: str,
        topics: Iterable[str] | None = None,
    ) -> None:
        self._bootstrap_servers = bootstrap_servers
        self._group_id = group_id
        self._client_id = client_id
        self._topics = list(topics or ALL_NOTIFICATION_TOPICS)
        self._consumer: AIOKafkaConsumer | None = None

    @classmethod
    def from_settings(cls, settings: Settings | None = None) -> "PriorityKafkaConsumer":
        settings = settings or get_settings()
        return cls(
            bootstrap_servers=settings.kafka_bootstrap_servers,
            group_id=settings.kafka_consumer_group,
            client_id=f"{settings.kafka_client_id}-consumer",
        )

    async def start(self) -> None:
        if self._consumer is not None:
            return
        self._consumer = AIOKafkaConsumer(
            *self._topics,
            bootstrap_servers=self._bootstrap_servers,
            group_id=self._group_id,
            client_id=self._client_id,
            enable_auto_commit=False,
            auto_offset_reset="earliest",
        )
        await self._consumer.start()
        logger.info("Kafka consumer started for topics: %s", self._topics)

    async def stop(self) -> None:
        if self._consumer is None:
            return
        await self._consumer.stop()
        self._consumer = None
        logger.info("Kafka consumer stopped")

    @property
    def consumer(self) -> AIOKafkaConsumer:
        if self._consumer is None:
            raise RuntimeError("Kafka consumer is not started")
        return self._consumer

    async def poll(
        self,
        *,
        batch_size: int = 100,
        timeout_ms: int = 1000,
    ) -> list[ConsumerRecord]:
        consumer = self.consumer
        assignment = consumer.assignment()
        if not assignment:
            await consumer.getmany(timeout_ms=timeout_ms, max_records=1)
            assignment = consumer.assignment()
        if not assignment:
            return []

        topic_names = [
            topic
            for topic in ALL_NOTIFICATION_TOPICS
            if topic in {tp.topic for tp in assignment}
        ]

        for topic in topic_names:
            topic_partitions = [tp for tp in assignment if tp.topic == topic]
            other_partitions = [tp for tp in assignment if tp.topic != topic]
            if other_partitions:
                consumer.pause(*other_partitions)
            if topic_partitions:
                consumer.resume(*topic_partitions)

            data = await consumer.getmany(timeout_ms=timeout_ms, max_records=batch_size)
            messages: list[ConsumerRecord] = []
            for tp in topic_partitions:
                messages.extend(data.get(tp, []))

            if other_partitions:
                consumer.resume(*assignment)

            if messages:
                messages.sort(key=lambda record: (record.partition, record.offset))
                return messages[:batch_size]

        return []

    async def commit(self, records: list[ConsumerRecord]) -> None:
        if not records:
            return
        offsets: dict[TopicPartition, int] = {}
        for record in records:
            tp = TopicPartition(record.topic, record.partition)
            offsets[tp] = max(offsets.get(tp, -1), record.offset + 1)
        await self.consumer.commit({tp: offset for tp, offset in offsets.items()})


class DlqKafkaConsumer(PriorityKafkaConsumer):
    """Consumer helper for DLQ inspection (phase 8)."""

    def __init__(self, *, bootstrap_servers: str, group_id: str, client_id: str) -> None:
        super().__init__(
            bootstrap_servers=bootstrap_servers,
            group_id=group_id,
            client_id=client_id,
            topics=[TOPIC_DLQ],
        )
