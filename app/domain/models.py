import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.domain.enums import (
    ChannelType,
    DeliveryStatus,
    NotificationStatus,
    PriorityLevel,
)


class Base(DeclarativeBase):
    pass


notification_status_enum = Enum(
    NotificationStatus,
    name="notification_status",
    values_callable=lambda enum_cls: [member.value for member in enum_cls],
)

delivery_status_enum = Enum(
    DeliveryStatus,
    name="delivery_status",
    values_callable=lambda enum_cls: [member.value for member in enum_cls],
)

channel_type_enum = Enum(
    ChannelType,
    name="channel_type",
    values_callable=lambda enum_cls: [member.value for member in enum_cls],
)

priority_level_enum = Enum(
    PriorityLevel,
    name="priority_level",
    values_callable=lambda enum_cls: [member.value for member in enum_cls],
)


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    idempotency_key: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    source_service: Mapped[str] = mapped_column(String(32), nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    priority: Mapped[PriorityLevel] = mapped_column(priority_level_enum, nullable=False)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    channels: Mapped[list[ChannelType]] = mapped_column(
        ARRAY(channel_type_enum), nullable=False
    )
    status: Mapped[NotificationStatus] = mapped_column(
        notification_status_enum,
        nullable=False,
        default=NotificationStatus.PENDING,
        server_default=NotificationStatus.PENDING.value,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    deliveries: Mapped[list["NotificationDelivery"]] = relationship(
        back_populates="notification",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("idx_notifications_status", "status", "created_at"),
    )


class NotificationDelivery(Base):
    __tablename__ = "notification_deliveries"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    notification_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("notifications.id", ondelete="CASCADE"),
        nullable=False,
    )
    channel: Mapped[ChannelType] = mapped_column(channel_type_enum, nullable=False)
    status: Mapped[DeliveryStatus] = mapped_column(
        delivery_status_enum,
        nullable=False,
        default=DeliveryStatus.PENDING,
        server_default=DeliveryStatus.PENDING.value,
    )
    attempt_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    max_attempts: Mapped[int] = mapped_column(
        Integer, nullable=False, default=5, server_default="5"
    )
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    provider_ref: Mapped[str | None] = mapped_column(String(128), nullable=True)
    next_retry_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    notification: Mapped["Notification"] = relationship(back_populates="deliveries")
    attempts: Mapped[list["DeliveryAttempt"]] = relationship(
        back_populates="delivery",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint("notification_id", "channel", name="uq_notification_channel"),
        Index(
            "idx_deliveries_retry",
            "status",
            "next_retry_at",
            postgresql_where=text("status = 'Retrying'"),
        ),
    )


class DeliveryAttempt(Base):
    __tablename__ = "delivery_attempts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    delivery_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("notification_deliveries.id", ondelete="CASCADE"),
        nullable=False,
    )
    attempt_num: Mapped[int] = mapped_column(Integer, nullable=False)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    delivery: Mapped["NotificationDelivery"] = relationship(back_populates="attempts")
