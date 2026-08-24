from datetime import datetime
from pathlib import Path
import cv2
import numpy as np
from config import CAPTURED_DIR, SAVE_PASS_IMAGES
from database.db import get_db, now_iso


def save_image(frame: np.ndarray, result: str) -> str | None:
    if result == "PASS" and not SAVE_PASS_IMAGES:
        return None
    folder = CAPTURED_DIR / ("fail" if result == "FAIL" else "pass")
    folder.mkdir(parents=True, exist_ok=True)
    filename = f"inspection_{datetime.now():%Y%m%d_%H%M%S_%f}.jpg"
    path = folder / filename
    if not cv2.imwrite(str(path), frame):
        raise OSError("Could not save inspection image")
    return str(path.relative_to(CAPTURED_DIR.parent))


def save_inspection(result, camera_id: str, product_id: str | None, frame: np.ndarray, is_demo: bool = False) -> int:
    image_path = save_image(frame, result.result)
    with get_db() as db:
        cursor = db.execute("""INSERT INTO inspections
            (inspection_time, product_id, camera_id, result, defect_type, confidence, image_path, processing_time, is_demo, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", (now_iso(), product_id, camera_id, result.result,
            result.defect_type, result.confidence, image_path, result.processing_time, int(is_demo), now_iso()))
        if result.defect_type and result.result == "FAIL":
            db.execute("""INSERT INTO defect_summary(defect_type, count, last_detected) VALUES (?, 1, ?)
                       ON CONFLICT(defect_type) DO UPDATE SET count = count + 1, last_detected = excluded.last_detected""",
                       (result.defect_type, now_iso()))
        return cursor.lastrowid
