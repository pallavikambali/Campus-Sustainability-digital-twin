from datetime import datetime
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db import get_session
from app.models import Incident, NotificationDelivery, Zone

router = APIRouter(prefix="/api/v1/notifications", tags=["notifications"])


class ChannelStatus(BaseModel):
    status: Literal["READY", "NOT_CONFIGURED"]
    enabled: bool


class NotificationStatusResponse(BaseModel):
    email: ChannelStatus
    whatsapp: ChannelStatus


class NotificationHistoryItem(BaseModel):
    id: UUID
    incident_id: UUID
    incident_type: str
    zone_name: str
    severity: str
    channel: str
    status: str
    attempted_at: datetime
    error: str | None


@router.get("/status", response_model=NotificationStatusResponse)
def get_notification_status() -> NotificationStatusResponse:
    return NotificationStatusResponse(
        email=ChannelStatus(
            status="READY" if settings.email_alerts_configured else "NOT_CONFIGURED",
            enabled=settings.email_alerts_configured,
        ),
        # WhatsApp sending is deliberately not enabled until its official API
        # integration and authenticated configuration UI are implemented.
        whatsapp=ChannelStatus(status="NOT_CONFIGURED", enabled=False),
    )


@router.get("", response_model=list[NotificationHistoryItem])
def get_notification_history(
    limit: int = Query(default=50, ge=1, le=200),
    session: Session = Depends(get_session),
) -> list[NotificationHistoryItem]:
    rows = session.execute(
        select(NotificationDelivery, Incident, Zone.name)
        .join(Incident, NotificationDelivery.incident_id == Incident.id)
        .join(Zone, Incident.zone_id == Zone.id)
        .order_by(
            NotificationDelivery.attempted_at.desc(),
            NotificationDelivery.id.desc(),
        )
        .limit(limit)
    )
    return [
        NotificationHistoryItem(
            id=delivery.id,
            incident_id=incident.id,
            incident_type=incident.type,
            zone_name=zone_name,
            severity=incident.severity,
            channel=delivery.channel,
            status=delivery.status,
            attempted_at=delivery.attempted_at,
            error=delivery.error,
        )
        for delivery, incident, zone_name in rows
    ]
