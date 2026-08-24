import io
import os
from functools import wraps

import cv2
import numpy as np
from flask import Flask, Response, abort, flash, redirect, render_template, request, session, url_for, send_file
from werkzeug.security import check_password_hash, generate_password_hash

import config
from camera.camera import Camera
from database.db import get_db, init_db, log_event
from image_processing.inspection import inspect_frame
from reports.weekly_report import generate_excel, weekly_data
from storage import save_inspection

app = Flask(__name__)
app.secret_key = config.SECRET_KEY
app.config["MAX_CONTENT_LENGTH"] = config.MAX_UPLOAD_MB * 1024 * 1024
init_db()
for folder in (config.CAPTURED_DIR / "pass", config.CAPTURED_DIR / "fail", config.REPORT_DIR):
    folder.mkdir(parents=True, exist_ok=True)


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("authenticated"):
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


def summary():
    with get_db() as db:
        total = db.execute("SELECT COUNT(*) AS n FROM inspections").fetchone()["n"]
        passed = db.execute("SELECT COUNT(*) AS n FROM inspections WHERE result = 'PASS'").fetchone()["n"]
        failed = db.execute("SELECT COUNT(*) AS n FROM inspections WHERE result = 'FAIL'").fetchone()["n"]
        common = db.execute("SELECT defect_type, count FROM defect_summary ORDER BY count DESC LIMIT 1").fetchone()
        recent = db.execute("SELECT * FROM inspections ORDER BY id DESC LIMIT 8").fetchall()
        daily = db.execute("SELECT substr(inspection_time, 1, 10) AS day, result, COUNT(*) AS count FROM inspections GROUP BY day, result ORDER BY day DESC LIMIT 30").fetchall()
    return {"total": total, "passed": passed, "failed": failed, "pass_rate": round(passed / total * 100, 1) if total else 0,
            "fail_rate": round(failed / total * 100, 1) if total else 0, "common": common, "recent": recent, "daily": daily,
            "mode": "DEMO DATA" if config.DEMO_MODE else "REAL DATA"}


@app.route("/")
def index():
    return redirect(url_for("dashboard" if session.get("authenticated") else "login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        expected_hash = os.getenv("ADMIN_PASSWORD_HASH", generate_password_hash("admin123"))
        if request.form.get("username") == os.getenv("ADMIN_USERNAME", "admin") and check_password_hash(expected_hash, request.form.get("password", "")):
            session["authenticated"] = True
            return redirect(request.args.get("next") or url_for("dashboard"))
        flash("Invalid credentials.", "error")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html", stats=summary(), config=config)


@app.route("/inspection")
@login_required
def inspection():
    return render_template("inspection.html", config=config)


@app.route("/history")
@login_required
def history():
    filters = {key: request.args.get(key, "").strip() for key in ("result", "defect", "date", "q")}
    clauses, values = ["1=1"], []
    if filters["result"] in {"PASS", "FAIL", "UNKNOWN"}:
        clauses.append("result = ?"); values.append(filters["result"])
    if filters["defect"]:
        clauses.append("defect_type = ?"); values.append(filters["defect"])
    if filters["date"]:
        clauses.append("date(inspection_time) = ?"); values.append(filters["date"])
    if filters["q"].isdigit():
        clauses.append("id = ?"); values.append(int(filters["q"]))
    with get_db() as db:
        rows = db.execute(f"SELECT * FROM inspections WHERE {' AND '.join(clauses)} ORDER BY id DESC", values).fetchall()
        defects = db.execute("SELECT DISTINCT defect_type FROM inspections WHERE defect_type IS NOT NULL ORDER BY defect_type").fetchall()
    return render_template("history.html", inspections=rows, filters=filters, defects=defects)


@app.route("/inspection-image/<int:inspection_id>")
@login_required
def inspection_image(inspection_id):
    with get_db() as db:
        row = db.execute("SELECT image_path FROM inspections WHERE id = ?", (inspection_id,)).fetchone()
    if not row or not row["image_path"]:
        abort(404)
    image_path = (config.BASE_DIR / row["image_path"]).resolve()
    if config.CAPTURED_DIR.resolve() not in image_path.parents:
        abort(404)
    return send_file(image_path)


@app.route("/reports")
@login_required
def reports():
    return render_template("reports.html", report=weekly_data())


@app.route("/reports/generate", methods=["POST"])
@login_required
def generate_report():
    path = generate_excel()
    flash("No inspection data available for the selected period." if path is None else f"Weekly report generated: {path.name}", "error" if path is None else "success")
    return redirect(url_for("reports"))


@app.route("/reports/export")
@login_required
def export_report():
    with get_db() as db:
        rows = db.execute("SELECT id, inspection_time, product_id, camera_id, result, defect_type, confidence, processing_time, is_demo FROM inspections ORDER BY id DESC").fetchall()
    output = io.BytesIO()
    pd.DataFrame([dict(row) for row in rows]).to_excel(output, index=False)
    output.seek(0)
    return send_file(output, as_attachment=True, download_name="quality_inspections.xlsx", mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


@app.route("/settings")
@login_required
def settings():
    return render_template("settings.html", config=config)


def demo_frame() -> np.ndarray:
    frame = np.full((480, 800, 3), 35, dtype=np.uint8)
    cv2.rectangle(frame, (190, 110), (610, 370), (170, 175, 180), -1)
    cv2.rectangle(frame, (245, 165), (555, 315), (70, 75, 80), 5)
    cv2.putText(frame, "DEMO WORKPIECE", (270, 250), cv2.FONT_HERSHEY_SIMPLEX, 1, (220, 220, 220), 2)
    return frame


def frame_stream():
    camera = Camera()
    frame_count = 0
    try:
        while True:
            frame_count += 1
            ok, frame = (True, demo_frame()) if config.DEMO_MODE else camera.read()
            if not ok or frame is None:
                status = "DISCONNECTED"
                frame = np.zeros((480, 800, 3), dtype=np.uint8)
                cv2.putText(frame, "CAMERA DISCONNECTED", (180, 240), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 80, 220), 2)
            else:
                status = "DEMO DATA" if config.DEMO_MODE else camera.status
                result = inspect_frame(frame)
                if frame_count % 20 == 0 and result.result != "UNKNOWN":
                    try:
                        save_inspection(result, config.CAMERA_ID, None, frame, config.DEMO_MODE)
                    except OSError as exc:
                        log_event("ERROR", str(exc))
                if result.box:
                    x, y, width, height = result.box
                    color = (70, 210, 130) if result.result == "PASS" else (40, 80, 220)
                    cv2.rectangle(frame, (x, y), (x + width, y + height), color, 3)
                    cv2.putText(frame, f"{result.result} {result.confidence:.0%}", (x, max(y - 10, 25)), cv2.FONT_HERSHEY_SIMPLEX, .8, (255, 255, 255), 2)
            cv2.putText(frame, f"{config.CAMERA_ID} | {status}", (18, 32), cv2.FONT_HERSHEY_SIMPLEX, .65, (240, 240, 240), 2)
            ok, buffer = cv2.imencode(".jpg", frame)
            if ok:
                yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + buffer.tobytes() + b"\r\n"
    finally:
        camera.release()


@app.route("/video_feed")
@login_required
def video_feed():
    return Response(frame_stream(), mimetype="multipart/x-mixed-replace; boundary=frame")


if __name__ == "__main__":
    app.run(debug=True)
