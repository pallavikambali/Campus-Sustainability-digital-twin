from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Incident, SensorReading, Zone


def get_zone_for_update(session: Session, zone_id: UUID) -> Zone | None:
    return session.scalar(select(Zone).where(Zone.id == zone_id).with_for_update())


def create_sensor_reading(
    session: Session,
    zone_id: UUID,
    energy_kwh: Decimal,
    water_liters: Decimal,
    occupancy: int,
) -> SensorReading:
    reading = SensorReading(
        zone_id=zone_id,
        energy_kwh=energy_kwh,
        water_liters=water_liters,
        occupancy=occupancy,
    )
    session.add(reading)
    session.flush()
    session.refresh(reading)
    return reading


def upsert_active_incident(
    session: Session,
    zone_id: UUID,
    incident_type: str,
    severity: str,
    current_value: Decimal,
    expected_range: str,
    description: str,
) -> Incident:
    incident = session.scalar(
        select(Incident)
        .where(
            Incident.zone_id == zone_id,
            Incident.type == incident_type,
            Incident.status == "ACTIVE",
        )
        .order_by(Incident.created_at.desc())
        .limit(1)
        .with_for_update()
    )
    is_new = incident is None
    if incident is None:
        incident = Incident(
            zone_id=zone_id,
            type=incident_type,
            severity=severity,
            current_value=current_value,
            expected_range=expected_range,
            description=description,
            status="ACTIVE",
            source="RULE",
        )
        session.add(incident)
    else:
        incident.severity = severity
        incident.current_value = current_value
        incident.expected_range = expected_range
        incident.description = description

    session.flush()
    if is_new:
        session.refresh(incident)
    return incident


def list_active_incidents(session: Session, zone_id: UUID) -> list[Incident]:
    return list(
        session.scalars(
            select(Incident)
            .where(Incident.zone_id == zone_id, Incident.status == "ACTIVE")
            .order_by(Incident.created_at, Incident.id)
        )
    )


def resolve_simulation_incidents(
    session: Session, zone_id: UUID, incident_types: tuple[str, ...]
) -> None:
    incidents = session.scalars(
        select(Incident).where(
            Incident.zone_id == zone_id,
            Incident.type.in_(incident_types),
            Incident.status == "ACTIVE",
        )
    )
    resolved_at = datetime.now(UTC)
    for incident in incidents:
        incident.status = "RESOLVED"
        incident.resolved_at = resolved_at