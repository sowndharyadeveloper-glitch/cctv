import cv2
import numpy as np
from config import DETECTION_THRESHOLD


def inspect_roi(roi: np.ndarray) -> tuple[str, str | None, float]:
    """Baseline inspection: use edge irregularity as a transparent heuristic.

    This is not a trained defect classifier. A production model can replace this
    function without changing the database or web layer.
    """
    if roi is None or roi.size == 0:
        return "UNKNOWN", None, 0.0
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(cv2.GaussianBlur(gray, (5, 5), 0), 60, 140)
    edge_ratio = float(np.count_nonzero(edges)) / edges.size
    confidence = min(1.0, abs(edge_ratio - DETECTION_THRESHOLD) / max(DETECTION_THRESHOLD, 0.001) + 0.55)
    if edge_ratio < DETECTION_THRESHOLD:
        return "FAIL", "Missing Component", confidence
    if edge_ratio > 0.32:
        return "FAIL", "Surface Defect", min(confidence, 0.99)
    return "PASS", None, min(confidence, 0.99)
