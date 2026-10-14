from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Incident, SensorReading, Zone


def list_zones(session: Session) -> list[Zone]:
    return list(session.scalars(select(Zone).order_by(Zone.name)))


def get_zone(session: Session, zone_id: UUID) -> Zone | None:
    return session.get(Zone, zone_id)


def list_latest_readings(session: Session) -> dict[UUID, SensorReading]:
    readings = session.scalars(
        select(SensorReading).order_by(
            SensorReading.zone_id,
            SensorReading.timestamp.desc(),
            SensorReading.id.desc(),
        )
    )
    latest: dict[UUID, SensorReading] = {}
    for reading in readings:
        latest.setdefault(reading.zone_id, reading)
    return latest


def count_active_incidents_by_zone(session: Session) -> dict[UUID, int]:
    rows = session.execute(
        select(Incident.zone_id, func.count(Incident.id))
        .where(Incident.status == "ACTIVE")
        .group_by(Incident.zone_id)
    )
    return {zone_id: count for zone_id, count in rows}


def count_active_incidents(session: Session) -> int:
    return session.scalar(
        select(func.count(Incident.id)).where(Incident.status == "ACTIVE")
    ) or 0


def list_active_incidents(session: Session, zone_id: UUID) -> list[Incident]:
    return list(
        session.scalars(
            select(Incident)
            .where(Incident.zone_id == zone_id, Incident.status == "ACTIVE")
            .order_by(Incident.created_at.desc(), Incident.id.desc())
        )
    )


def list_readings(
    session: Session, limit: int, zone_id: UUID | None = None
) -> list[tuple[SensorReading, str]]:
    statement = (
        select(SensorReading, Zone.name)
        .join(Zone, SensorReading.zone_id == Zone.id)
        .order_by(SensorReading.timestamp.desc(), SensorReading.id.desc())
        .limit(limit)
    )
    if zone_id is not None:
        statement = statement.where(SensorReading.zone_id == zone_id)
    return list(session.execute(statement))


def list_incidents(
    session: Session, active_only: bool, limit: int
) -> list[tuple[Incident, str]]:
    statement = (
        select(Incident, Zone.name)
        .join(Zone, Incident.zone_id == Zone.id)
        .order_by(Incident.created_at.desc(), Incident.id.desc())
        .limit(limit)
    )
    if active_only:
        statement = statement.where(Incident.status == "ACTIVE")
    return list(session.execute(statement))


def get_incident(session: Session, incident_id: UUID) -> tuple[Incident, str] | None:
    row = session.execute(
        select(Incident, Zone.name)
        .join(Zone, Incident.zone_id == Zone.id)
        .where(Incident.id == incident_id)
    ).first()
    return row