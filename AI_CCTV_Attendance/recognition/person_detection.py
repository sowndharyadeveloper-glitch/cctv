import json
from typing import Dict, List

import cv2


_person_detector = cv2.HOGDescriptor()
_person_detector.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())


def detect_people(frame) -> List[Dict[str, object]]:
    """Return HOG person boxes. Replace this adapter with a trained model in production."""
    boxes, weights = _person_detector.detectMultiScale(frame, winStride=(8, 8), padding=(8, 8), scale=1.05)
    detections = []
    for (x, y, width, height), weight in zip(boxes, weights):
        detections.append({
            "x": int(x), "y": int(y), "width": int(width), "height": int(height),
            "confidence": round(float(weight) * 100, 2),
        })
    return detections


def detect_people_in_zones(frame, zones: List[Dict[str, object]]) -> Dict[str, object]:
    detections = detect_people(frame)
    intrusions = []
    for index, detection in enumerate(detections, start=1):
        center = (detection["x"] + detection["width"] // 2, detection["y"] + detection["height"])
        for zone in zones:
            try:
                points = json.loads(zone["geometry_json"])
                polygon = [(int(point["x"]), int(point["y"])) for point in points]
            except (KeyError, TypeError, ValueError, json.JSONDecodeError):
                continue
            if len(polygon) >= 3 and cv2.pointPolygonTest(polygon, center, False) >= 0:
                intrusions.append({
                    "zone_id": zone["id"],
                    "zone_name": zone["name"],
                    "severity": zone["severity"],
                    "tracking_id": f"FRAME-PERSON-{index}",
                    "confidence": detection["confidence"],
                })
    return {"detections": detections, "intrusions": intrusions}
