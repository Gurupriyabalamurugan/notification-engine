"""Initial schema for notifications, deliveries, and attempts."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001_initial"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

notification_status = postgresql.ENUM(
    "Pending",
    "PartiallySent",
    "Sent",
    "Failed",
    "Retrying",
    name="notification_status",
    create_type=False,
)
delivery_status = postgresql.ENUM(
    "Pending",
    "Sent",
    "Failed",
    "Retrying",
    name="delivery_status",
    create_type=False,
)
channel_type = postgresql.ENUM(
    "email",
    "sms",
    "push",
    name="channel_type",
    create_type=False,
)
priority_level = postgresql.ENUM(
    "critical",
    "high",
    "normal",
    "low",
    name="priority_level",
    create_type=False,
)


def upgrade() -> None:
    notification_status.create(op.get_bind(), checkfirst=True)
    delivery_status.create(op.get_bind(), checkfirst=True)
    channel_type.create(op.get_bind(), checkfirst=True)
    priority_level.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("source_service", sa.String(length=32), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("priority", priority_level, nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("channels", postgresql.ARRAY(channel_type), nullable=False),
        sa.Column(
            "status",
            notification_status,
            server_default="Pending",
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key"),
    )
    op.create_index(
        "idx_notifications_status",
        "notifications",
        ["status", "created_at"],
        unique=False,
    )

    op.create_table(
        "notification_deliveries",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("notification_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("channel", channel_type, nullable=False),
        sa.Column(
            "status",
            delivery_status,
            server_default="Pending",
            nullable=False,
        ),
        sa.Column("attempt_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("max_attempts", sa.Integer(), server_default="5", nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("provider_ref", sa.String(length=128), nullable=True),
        sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["notification_id"],
            ["notifications.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "notification_id",
            "channel",
            name="uq_notification_channel",
        ),
    )
    op.create_index(
        "idx_deliveries_retry",
        "notification_deliveries",
        ["status", "next_retry_at"],
        unique=False,
        postgresql_where=sa.text("status = 'Retrying'"),
    )

    op.create_table(
        "delivery_attempts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("delivery_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("attempt_num", sa.Integer(), nullable=False),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["delivery_id"],
            ["notification_deliveries.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("delivery_attempts")
    op.drop_index(
        "idx_deliveries_retry",
        table_name="notification_deliveries",
        postgresql_where=sa.text("status = 'Retrying'"),
    )
    op.drop_table("notification_deliveries")
    op.drop_index("idx_notifications_status", table_name="notifications")
    op.drop_table("notifications")

    priority_level.drop(op.get_bind(), checkfirst=True)
    channel_type.drop(op.get_bind(), checkfirst=True)
    delivery_status.drop(op.get_bind(), checkfirst=True)
    notification_status.drop(op.get_bind(), checkfirst=True)
