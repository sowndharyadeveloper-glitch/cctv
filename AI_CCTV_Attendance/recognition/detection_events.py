from typing import Dict, List


DEMO_EVENTS: List[Dict[str, object]] = [
    {
        "alert_type": "RESTRICTED_AREA_INTRUSION",
        "severity": "CRITICAL",
        "zone_id": "HIGH-VOLTAGE-ROOM",
        "tracking_id": "DEMO-TRACK-01",
        "confidence": 94.0,
        "description": "Simulated person entered a restricted high-voltage area.",
    },
    {
        "alert_type": "PPE_VIOLATION",
        "severity": "HIGH",
        "zone_id": "WELDING-AREA",
        "tracking_id": "DEMO-TRACK-02",
        "confidence": 91.0,
        "description": "Simulated person is missing helmet and gloves in a PPE-required zone.",
    },
    {
        "alert_type": "HAZARD_EVENT",
        "severity": "MEDIUM",
        "zone_id": "LOADING-BAY",
        "tracking_id": "DEMO-TRACK-03",
        "confidence": 87.0,
        "description": "Simulated unsafe proximity event near the loading bay.",
    },
]


def demo_detection(camera_id: int | None = None) -> Dict[str, object]:
    event = DEMO_EVENTS[0]
    return {**event, "camera_id": camera_id, "simulated": True}