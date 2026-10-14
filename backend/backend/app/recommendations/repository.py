from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Incident, Recommendation, Zone


def get_incident_context(
    session: Session, incident_id: UUID
) -> tuple[Incident, Zone] | None:
    row = session.execute(
        select(Incident, Zone)
        .join(Zone, Incident.zone_id == Zone.id)
        .where(Incident.id == incident_id)
    ).first()
    return row


def create_recommendation(
    session: Session,
    incident_id: UUID,
    content: dict[str, object],
    provider: str,
) -> Recommendation:
    recommendation = Recommendation(
        incident_id=incident_id,
        content=content,
        provider=provider,
    )
    session.add(recommendation)
    session.flush()
    session.refresh(recommendation)
    return recommendation


def get_latest_recommendation(
    session: Session, incident_id: UUID
) -> Recommendation | None:
    return session.scalar(
        select(Recommendation)
        .where(Recommendation.incident_id == incident_id)
        .order_by(Recommendation.created_at.desc(), Recommendation.id.desc())
        .limit(1)
    )