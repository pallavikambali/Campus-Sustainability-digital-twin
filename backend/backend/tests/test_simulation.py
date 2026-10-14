from collections.abc import Generator
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import engine, get_session
from app.main import app
from app.models import Incident, Zone


@pytest.fixture
def simulation_client() -> Generator[tuple[TestClient, Session, dict[str, UUID]], None, None]:
    with Session(engine) as lookup_session:
        zone_ids = dict(lookup_session.execute(select(Zone.name, Zone.id)).all())
    assert {"Academic Block", "Library", "Canteen"}.issubset(zone_ids)

    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")

    def override_get_session() -> Generator[Session, None, None]:
        yield session

    app.dependency_overrides[get_session] = override_get_session
    try:
        with TestClient(app) as client:
            yield client, session, zone_ids
    finally:
        app.dependency_overrides.pop(get_session, None)
        session.close()
        transaction.rollback()
        connection.close()


def test_energy_spike_creates_high_energy_incident(
    simulation_client: tuple[TestClient, Session, dict[str, UUID]],
) -> None:
    client, _, zone_ids = simulation_client
    zone_id = zone_ids["Academic Block"]

    response = client.post(f"/api/v1/simulation/{zone_id}/energy-spike")

    assert response.status_code == 200
    payload = response.json()
    assert payload["reading"]["energy_kwh"] == "360.00"
    assert payload["zone_status"] == "WARNING"
    assert [incident["type"] for incident in payload["incidents"]] == [
        "HIGH_ENERGY_CONSUMPTION"
    ]


def test_water_leak_with_stable_occupancy_creates_incident(
    simulation_client: tuple[TestClient, Session, dict[str, UUID]],
) -> None:
    client, _, zone_ids = simulation_client
    zone_id = zone_ids["Academic Block"]

    response = client.post(f"/api/v1/simulation/{zone_id}/water-leak")

    assert response.status_code == 200
    payload = response.json()
    assert payload["reading"]["water_liters"] == "12600.00"
    assert payload["reading"]["occupancy"] == 180
    assert [incident["type"] for incident in payload["incidents"]] == [
        "POSSIBLE_WATER_LEAKAGE"
    ]


def test_occupancy_surge_above_capacity_creates_incident(
    simulation_client: tuple[TestClient, Session, dict[str, UUID]],
) -> None:
    client, _, zone_ids = simulation_client
    zone_id = zone_ids["Academic Block"]

    response = client.post(f"/api/v1/simulation/{zone_id}/occupancy-surge")

    assert response.status_code == 200
    payload = response.json()
    assert payload["reading"]["occupancy"] == 330
    assert payload["zone_status"] == "CRITICAL"
    assert [incident["type"] for incident in payload["incidents"]] == [
        "ABNORMAL_OCCUPANCY"
    ]


def test_reset_returns_zone_to_normal(
    simulation_client: tuple[TestClient, Session, dict[str, UUID]],
) -> None:
    client, session, zone_ids = simulation_client
    zone_id = zone_ids["Academic Block"]
    client.post(f"/api/v1/simulation/{zone_id}/energy-spike")

    response = client.post(f"/api/v1/simulation/{zone_id}/reset")

    assert response.status_code == 200
    payload = response.json()
    assert payload["zone_status"] == "NORMAL"
    assert payload["reading"]["energy_kwh"] == "120.00"
    assert payload["incidents"] == []
    active_incidents = session.scalars(
        select(Incident).where(
            Incident.zone_id == zone_id,
            Incident.status == "ACTIVE",
        )
    )
    assert list(active_incidents) == []


def test_repeated_scenario_updates_existing_active_incident(
    simulation_client: tuple[TestClient, Session, dict[str, UUID]],
) -> None:
    client, session, zone_ids = simulation_client
    zone_id = zone_ids["Academic Block"]
    endpoint = f"/api/v1/simulation/{zone_id}/energy-spike"

    first_response = client.post(endpoint)
    first_incident_id = first_response.json()["incidents"][0]["id"]
    second_response = client.post(endpoint)
    second_incident_id = second_response.json()["incidents"][0]["id"]

    active_incidents = list(
        session.scalars(
            select(Incident).where(
                Incident.zone_id == zone_id,
                Incident.type == "HIGH_ENERGY_CONSUMPTION",
                Incident.status == "ACTIVE",
            )
        )
    )
    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert second_incident_id == first_incident_id
    assert len(active_incidents) == 1


@pytest.mark.parametrize(
    ("zone_name", "expected_energy"),
    [
        ("Academic Block", "360.00"),
        ("Library", "225.00"),
        ("Canteen", "270.00"),
    ],
)
def test_energy_scenarios_are_deterministic_for_each_zone(
    simulation_client: tuple[TestClient, Session, dict[str, UUID]],
    zone_name: str,
    expected_energy: str,
) -> None:
    client, _, zone_ids = simulation_client

    response = client.post(f"/api/v1/simulation/{zone_ids[zone_name]}/energy-spike")

    assert response.status_code == 200
    assert response.json()["reading"]["energy_kwh"] == expected_energy