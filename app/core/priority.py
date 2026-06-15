from app.domain.enums import PriorityLevel
from app.messaging.topics import PRIORITY_TOPICS

PRIORITY_MAP: dict[tuple[str, str], PriorityLevel] = {
    ("payment", "otp"): PriorityLevel.CRITICAL,
    ("payment", "fraud_alert"): PriorityLevel.CRITICAL,
    ("order", "confirmed"): PriorityLevel.HIGH,
    ("shipping", "delivered"): PriorityLevel.HIGH,
    ("order", "marketing"): PriorityLevel.LOW,
}


def resolve_priority(source_service: str, event_type: str) -> PriorityLevel:
    return PRIORITY_MAP.get((source_service, event_type), PriorityLevel.NORMAL)


def topic_for_priority(priority: PriorityLevel) -> str:
    return PRIORITY_TOPICS[priority]
