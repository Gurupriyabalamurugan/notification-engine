import enum


class NotificationStatus(str, enum.Enum):
    PENDING = "Pending"
    PARTIALLY_SENT = "PartiallySent"
    SENT = "Sent"
    FAILED = "Failed"
    RETRYING = "Retrying"


class DeliveryStatus(str, enum.Enum):
    PENDING = "Pending"
    SENT = "Sent"
    FAILED = "Failed"
    RETRYING = "Retrying"


class ChannelType(str, enum.Enum):
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"


class PriorityLevel(str, enum.Enum):
    CRITICAL = "critical"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"
