from dataclasses import dataclass

from app.core.priority import resolve_priority
from app.db.repository import NotificationRepository
from app.domain.models import Notification
from app.domain.schemas import CreateNotificationRequest
from app.messaging.messages import NotificationPublisher
from app.services.idempotency import IdempotencyService


@dataclass(frozen=True)
class CreateNotificationResult:
    notification: Notification
    created: bool


class NotificationService:
    def __init__(
        self,
        repository: NotificationRepository,
        idempotency: IdempotencyService,
        publisher: NotificationPublisher,
    ) -> None:
        self._repository = repository
        self._idempotency = idempotency
        self._publisher = publisher

    async def create(self, request: CreateNotificationRequest) -> CreateNotificationResult:
        claimed = await self._idempotency.claim(request.idempotency_key)
        if not claimed:
            existing = await self._repository.get_by_idempotency_key(request.idempotency_key)
            if existing is not None:
                return CreateNotificationResult(notification=existing, created=False)

        priority = resolve_priority(request.source_service, request.event_type)

        try:
            notification, created = await self._repository.create_notification(
                idempotency_key=request.idempotency_key,
                source_service=request.source_service,
                event_type=request.event_type,
                priority=priority,
                user_id=request.user_id,
                payload=request.payload,
                channels=request.channels,
            )
        except Exception:
            if claimed:
                await self._idempotency.release(request.idempotency_key)
            raise

        if not created:
            return CreateNotificationResult(notification=notification, created=False)

        await self._publisher.publish(notification)
        return CreateNotificationResult(notification=notification, created=True)
