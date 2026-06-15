from app.core.priority import resolve_priority, topic_for_priority
from app.domain.enums import PriorityLevel
from app.messaging.topics import (
    TOPIC_CRITICAL,
    TOPIC_HIGH,
    TOPIC_LOW,
    TOPIC_NORMAL,
)


def test_otp_maps_to_critical_topic() -> None:
    priority = resolve_priority("payment", "otp")

    assert priority == PriorityLevel.CRITICAL
    assert topic_for_priority(priority) == TOPIC_CRITICAL


def test_marketing_maps_to_low_topic() -> None:
    priority = resolve_priority("order", "marketing")

    assert priority == PriorityLevel.LOW
    assert topic_for_priority(priority) == TOPIC_LOW


def test_unknown_event_defaults_to_normal() -> None:
    priority = resolve_priority("order", "receipt")

    assert priority == PriorityLevel.NORMAL
    assert topic_for_priority(priority) == TOPIC_NORMAL


def test_order_confirmed_is_high() -> None:
    priority = resolve_priority("order", "confirmed")

    assert priority == PriorityLevel.HIGH
    assert topic_for_priority(priority) == TOPIC_HIGH
