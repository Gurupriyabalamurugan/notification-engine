from datetime import datetime

from pydantic import BaseModel, Field

from app.domain.enums import ChannelType


class CreateNotificationRequest(BaseModel):
    idempotency_key: str = Field(min_length=1, max_length=128)
    source_service: str = Field(min_length=1, max_length=32)
    event_type: str = Field(min_length=1, max_length=64)
    user_id: str = Field(min_length=1, max_length=64)
    channels: list[ChannelType] = Field(min_length=1)
    payload: dict = Field(default_factory=dict)


class NotificationResponse(BaseModel):
    notification_id: str
    status: str
    created: bool


class DeliveryStatusResponse(BaseModel):
    channel: ChannelType
    status: str
    attempt_count: int
    max_attempts: int
    last_error: str | None = None
    provider_ref: str | None = None
    next_retry_at: datetime | None = None
    sent_at: datetime | None = None


class NotificationDetailResponse(BaseModel):
    notification_id: str
    idempotency_key: str
    source_service: str
    event_type: str
    priority: str
    user_id: str
    status: str
    channels: list[ChannelType]
    payload: dict
    deliveries: list[DeliveryStatusResponse]
    created_at: datetime
    updated_at: datetime
