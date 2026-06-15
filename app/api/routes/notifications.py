import uuid

from fastapi import APIRouter, Depends, Header, HTTPException, status
from fastapi.responses import JSONResponse

from app.api.deps import get_notification_service, get_repository
from app.db.repository import NotificationRepository
from app.domain.schemas import (
    CreateNotificationRequest,
    DeliveryStatusResponse,
    NotificationDetailResponse,
    NotificationResponse,
)
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/v1/notifications", tags=["notifications"])


@router.post(
    "",
    response_model=NotificationResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses={status.HTTP_200_OK: {"model": NotificationResponse}},
)
async def create_notification(
    body: CreateNotificationRequest,
    service: NotificationService = Depends(get_notification_service),
    idempotency_key_header: str | None = Header(default=None, alias="Idempotency-Key"),
) -> JSONResponse:
    if idempotency_key_header:
        body = body.model_copy(update={"idempotency_key": idempotency_key_header})

    result = await service.create(body)
    response = NotificationResponse(
        notification_id=str(result.notification.id),
        status=result.notification.status.value,
        created=result.created,
    )
    status_code = status.HTTP_202_ACCEPTED if result.created else status.HTTP_200_OK
    return JSONResponse(status_code=status_code, content=response.model_dump())


@router.get("/{notification_id}", response_model=NotificationDetailResponse)
async def get_notification(
    notification_id: uuid.UUID,
    repository: NotificationRepository = Depends(get_repository),
) -> NotificationDetailResponse:
    notification = await repository.get_by_id(notification_id)
    if notification is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")

    return NotificationDetailResponse(
        notification_id=str(notification.id),
        idempotency_key=notification.idempotency_key,
        source_service=notification.source_service,
        event_type=notification.event_type,
        priority=notification.priority.value,
        user_id=notification.user_id,
        status=notification.status.value,
        channels=notification.channels,
        payload=notification.payload,
        deliveries=[
            DeliveryStatusResponse(
                channel=delivery.channel,
                status=delivery.status.value,
                attempt_count=delivery.attempt_count,
                max_attempts=delivery.max_attempts,
                last_error=delivery.last_error,
                provider_ref=delivery.provider_ref,
                next_retry_at=delivery.next_retry_at,
                sent_at=delivery.sent_at,
            )
            for delivery in notification.deliveries
        ],
        created_at=notification.created_at,
        updated_at=notification.updated_at,
    )
