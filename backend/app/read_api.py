from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app import read_repository
from app.core.config import settings
from app.db import get_session
from app.models import Incident, SensorReading, WasteDetection, Zone
from app.schemas import (
    DashboardSummaryResponse,
    IncidentListItemResponse,
    IncidentResponse,
    LatestWasteDetectionResponse,
    ReadingListItemResponse,
    ZoneDetailResponse,
    ZoneSummaryResponse,
)
from app.waste_detection import repository as waste_repository
from app.waste_detection.detectors import ObjectDetection
from app.waste_detection.rules import count_waste_candidates

router = APIRouter(tags=["dashboard"])


def _zone_summary(
    zone: Zone,
    latest_reading: SensorReading | None,
    active_incident_count: int,
    latest_waste_detection: WasteDetection | None,
) -> ZoneSummaryResponse:
    return ZoneSummaryResponse(
        id=zone.id,
        name=zone.name,
        type=zone.type,
        capacity=zone.capacity,
        status=zone.status,
        active_incident_count=active_incident_count,
        latest_reading=(
            None
            if latest_reading is None
            else ReadingListItemResponse.model_validate(
                {**latest_reading.__dict__, "zone_name": zone.name}
            )
        ),
        latest_waste_detection=(
            None
            if latest_waste_detection is None
            else LatestWasteDetectionResponse(
                id=latest_waste_detection.id,
                waste_level=latest_waste_detection.waste_level,
                detected_object_count=len(latest_waste_detection.detected_objects),
                waste_object_count=count_waste_candidates(
                    [
                        ObjectDetection(class_name=item["class_name"])
                        for item in latest_waste_detection.detected_objects
                    ],
                    settings.waste_candidate_classes.split(","),
                ),
                model_name=latest_waste_detection.model_name,
                is_mock=latest_waste_detection.model_name.startswith("mock"),
                created_at=latest_waste_detection.created_at,
            )
        ),
    )


def _zone_summaries(session: Session) -> list[ZoneSummaryResponse]:
    zones = read_repository.list_zones(session)
    latest_readings = read_repository.list_latest_readings(session)
    incident_counts = read_repository.count_active_incidents_by_zone(session)
    latest_waste_detections = waste_repository.get_latest_by_zone(session)

    return [
        _zone_summary(
            zone,
            latest_readings.get(zone.id),
            incident_counts.get(zone.id, 0),
            latest_waste_detections.get(zone.id),
        )
        for zone in zones
    ]
    
def _incident_response(
    incident: Incident,
    zone_name: str,
) -> IncidentListItemResponse:
    return IncidentListItemResponse.model_validate(
        {**incident.__dict__, "zone_name": zone_name}
    )

@router.get("/api/v1/zones", response_model=list[ZoneSummaryResponse])
def get_zones(session: Session = Depends(get_session)) -> list[ZoneSummaryResponse]:
    return _zone_summaries(session)


@router.get("/api/v1/zones/{zone_id}", response_model=ZoneDetailResponse)
def get_zone(
    zone_id: UUID, session: Session = Depends(get_session)
) -> ZoneDetailResponse:
    zone = read_repository.get_zone(session, zone_id)
    if zone is None:
        raise HTTPException(status_code=404, detail="Zone not found")

    latest_reading = read_repository.list_latest_readings(session).get(zone.id)
    incident_count = read_repository.count_active_incidents_by_zone(session).get(zone.id, 0)
    latest_waste_detection = waste_repository.get_latest_by_zone(session).get(zone.id)
    return ZoneDetailResponse(
        **_zone_summary(
            zone, latest_reading, incident_count, latest_waste_detection
        ).model_dump(),
        active_incidents=[
            IncidentResponse.model_validate(incident)
            for incident in read_repository.list_active_incidents(session, zone.id)
        ],
    )


@router.get("/api/v1/dashboard/summary", response_model=DashboardSummaryResponse)
def get_dashboard_summary(
    session: Session = Depends(get_session),
) -> DashboardSummaryResponse:
    zones = _zone_summaries(session)
    return DashboardSummaryResponse(
        total_zones=len(zones),
        normal_zones=sum(zone.status == "NORMAL" for zone in zones),
        warning_zones=sum(zone.status == "WARNING" for zone in zones),
        critical_zones=sum(zone.status == "CRITICAL" for zone in zones),
        active_incidents=read_repository.count_active_incidents(session),
        zones=zones,
    )


@router.get("/api/v1/readings", response_model=list[ReadingListItemResponse])
def get_readings(
    zone_id: UUID | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    session: Session = Depends(get_session),
) -> list[ReadingListItemResponse]:
    return [
        ReadingListItemResponse.model_validate(
            {**reading.__dict__, "zone_name": zone_name}
        )
        for reading, zone_name in read_repository.list_readings(session, limit, zone_id)
    ]


@router.get("/api/v1/incidents", response_model=list[IncidentListItemResponse])
def get_incidents(
    active_only: bool = True,
    limit: int = Query(default=50, ge=1, le=200),
    session: Session = Depends(get_session),
) -> list[IncidentListItemResponse]:
    return [
        _incident_response(incident, zone_name)
        for incident, zone_name in read_repository.list_incidents(
            session, active_only, limit
        )
    ]


@router.get("/api/v1/incidents/{incident_id}", response_model=IncidentListItemResponse)
def get_incident(
    incident_id: UUID, session: Session = Depends(get_session)
) -> IncidentListItemResponse:
    result = read_repository.get_incident(session, incident_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    incident, zone_name = result
    return _incident_response(incident, zone_name)

