from dataclasses import dataclass
from decimal import Decimal
from typing import Literal
from uuid import UUID

from sqlalchemy.orm import Session

from app import repositories
from app.models import Incident, SensorReading, Zone
from app.schemas import IncidentResponse, SensorReadingResponse, SimulationResponse

Scenario = Literal["energy-spike", "water-leak", "occupancy-surge"]
SIMULATION_INCIDENT_TYPES = (
    "HIGH_ENERGY_CONSUMPTION",
    "POSSIBLE_WATER_LEAKAGE",
    "ABNORMAL_OCCUPANCY",
)


@dataclass(frozen=True)
class ZoneProfile:
    normal_energy_kwh: Decimal
    normal_water_liters: Decimal
    normal_occupancy: int

    @property
    def maximum_expected_energy_kwh(self) -> Decimal:
        return self.normal_energy_kwh * Decimal("1.5")

    @property
    def maximum_expected_water_liters(self) -> Decimal:
        return self.normal_water_liters * Decimal("1.5")


ZONE_PROFILES = {
    "Academic Block": ZoneProfile(Decimal("120.00"), Decimal("4200.00"), 180),
    "Library": ZoneProfile(Decimal("75.00"), Decimal("2400.00"), 90),
    "Canteen": ZoneProfile(Decimal("90.00"), Decimal("3000.00"), 120),
}


class ZoneNotFoundError(Exception):
    pass


class UnsupportedZoneError(Exception):
    pass


@dataclass(frozen=True)
class Anomaly:
    incident_type: str
    severity: str
    current_value: Decimal
    expected_range: str
    description: str


def _load_zone(session: Session, zone_id: UUID) -> tuple[Zone, ZoneProfile]:
    zone = repositories.get_zone_for_update(session, zone_id)
    if zone is None:
        raise ZoneNotFoundError
    profile = ZONE_PROFILES.get(zone.name)
    if profile is None:
        raise UnsupportedZoneError(zone.name)
    return zone, profile


def _reading_values(
    zone: Zone, profile: ZoneProfile, scenario: Scenario | None
) -> tuple[Decimal, Decimal, int]:
    energy_kwh = profile.normal_energy_kwh
    water_liters = profile.normal_water_liters
    occupancy = profile.normal_occupancy

    if scenario == "energy-spike":
        energy_kwh = profile.maximum_expected_energy_kwh * Decimal("2")
    elif scenario == "water-leak":
        water_liters = profile.maximum_expected_water_liters * Decimal("2")
    elif scenario == "occupancy-surge":
        occupancy = zone.capacity + max(10, (zone.capacity + 9) // 10)

    return energy_kwh, water_liters, occupancy


def _detect_anomalies(zone: Zone, profile: ZoneProfile, reading: SensorReading) -> list[Anomaly]:
    anomalies: list[Anomaly] = []

    if reading.energy_kwh > profile.maximum_expected_energy_kwh:
        anomalies.append(
            Anomaly(
                incident_type="HIGH_ENERGY_CONSUMPTION",
                severity="HIGH",
                current_value=reading.energy_kwh,
                expected_range=f"0-{profile.maximum_expected_energy_kwh:.2f} kWh per reading",
                description=(
                    f"Energy consumption in {zone.name} exceeded the expected range."
                ),
            )
        )

    occupancy_change = abs(reading.occupancy - profile.normal_occupancy)
    occupancy_is_stable = occupancy_change <= profile.normal_occupancy * 0.10
    if (
        reading.water_liters > profile.maximum_expected_water_liters
        and occupancy_is_stable
    ):
        anomalies.append(
            Anomaly(
                incident_type="POSSIBLE_WATER_LEAKAGE",
                severity="HIGH",
                current_value=reading.water_liters,
                expected_range=(
                    f"<= {profile.maximum_expected_water_liters:.2f} L per reading; "
                    f"occupancy within 10% of {profile.normal_occupancy}"
                ),
                description=(
                    f"Water consumption in {zone.name} was high while occupancy remained stable."
                ),
            )
        )

    if reading.occupancy > zone.capacity:
        anomalies.append(
            Anomaly(
                incident_type="ABNORMAL_OCCUPANCY",
                severity="CRITICAL",
                current_value=Decimal(reading.occupancy),
                expected_range=f"0-{zone.capacity} occupants",
                description=(
                    f"Occupancy in {zone.name} exceeded its capacity of {zone.capacity}."
                ),
            )
        )

    return anomalies


def recalculate_zone_status(session: Session, zone: Zone) -> list[Incident]:
    active_incidents = repositories.list_active_incidents(session, zone.id)
    serious_incidents = sum(
        incident.severity in {"HIGH", "CRITICAL"} for incident in active_incidents
    )
    has_critical_incident = any(
        incident.severity == "CRITICAL" for incident in active_incidents
    )
    if has_critical_incident or serious_incidents >= 2:
        zone.status = "CRITICAL"
    elif active_incidents:
        zone.status = "WARNING"
    else:
        zone.status = "NORMAL"
    session.flush()
    return active_incidents


def _response(
    zone: Zone, reading: SensorReading, incidents: list[Incident]
) -> SimulationResponse:
    return SimulationResponse(
        zone_id=zone.id,
        zone_name=zone.name,
        zone_status=zone.status,
        reading=SensorReadingResponse.model_validate(reading),
        incidents=[IncidentResponse.model_validate(incident) for incident in incidents],
    )


def simulate(
    session: Session, zone_id: UUID, scenario: Scenario
) -> SimulationResponse:
    zone, profile = _load_zone(session, zone_id)
    reading = repositories.create_sensor_reading(
        session, zone.id, *_reading_values(zone, profile, scenario)
    )

    detected_incidents = [
        repositories.upsert_active_incident(
            session,
            zone.id,
            anomaly.incident_type,
            anomaly.severity,
            anomaly.current_value,
            anomaly.expected_range,
            anomaly.description,
        )
        for anomaly in _detect_anomalies(zone, profile, reading)
    ]
    recalculate_zone_status(session, zone)
    return _response(zone, reading, detected_incidents)


def reset_zone(session: Session, zone_id: UUID) -> SimulationResponse:
    zone, profile = _load_zone(session, zone_id)
    reading = repositories.create_sensor_reading(
        session, zone.id, *_reading_values(zone, profile, None)
    )
    repositories.resolve_simulation_incidents(
        session, zone.id, SIMULATION_INCIDENT_TYPES
    )
    active_incidents = recalculate_zone_status(session, zone)
    return _response(zone, reading, active_incidents)