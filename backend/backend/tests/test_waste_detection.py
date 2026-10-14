from collections.abc import Generator
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db import engine, get_session
from app.main import app
from app.models import Zone
from app.waste_detection.api import get_waste_detector
from app.waste_detection.detectors import (
    MockWasteDetector,
    ObjectDetection,
    get_configured_detector,
)
from app.waste_detection.rules import calculate_waste_level

PNG_IMAGE = b"\x89PNG\r\n\x1a\n" + (b"\x00" * 32)


class FixedWasteDetector:
    model_name = "test-detector"
    is_mock = False

    def __init__(self, detection_count: int) -> None:
        self.detection_count = detection_count

    def detect(self, image: bytes) -> list[ObjectDetection]:
        assert image.startswith(b"\x89PNG")
        return [
            ObjectDetection(
                class_name="bottle",
                confidence=0.9,
                bounding_box=(float(index), 1.0, float(index + 10), 11.0),
            )
            for index in range(self.detection_count)
        ]


@pytest.fixture
def waste_client() -> Generator[tuple[TestClient, UUID], None, None]:
    with Session(engine) as lookup_session:
        zone_id = lookup_session.scalar(
            select(Zone.id).where(Zone.name == "Academic Block")
        )
    assert zone_id is not None

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
            yield client, zone_id
    finally:
        app.dependency_overrides.pop(get_session, None)
        transaction.rollback()
        connection.close()


def upload_image(client: TestClient, zone_id: UUID):
    return client.post(
        "/api/v1/waste-detections",
        data={"zone_id": str(zone_id)},
        files={"image": ("campus.png", PNG_IMAGE, "image/png")},
    )


def test_mock_detector_returns_structured_simulated_detections() -> None:
    detector = MockWasteDetector()

    detections = detector.detect(PNG_IMAGE)

    assert detector.is_mock is True
    assert detector.model_name == "mock-simulated"
    assert [detection.class_name for detection in detections] == ["bottle", "cup"]
    assert all(detection.confidence is not None for detection in detections)
    assert all(detection.bounding_box is None for detection in detections)


def test_unavailable_yolo_model_falls_back_to_mock(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    monkeypatch.setattr(settings, "waste_detector", "yolo")
    monkeypatch.setattr(settings, "waste_yolo_model_path", tmp_path / "missing.pt")
    get_configured_detector.cache_clear()

    detector = get_configured_detector()

    get_configured_detector.cache_clear()
    assert isinstance(detector, MockWasteDetector)
    assert detector.is_mock is True


@pytest.mark.parametrize(
    ("count", "expected"),
    [(0, "NONE"), (1, "LOW"), (2, "LOW"), (3, "MEDIUM"), (4, "MEDIUM"), (5, "HIGH")],
)
def test_waste_levels_are_deterministic(count: int, expected: str) -> None:
    detections = [ObjectDetection("bottle") for _ in range(count)]

    assert calculate_waste_level(detections, medium_threshold=3, high_threshold=5) == expected


def test_non_waste_detector_classes_are_not_counted_as_waste() -> None:
    detections = [ObjectDetection("person") for _ in range(8)]

    assert calculate_waste_level(detections, medium_threshold=3, high_threshold=5) == "NONE"


def test_image_upload_is_marked_mock_and_persisted(
    waste_client: tuple[TestClient, UUID],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    client, zone_id = waste_client
    monkeypatch.setattr(settings, "waste_image_storage_dir", tmp_path)

    response = upload_image(client, zone_id)

    assert response.status_code == 200
    result = response.json()
    assert result["waste_level"] == "LOW"
    assert result["is_mock"] is True
    assert result["model_name"] == "mock-simulated"
    assert [item["class_name"] for item in result["detected_objects"]] == [
        "bottle",
        "cup",
    ]
    assert (tmp_path / result["image_path"].rsplit("/", 1)[1]).is_file()

    list_response = client.get(f"/api/v1/waste-detections?zone_id={zone_id}")
    assert list_response.status_code == 200
    assert list_response.json()[0]["id"] == result["id"]
    assert result["detected_object_count"] == 2
    assert result["waste_object_count"] == 2

    summary_response = client.get("/api/v1/dashboard/summary")
    zone = next(
        zone for zone in summary_response.json()["zones"] if zone["id"] == str(zone_id)
    )
    assert zone["latest_waste_detection"]["id"] == result["id"]
    assert zone["latest_waste_detection"]["is_mock"] is True


def test_high_waste_creates_one_active_incident_and_updates_zone_status(
    waste_client: tuple[TestClient, UUID],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    client, zone_id = waste_client
    monkeypatch.setattr(settings, "waste_image_storage_dir", tmp_path)
    monkeypatch.setitem(
        app.dependency_overrides,
        get_waste_detector,
        lambda: FixedWasteDetector(5),
    )

    first_response = upload_image(client, zone_id)
    second_response = upload_image(client, zone_id)

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    first_result = first_response.json()
    second_result = second_response.json()
    assert first_result["waste_level"] == "HIGH"
    assert first_result["incident_created"] is True
    assert first_result["incident_updated"] is False
    assert second_result["incident_created"] is False
    assert second_result["incident_updated"] is True
    assert first_result["incident"]["id"] == second_result["incident"]["id"]
    assert second_result["zone_status"] == "WARNING"

    active_incidents_response = client.get("/api/v1/incidents?active_only=true&limit=100")
    zone_response = client.get(f"/api/v1/zones/{zone_id}")
    active_waste_incidents = [
        incident
        for incident in active_incidents_response.json()
        if incident["zone_id"] == str(zone_id)
        and incident["type"] == "WASTE_ACCUMULATION"
    ]
    zone = zone_response.json()
    assert len(active_waste_incidents) == 1
    assert zone["status"] == "WARNING"


def test_upload_rejects_non_image_content(
    waste_client: tuple[TestClient, UUID],
) -> None:
    client, zone_id = waste_client
    response = client.post(
        "/api/v1/waste-detections",
        data={"zone_id": str(zone_id)},
        files={"image": ("campus.png", b"not an image", "image/png")},
    )

    assert response.status_code == 415