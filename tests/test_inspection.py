from datetime import date
from types import SimpleNamespace

import numpy as np

import config
import database.db as db_module
from image_processing.inspection import inspect_frame
from reports.weekly_report import weekly_data
from storage import save_image, save_inspection


def test_empty_frame_is_unknown():
    result = inspect_frame(np.zeros((100, 100, 3), dtype=np.uint8))
    assert result.result == "UNKNOWN"
    assert result.box is None


def test_database_insert_and_weekly_report(tmp_path, monkeypatch):
    db_path = tmp_path / "inspection.db"
    captured_dir = tmp_path / "captured_images"
    monkeypatch.setattr(config, "DATABASE_PATH", db_path)
    monkeypatch.setattr(db_module, "DATABASE_PATH", db_path)
    monkeypatch.setattr(config, "CAPTURED_DIR", captured_dir)
    db_module.init_db()

    fail_result = SimpleNamespace(result="FAIL", defect_type="Surface Defect", confidence=0.92, processing_time=0.25)
    insert_id = save_inspection(fail_result, "Camera-01", "P-001", np.zeros((120, 120, 3), dtype=np.uint8), is_demo=False)
    assert insert_id > 0

    with db_module.get_db() as connection:
        row = connection.execute("SELECT result, defect_type, camera_id, image_path FROM inspections WHERE id = ?", (insert_id,)).fetchone()
        assert row is not None
        assert row["result"] == "FAIL"
        assert row["defect_type"] == "Surface Defect"
        assert row["camera_id"] == "Camera-01"

    report = weekly_data(date.today())
    assert report["empty"] is False
    assert report["total"] >= 1
    assert report["failed"] >= 1
    assert report["most_common"] == "Surface Defect"


def test_image_save_and_defect_count(tmp_path, monkeypatch):
    db_path = tmp_path / "inspection.db"
    captured_dir = tmp_path / "captured_images"
    monkeypatch.setattr(config, "DATABASE_PATH", db_path)
    monkeypatch.setattr(db_module, "DATABASE_PATH", db_path)
    monkeypatch.setattr(config, "CAPTURED_DIR", captured_dir)
    monkeypatch.setattr(config, "SAVE_PASS_IMAGES", True)
    db_module.init_db()

    image_path = save_image(np.ones((80, 80, 3), dtype=np.uint8) * 255, "PASS")
    assert image_path is not None
    assert (tmp_path / image_path).exists()

    result = SimpleNamespace(result="PASS", defect_type=None, confidence=0.88, processing_time=0.1)
    save_inspection(result, "Camera-02", "P-002", np.ones((80, 80, 3), dtype=np.uint8) * 200, is_demo=True)

    with db_module.get_db() as connection:
        total_pass = connection.execute("SELECT COUNT(*) FROM inspections WHERE result = 'PASS'").fetchone()[0]
        demo_rows = connection.execute("SELECT COUNT(*) FROM inspections WHERE is_demo = 1").fetchone()[0]
        assert total_pass >= 1
        assert demo_rows >= 1
