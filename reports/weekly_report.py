from datetime import date, timedelta
from pathlib import Path

from openpyxl import Workbook

from config import REPORT_DIR
from database.db import get_db


def weekly_data(end_date: date | None = None) -> dict:
    end = end_date or date.today()
    start = end - timedelta(days=6)
    with get_db() as db:
        rows = db.execute(
            "SELECT * FROM inspections WHERE date(inspection_time) BETWEEN ? AND ? ORDER BY inspection_time",
            (start.isoformat(), end.isoformat()),
        ).fetchall()
    data = [dict(row) for row in rows]
    if not data:
        return {"empty": True, "start": start, "end": end}

    total = len(data)
    passed = sum(1 for row in data if row.get("result") == "PASS")
    failed = sum(1 for row in data if row.get("result") == "FAIL")

    defect_counts = {}
    for row in data:
        if row.get("result") == "FAIL" and row.get("defect_type"):
            defect_key = row["defect_type"]
            defect_counts[defect_key] = defect_counts.get(defect_key, 0) + 1

    daily = {}
    for row in data:
        inspection_time = str(row.get("inspection_time", ""))
        day = inspection_time[:10]
        if day:
            daily[day] = daily.get(day, 0) + 1

    return {
        "empty": False,
        "start": start,
        "end": end,
        "total": total,
        "passed": passed,
        "failed": failed,
        "pass_rate": round(passed / total * 100, 2),
        "fail_rate": round(failed / total * 100, 2),
        "most_common": max(defect_counts, key=defect_counts.get) if defect_counts else "None",
        "defects": defect_counts,
        "daily": daily,
        "rows": data,
    }


def generate_excel(end_date: date | None = None) -> Path | None:
    report = weekly_data(end_date)
    if report["empty"]:
        return None
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    path = REPORT_DIR / f"weekly_quality_{report['end'].isoformat()}.xlsx"
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Inspections"

    columns = [
        "id",
        "inspection_time",
        "product_id",
        "camera_id",
        "result",
        "defect_type",
        "confidence",
        "image_path",
        "processing_time",
        "is_demo",
        "created_at",
    ]
    sheet.append(columns)
    for row in report["rows"]:
        values = [row.get(column) for column in columns]
        sheet.append(values)

    workbook.save(path)
    return path
