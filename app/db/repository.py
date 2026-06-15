import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.enums import ChannelType, DeliveryStatus, NotificationStatus, PriorityLevel
from app.domain.models import DeliveryAttempt, Notification, NotificationDelivery

_UNSET: Any = object()


class NotificationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_notification(
        self,
        *,
        idempotency_key: str,
        source_service: str,
        event_type: str,
        priority: PriorityLevel,
        user_id: str,
        payload: dict,
        channels: list[ChannelType],
        max_attempts: int = 5,
    ) -> tuple[Notification, bool]:
        insert_stmt = (
            insert(Notification)
            .values(
                idempotency_key=idempotency_key,
                source_service=source_service,
                event_type=event_type,
                priority=priority,
                user_id=user_id,
                payload=payload,
                channels=channels,
                status=NotificationStatus.PENDING,
            )
            .on_conflict_do_nothing(index_elements=["idempotency_key"])
            .returning(Notification.id)
        )
        result = await self._session.execute(insert_stmt)
        created_id = result.scalar_one_or_none()

        if created_id is None:
            existing = await self.get_by_idempotency_key(idempotency_key)
            if existing is None:
                raise RuntimeError(
                    f"Notification conflict for idempotency_key={idempotency_key!r} "
                    "but row not found"
                )
            return existing, False

        for channel in channels:
            self._session.add(
                NotificationDelivery(
                    notification_id=created_id,
                    channel=channel,
                    max_attempts=max_attempts,
                    status=DeliveryStatus.PENDING,
                )
            )

        await self._session.flush()
        notification = await self.get_by_id(created_id)
        if notification is None:
            raise RuntimeError(f"Notification {created_id} not found after insert")
        return notification, True

    async def get_by_id(self, notification_id: uuid.UUID) -> Notification | None:
        stmt = (
            select(Notification)
            .where(Notification.id == notification_id)
            .options(selectinload(Notification.deliveries))
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_idempotency_key(self, idempotency_key: str) -> Notification | None:
        stmt = (
            select(Notification)
            .where(Notification.idempotency_key == idempotency_key)
            .options(selectinload(Notification.deliveries))
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_delivery_status(
        self,
        delivery_id: uuid.UUID,
        *,
        status: DeliveryStatus,
        attempt_count: int | None = None,
        last_error: str | None = _UNSET,
        provider_ref: str | None = _UNSET,
        next_retry_at: datetime | None = _UNSET,
        sent_at: datetime | None = _UNSET,
        record_attempt: DeliveryAttempt | None = None,
    ) -> NotificationDelivery | None:
        stmt = select(NotificationDelivery).where(NotificationDelivery.id == delivery_id)
        result = await self._session.execute(stmt)
        delivery = result.scalar_one_or_none()
        if delivery is None:
            return None

        delivery.status = status
        if attempt_count is not None:
            delivery.attempt_count = attempt_count
        if last_error is not _UNSET:
            delivery.last_error = last_error
        if provider_ref is not _UNSET:
            delivery.provider_ref = provider_ref
        if next_retry_at is not _UNSET:
            delivery.next_retry_at = next_retry_at
        if sent_at is not _UNSET:
            delivery.sent_at = sent_at

        if record_attempt is not None:
            record_attempt.delivery_id = delivery_id
            self._session.add(record_attempt)

        await self._session.flush()
        return delivery

    async def get_retryable_deliveries(
        self,
        *,
        as_of: datetime,
        limit: int = 100,
    ) -> list[NotificationDelivery]:
        stmt = (
            select(NotificationDelivery)
            .where(
                NotificationDelivery.status == DeliveryStatus.RETRYING,
                NotificationDelivery.next_retry_at <= as_of,
            )
            .options(selectinload(NotificationDelivery.notification))
            .order_by(NotificationDelivery.next_retry_at)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def update_notification_status(
        self,
        notification_id: uuid.UUID,
        status: NotificationStatus,
    ) -> Notification | None:
        stmt = select(Notification).where(Notification.id == notification_id)
        result = await self._session.execute(stmt)
        notification = result.scalar_one_or_none()
        if notification is None:
            return None

        notification.status = status
        await self._session.flush()
        return notification
