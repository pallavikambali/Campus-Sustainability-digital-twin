from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Incident, WasteDetection, Zone


def create_waste_detection(
    session: Session,
    zone_id: UUID,
    image_path: str,
    detected_objects: list[dict[str, str | float | dict[str, float] | None]],
    waste_level: str,
    model_name: str,
) -> WasteDetection:
    detection = WasteDetection(
        zone_id=zone_id,
        image_path=image_path,
        detected_objects=detected_objects,
        waste_level=waste_level,
        model_name=model_name,
    )
    session.add(detection)
    session.flush()
    session.refresh(detection)
    return detection


def list_waste_detections(
    session: Session, limit: int, zone_id: UUID | None = None
) -> list[tuple[WasteDetection, str]]:
    statement = (
        select(WasteDetection, Zone.name)
        .join(Zone, WasteDetection.zone_id == Zone.id)
        .order_by(WasteDetection.created_at.desc(), WasteDetection.id.desc())
        .limit(limit)
    )
    if zone_id is not None:
        statement = statement.where(WasteDetection.zone_id == zone_id)
    return list(session.execute(statement))


def get_latest_by_zone(session: Session) -> dict[UUID, WasteDetection]:
    detections = session.scalars(
        select(WasteDetection).order_by(
            WasteDetection.zone_id,
            WasteDetection.created_at.desc(),
            WasteDetection.id.desc(),
        )
    )
    latest: dict[UUID, WasteDetection] = {}
    for detection in detections:
        latest.setdefault(detection.zone_id, detection)
    return latest


def get_active_waste_incident(session: Session, zone_id: UUID) -> Incident | None:
    return session.scalar(
        select(Incident)
        .where(
            Incident.zone_id == zone_id,
            Incident.type == "WASTE_ACCUMULATION",
            Incident.status == "ACTIVE",
        )
        .order_by(Incident.created_at.desc())
        .limit(1)
        .with_for_update()
    )