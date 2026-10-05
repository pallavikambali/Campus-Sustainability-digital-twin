from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class SensorReadingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    zone_id: UUID
    timestamp: datetime
    energy_kwh: Decimal
    water_liters: Decimal
    occupancy: int


class IncidentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    zone_id: UUID
    type: str
    severity: str
    current_value: Decimal | None
    expected_range: str | None
    description: str
    status: str
    source: str
    created_at: datetime
    resolved_at: datetime | None


class SimulationResponse(BaseModel):
    zone_id: UUID
    zone_name: str
    zone_status: str
    reading: SensorReadingResponse
    incidents: list[IncidentResponse]


class ReadingListItemResponse(SensorReadingResponse):
    zone_name: str


class IncidentListItemResponse(IncidentResponse):
    zone_name: str


class DetectedObjectResponse(BaseModel):
    class_name: str
    confidence: float | None = None
    bounding_box: dict[str, float] | None = None


class LatestWasteDetectionResponse(BaseModel):
    id: UUID
    waste_level: str
    waste_object_count: int
    detected_object_count: int
    model_name: str
    is_mock: bool
    created_at: datetime


class ZoneSummaryResponse(BaseModel):
    id: UUID
    name: str
    type: str
    capacity: int
    status: str
    active_incident_count: int
    latest_reading: SensorReadingResponse | None
    latest_waste_detection: LatestWasteDetectionResponse | None = None


class ZoneDetailResponse(ZoneSummaryResponse):
    active_incidents: list[IncidentResponse]


class DashboardSummaryResponse(BaseModel):
    total_zones: int
    normal_zones: int
    warning_zones: int
    critical_zones: int
    active_incidents: int
    zones: list[ZoneSummaryResponse]

class WasteDetectionRecordResponse(BaseModel):
    id: UUID
    zone_id: UUID
    image_path: str | None
    detected_objects: list[DetectedObjectResponse]
    detected_object_count: int
    waste_level: str
    waste_object_count: int
    model_name: str
    is_mock: bool
    created_at: datetime

class WasteDetectionListItemResponse(WasteDetectionRecordResponse):
    zone_name: str

class WasteDetectionResultResponse(WasteDetectionRecordResponse):
    zone_status: str
    incident_created: bool
    incident_updated: bool
    incident: IncidentResponse | None