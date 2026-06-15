from app.domain.enums import PriorityLevel

TOPIC_CRITICAL = "notifications.critical"
TOPIC_HIGH = "notifications.high"
TOPIC_NORMAL = "notifications.normal"
TOPIC_LOW = "notifications.low"
TOPIC_DLQ = "notifications.dlq"

PRIORITY_TOPICS: dict[PriorityLevel, str] = {
    PriorityLevel.CRITICAL: TOPIC_CRITICAL,
    PriorityLevel.HIGH: TOPIC_HIGH,
    PriorityLevel.NORMAL: TOPIC_NORMAL,
    PriorityLevel.LOW: TOPIC_LOW,
}

PRIORITY_ORDER: list[PriorityLevel] = [
    PriorityLevel.CRITICAL,
    PriorityLevel.HIGH,
    PriorityLevel.NORMAL,
    PriorityLevel.LOW,
]
