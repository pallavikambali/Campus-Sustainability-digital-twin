from collections.abc import Generator
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import engine, get_session
from app.main import app
from app.models import Zone


@pytest.fixture
def read_api_client() -> Generator[tuple[TestClient, dict[str, UUID]], None, None]:
    with Session(engine) as lookup_session:
        zone_ids = dict(lookup_session.execute(select(Zone.name, Zone.id)).all())

    connection = engine.connect()
    transaction = connection.begin()

    def override_get_session() -> Generator[Session, None, None]:
        with Session(
            bind=connection,
            join_transaction_mode="create_savepoint",
        ) as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    try:
        with TestClient(app) as client:
            yield client, zone_ids
    finally:
        app.dependency_overrides.pop(get_session, None)
        transaction.rollback()
        connection.close()


def test_zone_and_summary_endpoints_return_database_zones(
    read_api_client: tuple[TestClient, dict[str, UUID]],
) -> None:
    client, zone_ids = read_api_client

    zones_response = client.get("/api/v1/zones")
    summary_response = client.get("/api/v1/dashboard/summary")

    assert zones_response.status_code == 200
    assert {zone["name"] for zone in zones_response.json()} == set(zone_ids)
    summary = summary_response.json()
    assert summary["total_zones"] == 3
    assert (
        summary["normal_zones"] + summary["warning_zones"] + summary["critical_zones"]
        == 3
    )
    assert {zone["name"] for zone in summary["zones"]} == set(zone_ids)


def test_zone_detail_and_unknown_zone(
    read_api_client: tuple[TestClient, dict[str, UUID]],
) -> None:
    client, zone_ids = read_api_client

    response = client.get(f"/api/v1/zones/{zone_ids['Library']}")
    missing_response = client.get("/api/v1/zones/00000000-0000-4000-8000-000000000099")

    assert response.status_code == 200
    assert response.json()["name"] == "Library"
    assert response.json()["capacity"] == 150
    assert "active_incidents" in response.json()
    assert missing_response.status_code == 404


def test_readings_and_incidents_reflect_simulation_writes(
    read_api_client: tuple[TestClient, dict[str, UUID]],
) -> None:
    client, zone_ids = read_api_client
    zone_id = zone_ids["Academic Block"]

    simulation_response = client.post(f"/api/v1/simulation/{zone_id}/energy-spike")
    readings_response = client.get(f"/api/v1/readings?zone_id={zone_id}&limit=5")
    incidents_response = client.get("/api/v1/incidents")

    assert simulation_response.status_code == 200
    assert readings_response.status_code == 200
    readings = readings_response.json()
    assert readings[0]["zone_name"] == "Academic Block"
    assert readings[0]["energy_kwh"] == "360.00"
    assert incidents_response.status_code == 200
    incident = next(
        item
        for item in incidents_response.json()
        if item["zone_id"] == str(zone_id)
    )
    assert incident["type"] == "HIGH_ENERGY_CONSUMPTION"
    assert incident["zone_name"] == "Academic Block"

    detail_response = client.get(f"/api/v1/incidents/{incident['id']}")
    assert detail_response.status_code == 200
    assert detail_response.json()["id"] == incident["id"]