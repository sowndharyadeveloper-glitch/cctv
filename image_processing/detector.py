import cv2
import numpy as np
from image_processing.preprocessing import gray_edges


def detect_product(frame: np.ndarray) -> tuple[tuple[int, int, int, int] | None, float]:
    """Find the largest non-trivial contour as the inspection workpiece ROI."""
    edges = gray_edges(frame)
    edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None, 0.0
    contour = max(contours, key=cv2.contourArea)
    area = cv2.contourArea(contour)
    frame_area = frame.shape[0] * frame.shape[1]
    if area < frame_area * 0.01:
        return None, 0.0
    x, y, width, height = cv2.boundingRect(contour)
    return (x, y, width, height), min(area / frame_area * 4, 1.0)
