import pytest
from fastapi.testclient import TestClient
from sqlalchemy import inspect, select
from sqlalchemy.exc import IntegrityError, ProgrammingError
from sqlalchemy.orm import Session

from app.db import engine
from app.main import app
from app.models import SensorReading, Zone

client = TestClient(app)


def test_health_endpoint_confirms_database_connection() -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "connected"}


def test_initial_schema_and_seeded_zones() -> None:
    expected_tables = {
        "alembic_version",
        "zones",
        "sensor_readings",
        "incidents",
        "waste_detections",
        "recommendations",
        "reports",
    }
    assert expected_tables.issubset(set(inspect(engine).get_table_names()))

    with Session(engine) as session:
        zone_names = set(session.scalars(select(Zone.name)))

    assert {"Academic Block", "Library", "Canteen"}.issubset(zone_names)


def test_sensor_reading_rejects_negative_values() -> None:
    with Session(engine) as session:
        zone_id = session.scalar(select(Zone.id).where(Zone.name == "Academic Block"))
        assert zone_id is not None
        session.add(
            SensorReading(
                zone_id=zone_id,
                energy_kwh=-1,
                water_liters=100,
                occupancy=10,
            )
        )
        with pytest.raises((IntegrityError, ProgrammingError)):
            session.flush()
