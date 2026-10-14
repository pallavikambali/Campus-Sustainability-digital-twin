from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db import get_session
from app.notifications import notify_critical_zone
from app.schemas import WasteDetectionListItemResponse, WasteDetectionResultResponse
from app.services import ZoneNotFoundError
from app.waste_detection import repository
from app.waste_detection.detectors import WasteDetector, get_configured_detector
from app.waste_detection.service import analyze_waste_image, waste_detection_response

router = APIRouter(prefix="/api/v1/waste-detections", tags=["computer-vision"])
MAX_IMAGE_BYTES = settings.waste_max_upload_bytes
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}


def get_waste_detector() -> WasteDetector:
    return get_configured_detector()


def _image_extension(image: bytes) -> str | None:
    if image.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if image.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if len(image) >= 12 and image[:4] == b"RIFF" and image[8:12] == b"WEBP":
        return "webp"
    return None


@router.post("", response_model=WasteDetectionResultResponse)
def create_waste_detection(
    zone_id: UUID = Form(...),
    image: UploadFile = File(...),
    session: Session = Depends(get_session),
    detector: WasteDetector = Depends(get_waste_detector),
) -> WasteDetectionResultResponse:
    if image.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=415, detail="Upload a JPEG, PNG, or WebP image")
    contents = image.file.read(MAX_IMAGE_BYTES + 1)
    if len(contents) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="Image exceeds the 10 MB upload limit")
    extension = _image_extension(contents)
    if extension is None:
        raise HTTPException(status_code=415, detail="Uploaded file is not a supported image")

    try:
        with session.begin():
            result = analyze_waste_image(
                session, zone_id, contents, extension, detector=detector
            )
        if result.zone_status == "CRITICAL":
            notify_critical_zone(session, zone_id)
        return result
    except ZoneNotFoundError as error:
        raise HTTPException(status_code=404, detail="Zone not found") from error


@router.get("", response_model=list[WasteDetectionListItemResponse])
def list_waste_detections(
    zone_id: UUID | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    session: Session = Depends(get_session),
) -> list[WasteDetectionListItemResponse]:
    return [
        WasteDetectionListItemResponse.model_validate(
            waste_detection_response(detection, zone_name)
        )
        for detection, zone_name in repository.list_waste_detections(
            session, limit, zone_id
        )
    ]