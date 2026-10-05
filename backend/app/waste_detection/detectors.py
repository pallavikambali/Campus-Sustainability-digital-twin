import logging
from dataclasses import dataclass
from functools import lru_cache
from io import BytesIO
from pathlib import Path
from typing import Protocol

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ObjectDetection:
    class_name: str
    confidence: float | None = None
    bounding_box: tuple[float, float, float, float] | None = None


class WasteDetector(Protocol):
    model_name: str
    is_mock: bool

    def detect(self, image: bytes) -> list[ObjectDetection]: ...


class MockWasteDetector:
    model_name = "mock-simulated"
    is_mock = True

    def detect(self, image: bytes) -> list[ObjectDetection]:
        del image
        return [
            ObjectDetection("bottle", confidence=0.94),
            ObjectDetection("cup", confidence=0.89),
        ]


class UltralyticsWasteDetector:
    is_mock = False

    def __init__(self, model_path: Path) -> None:
        if not model_path.is_file():
            raise FileNotFoundError(f"YOLO weights not found: {model_path}")
        try:
            from ultralytics import YOLO  # type: ignore[import-not-found]
        except ImportError as error:
            raise RuntimeError(
                "Install the optional 'vision' extra to enable the YOLO adapter."
            ) from error

        self.model_name = f"yolo:{model_path.name}"
        self._model = YOLO(str(model_path))

    def detect(self, image: bytes) -> list[ObjectDetection]:
        try:
            from PIL import Image  # type: ignore[import-not-found]
        except ImportError as error:
            raise RuntimeError("Pillow is required by the optional YOLO adapter.") from error

        with Image.open(BytesIO(image)) as source:
            result = self._model.predict(source.convert("RGB"), verbose=False)[0]

        detections: list[ObjectDetection] = []
        for box in result.boxes:
            class_id = int(box.cls[0].item())
            coordinates = tuple(float(value) for value in box.xyxy[0].tolist())
            detections.append(
                ObjectDetection(
                    class_name=str(result.names[class_id]),
                    confidence=float(box.conf[0].item()),
                    bounding_box=coordinates,  # type: ignore[arg-type]
                )
            )
        return detections


@lru_cache(maxsize=1)
def get_configured_detector() -> WasteDetector:
    if settings.waste_detector.strip().lower() != "yolo":
        return MockWasteDetector()
    try:
        return UltralyticsWasteDetector(settings.waste_yolo_model_path)
    except Exception as error:
        logger.warning("YOLO unavailable; using mock detections: %s", error)
        return MockWasteDetector()