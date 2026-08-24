import time
from dataclasses import dataclass
import cv2
import numpy as np
from image_processing.detector import detect_product
from image_processing.defect_detection import inspect_roi


@dataclass
class InspectionResult:
	result: str
	defect_type: str | None
	confidence: float
	processing_time: float
	box: tuple[int, int, int, int] | None


def inspect_frame(frame: np.ndarray) -> InspectionResult:
	started = time.perf_counter()
	box, detection_confidence = detect_product(frame)
	if box is None:
		return InspectionResult("UNKNOWN", "Other", detection_confidence, time.perf_counter() - started, None)
	x, y, width, height = box
	result, defect, confidence = inspect_roi(frame[y:y + height, x:x + width])
	return InspectionResult(result, defect, min(confidence, detection_confidence or confidence), time.perf_counter() - started, box)
from image_processing.inspection import *  # noqa: F401,F403
