from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app import repositories
from app.core.config import settings
from app.models import Incident, WasteDetection, Zone
from app.schemas import (
    DetectedObjectResponse,
    IncidentResponse,
    WasteDetectionResultResponse,
)
from app.services import ZoneNotFoundError, recalculate_zone_status
from app.waste_detection import repository
from app.waste_detection.detectors import (
    ObjectDetection,
    WasteDetector,
    get_configured_detector,
)
from app.waste_detection.rules import calculate_waste_level, count_waste_candidates
from app.waste_detection.storage import LocalImageStorage


def _detection_records(
    detections: list[ObjectDetection],
) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for detection in detections:
        bounding_box = detection.bounding_box
        record: dict[str, object] = {
            "class_name": detection.class_name,
            "confidence": detection.confidence,
            "bounding_box": (
                None
                if bounding_box is None
                else dict(zip(("x1", "y1", "x2", "y2"), bounding_box, strict=True))
            ),
        }
        records.append(record)
    return records


def _stored_response(
    detection: WasteDetection,
    zone: Zone,
    incident: Incident | None,
    incident_created: bool,
    incident_updated: bool,
) -> WasteDetectionResultResponse:
    return WasteDetectionResultResponse(
        id=detection.id,
        zone_id=detection.zone_id,
        image_path=detection.image_path,
        detected_objects=[
            DetectedObjectResponse.model_validate(item)
            for item in detection.detected_objects
        ],
        detected_object_count=len(detection.detected_objects),
        waste_level=detection.waste_level,
        waste_object_count=count_waste_candidates(
            [
                ObjectDetection(class_name=item["class_name"])
                for item in detection.detected_objects
            ],
            settings.waste_candidate_classes.split(","),
        ),
        model_name=detection.model_name,
        is_mock=detection.model_name.startswith("mock"),
        created_at=detection.created_at,
        zone_status=zone.status,
        incident_created=incident_created,
        incident_updated=incident_updated,
        incident=None if incident is None else IncidentResponse.model_validate(incident),
    )


def analyze_waste_image(
    session: Session,
    zone_id: UUID,
    image: bytes,
    extension: str,
    detector: WasteDetector | None = None,
    storage: LocalImageStorage | None = None,
) -> WasteDetectionResultResponse:
    zone = repositories.get_zone_for_update(session, zone_id)
    if zone is None:
        raise ZoneNotFoundError

    active_detector = detector or get_configured_detector()
    image_storage = storage or LocalImageStorage()
    image_path = image_storage.save(image, extension)
    try:
        detections = active_detector.detect(image)
        waste_level = calculate_waste_level(
            detections,
            settings.waste_medium_object_threshold,
            settings.waste_high_object_threshold,
            settings.waste_candidate_classes.split(","),
        )
        waste_object_count = count_waste_candidates(
            detections, settings.waste_candidate_classes.split(",")
        )
        incident = None
        incident_created = False
        incident_updated = False
        if waste_level == "HIGH":
            existing_incident = repository.get_active_waste_incident(session, zone.id)
            incident_created = existing_incident is None
            incident_updated = existing_incident is not None
            incident = repositories.upsert_active_incident(
                session,
                zone.id,
                "WASTE_ACCUMULATION",
                "HIGH",
                Decimal(waste_object_count),
                f"HIGH at >= {settings.waste_high_object_threshold} waste objects",
                (
                    f"High waste level detected in {zone.name}: "
                    f"{waste_object_count} waste objects identified by "
                    f"{active_detector.model_name}."
                ),
            )

        record = repository.create_waste_detection(
            session,
            zone.id,
            image_path,
            _detection_records(detections),
            waste_level,
            active_detector.model_name,
        )
        recalculate_zone_status(session, zone)
        return _stored_response(
            record,
            zone,
            incident,
            incident_created,
            incident_updated,
        )
    except Exception:
        image_storage.delete(image_path)
        raise


def waste_detection_response(
    detection: WasteDetection, zone_name: str
) -> dict[str, object]:
    objects = [
        ObjectDetection(class_name=item["class_name"])
        for item in detection.detected_objects
    ]
    return {
        "id": detection.id,
        "zone_id": detection.zone_id,
        "zone_name": zone_name,
        "image_path": detection.image_path,
        "detected_objects": detection.detected_objects,
        "detected_object_count": len(detection.detected_objects),
        "waste_level": detection.waste_level,
        "waste_object_count": count_waste_candidates(
            objects, settings.waste_candidate_classes.split(",")
        ),
        "model_name": detection.model_name,
        "is_mock": detection.model_name.startswith("mock"),
        "created_at": detection.created_at,
    }