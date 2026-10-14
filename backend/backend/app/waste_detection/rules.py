from collections.abc import Iterable, Sequence
from typing import Literal

from app.waste_detection.detectors import ObjectDetection

WasteLevel = Literal["NONE", "LOW", "MEDIUM", "HIGH"]
WASTE_CANDIDATE_CLASSES = frozenset(
    {
        "bottle",
        "cup",
        "can",
        "plastic bag",
        "paper",
        "cardboard",
        "carton",
        "wrapper",
        "food waste",
    }
)


def count_waste_candidates(
    detections: Sequence[ObjectDetection],
    candidate_classes: Iterable[str] = WASTE_CANDIDATE_CLASSES,
) -> int:
    normalized_classes = {class_name.strip().casefold() for class_name in candidate_classes}
    return sum(
        detection.class_name.strip().casefold() in normalized_classes
        for detection in detections
    )


def calculate_waste_level(
    detections: Sequence[ObjectDetection],
    medium_threshold: int,
    high_threshold: int,
    candidate_classes: Iterable[str] = WASTE_CANDIDATE_CLASSES,
) -> WasteLevel:
    if medium_threshold < 1 or high_threshold <= medium_threshold:
        raise ValueError("Waste thresholds must satisfy 1 <= medium < high")

    detection_count = count_waste_candidates(detections, candidate_classes)
    if detection_count >= high_threshold:
        return "HIGH"
    if detection_count >= medium_threshold:
        return "MEDIUM"
    if detection_count > 0:
        return "LOW"
    return "NONE"