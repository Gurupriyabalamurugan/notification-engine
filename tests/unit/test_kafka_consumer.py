from unittest.mock import AsyncMock, MagicMock

import pytest
from aiokafka.structs import ConsumerRecord, TopicPartition

from app.messaging.kafka_consumer import PriorityKafkaConsumer
from app.messaging.topics import TOPIC_CRITICAL, TOPIC_HIGH, TOPIC_NORMAL


def _record(topic: str, offset: int) -> ConsumerRecord:
    return ConsumerRecord(
        topic=topic,
        partition=0,
        offset=offset,
        timestamp=0,
        timestamp_type=0,
        key=None,
        value=b'{"notification_id":"00000000-0000-0000-0000-000000000001"}',
        checksum=None,
        serialized_key_size=-1,
        serialized_value_size=-1,
        headers=[],
    )


@pytest.mark.asyncio
async def test_poll_returns_critical_before_high() -> None:
    consumer = PriorityKafkaConsumer(
        bootstrap_servers="localhost:19092",
        group_id="test-group",
        client_id="test-client",
    )
    mock_consumer = MagicMock()
    assignment = [
        TopicPartition(TOPIC_CRITICAL, 0),
        TopicPartition(TOPIC_HIGH, 0),
        TopicPartition(TOPIC_NORMAL, 0),
    ]
    mock_consumer.assignment.return_value = assignment
    mock_consumer.getmany = AsyncMock(
        return_value={
            TopicPartition(TOPIC_CRITICAL, 0): [_record(TOPIC_CRITICAL, 0)],
            TopicPartition(TOPIC_HIGH, 0): [_record(TOPIC_HIGH, 0)],
        }
    )
    mock_consumer.pause = MagicMock()
    mock_consumer.resume = MagicMock()
    consumer._consumer = mock_consumer

    records = await consumer.poll(batch_size=10, timeout_ms=100)

    assert len(records) == 1
    assert records[0].topic == TOPIC_CRITICAL


@pytest.mark.asyncio
async def test_poll_falls_through_to_high_when_critical_empty() -> None:
    consumer = PriorityKafkaConsumer(
        bootstrap_servers="localhost:19092",
        group_id="test-group",
        client_id="test-client",
    )
    mock_consumer = MagicMock()
    assignment = [
        TopicPartition(TOPIC_CRITICAL, 0),
        TopicPartition(TOPIC_HIGH, 0),
    ]
    mock_consumer.assignment.return_value = assignment
    mock_consumer.getmany = AsyncMock(
        side_effect=[
            {},
            {TopicPartition(TOPIC_HIGH, 0): [_record(TOPIC_HIGH, 1)]},
        ]
    )
    mock_consumer.pause = MagicMock()
    mock_consumer.resume = MagicMock()
    consumer._consumer = mock_consumer

    records = await consumer.poll(batch_size=10, timeout_ms=100)

    assert len(records) == 1
    assert records[0].topic == TOPIC_HIGH
