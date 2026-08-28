import os
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional

from config import DB_PATH


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _table_columns(conn: sqlite3.Connection, table_name: str) -> set[str]:
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return {row[1] for row in rows}


def init_db() -> None:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = get_connection()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                register_number TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                department TEXT NOT NULL,
                year TEXT NOT NULL,
                section TEXT NOT NULL,
                email TEXT,
                phone TEXT,
                face_encoding TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS face_embeddings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                embedding TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(student_id) REFERENCES students(id) ON DELETE CASCADE
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                attendance_date TEXT NOT NULL,
                attendance_time TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Present',
                confidence REAL NOT NULL DEFAULT 0.0,
                camera_id TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(student_id, attendance_date),
                FOREIGN KEY(student_id) REFERENCES students(id) ON DELETE CASCADE
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS admin_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'faculty',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'faculty',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS cameras (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                camera_type TEXT NOT NULL DEFAULT 'ip_camera',
                stream_url TEXT NOT NULL,
                location TEXT,
                department TEXT,
                status TEXT NOT NULL DEFAULT 'unknown',
                last_checked_at TEXT,
                last_error TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS safety_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alert_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                camera_id INTEGER,
                zone_id TEXT,
                tracking_id TEXT,
                confidence REAL NOT NULL DEFAULT 0.0,
                description TEXT NOT NULL,
                snapshot_path TEXT,
                video_path TEXT,
                status TEXT NOT NULL DEFAULT 'NEW',
                simulated INTEGER NOT NULL DEFAULT 0,
                acknowledged_by TEXT,
                acknowledged_at TEXT,
                resolved_at TEXT,
                resolution_note TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(camera_id) REFERENCES cameras(id) ON DELETE SET NULL
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS zones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                camera_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                zone_type TEXT NOT NULL DEFAULT 'restricted',
                geometry_json TEXT NOT NULL,
                severity TEXT NOT NULL DEFAULT 'HIGH',
                required_ppe_json TEXT NOT NULL DEFAULT '[]',
                alert_enabled INTEGER NOT NULL DEFAULT 1,
                recording_enabled INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(camera_id) REFERENCES cameras(id) ON DELETE CASCADE
            )
            """
        )

        student_cols = _table_columns(conn, 'students')
        for col in ['email', 'phone', 'face_encoding']:
            if col not in student_cols:
                conn.execute(f'ALTER TABLE students ADD COLUMN {col} TEXT')

        admin_cols = _table_columns(conn, 'admin_users')
        if 'role' not in admin_cols:
            conn.execute("ALTER TABLE admin_users ADD COLUMN role TEXT NOT NULL DEFAULT 'faculty'")

        user_cols = _table_columns(conn, 'users')
        if 'role' not in user_cols:
            conn.execute("ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'faculty'")

        conn.execute("CREATE INDEX IF NOT EXISTS idx_students_register_number ON students(register_number)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_attendance_date ON attendance(attendance_date)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_attendance_student ON attendance(student_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_face_student ON face_embeddings(student_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_cameras_status ON cameras(status)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_alerts_status_created ON safety_alerts(status, created_at)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_alerts_dedupe ON safety_alerts(alert_type, camera_id, zone_id, tracking_id, created_at)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_zones_camera ON zones(camera_id)")
        conn.commit()
    finally:
        conn.close()


def ensure_default_admin(username: str = "admin", password_hash: str = "pbkdf2:sha256:150000$admin123") -> None:
    conn = get_connection()
    try:
        existing = conn.execute("SELECT id FROM admin_users WHERE username = ?", (username,)).fetchone()
        if existing is None:
            conn.execute(
                "INSERT INTO admin_users (username, password_hash, role) VALUES (?, ?, ?)",
                (username, password_hash, "faculty"),
            )
            conn.commit()
    finally:
        conn.close()


def add_student(data: Dict[str, str]) -> Optional[int]:
    conn = get_connection()
    try:
        cursor = conn.execute(
            """
            INSERT INTO students (register_number, name, department, year, section, email, phone, face_encoding)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data.get("register_number", "").strip(),
                data.get("name", "").strip(),
                data.get("department", "").strip(),
                data.get("year", "").strip(),
                data.get("section", "").strip(),
                data.get("email", "").strip(),
                data.get("phone", "").strip(),
                data.get("face_encoding"),
            ),
        )
        conn.commit()
        return int(cursor.lastrowid)
    except sqlite3.IntegrityError:
        conn.rollback()
        return None
    finally:
        conn.close()


def get_student_by_register(register_number: str) -> Optional[sqlite3.Row]:
    conn = get_connection()
    try:
        return conn.execute(
            "SELECT * FROM students WHERE register_number = ?",
            (register_number,),
        ).fetchone()
    finally:
        conn.close()


def get_student_by_id(student_id: int) -> Optional[sqlite3.Row]:
    conn = get_connection()
    try:
        return conn.execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone()
    finally:
        conn.close()


def get_all_students() -> List[sqlite3.Row]:
    conn = get_connection()
    try:
        return conn.execute("SELECT * FROM students ORDER BY name ASC").fetchall()
    finally:
        conn.close()


def delete_student(student_id: int) -> None:
    conn = get_connection()
    try:
        conn.execute("DELETE FROM students WHERE id = ?", (student_id,))
        conn.commit()
    finally:
        conn.close()


def update_student(student_id: int, data: Dict[str, str]) -> None:
    conn = get_connection()
    try:
        conn.execute(
            """
            UPDATE students
            SET register_number = ?, name = ?, department = ?, year = ?, section = ?, email = ?, phone = ?, face_encoding = ?
            WHERE id = ?
            """,
            (
                data.get("register_number", "").strip(),
                data.get("name", "").strip(),
                data.get("department", "").strip(),
                data.get("year", "").strip(),
                data.get("section", "").strip(),
                data.get("email", "").strip(),
                data.get("phone", "").strip(),
                data.get("face_encoding"),
                student_id,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def insert_face_embedding(student_id: int, embedding: str) -> None:
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO face_embeddings (student_id, embedding) VALUES (?, ?)",
            (student_id, embedding),
        )
        conn.commit()
    finally:
        conn.close()


def get_face_embeddings_for_student(student_id: int) -> List[sqlite3.Row]:
    conn = get_connection()
    try:
        return conn.execute(
            "SELECT * FROM face_embeddings WHERE student_id = ? ORDER BY created_at DESC",
            (student_id,),
        ).fetchall()
    finally:
        conn.close()


def clear_face_embeddings_for_student(student_id: int) -> None:
    conn = get_connection()
    try:
        conn.execute("DELETE FROM face_embeddings WHERE student_id = ?", (student_id,))
        conn.commit()
    finally:
        conn.close()


def mark_attendance(student_id: int, attendance_date: str, attendance_time: str, status: str, confidence: float, camera_id: str) -> bool:
    conn = get_connection()
    try:
        existing = conn.execute(
            "SELECT 1 FROM attendance WHERE student_id = ? AND attendance_date = ?",
            (student_id, attendance_date),
        ).fetchone()
        if existing:
            return False
        conn.execute(
            """
            INSERT INTO attendance (student_id, attendance_date, attendance_time, status, confidence, camera_id)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (student_id, attendance_date, attendance_time, status, confidence, camera_id),
        )
        conn.commit()
        return True
    finally:
        conn.close()


def get_attendance_records(filters: Optional[Dict[str, Any]] = None) -> List[sqlite3.Row]:
    conn = get_connection()
    try:
        query = """
            SELECT a.*, s.register_number, s.name, s.department, s.year, s.section
            FROM attendance a
            JOIN students s ON s.id = a.student_id
        """
        params: List[Any] = []
        clauses: List[str] = []

        if filters:
            if filters.get("date"):
                clauses.append("a.attendance_date = ?")
                params.append(filters["date"])
            if filters.get("status"):
                clauses.append("a.status = ?")
                params.append(filters["status"])
            if filters.get("department"):
                clauses.append("s.department = ?")
                params.append(filters["department"])
            if filters.get("register_number"):
                clauses.append("s.register_number LIKE ?")
                params.append(f"%{filters['register_number']}%")
            if filters.get("name"):
                clauses.append("s.name LIKE ?")
                params.append(f"%{filters['name']}%")

        if clauses:
            query += " WHERE " + " AND ".join(clauses)

        query += " ORDER BY a.attendance_date DESC, a.attendance_time DESC"
        return conn.execute(query, params).fetchall()
    finally:
        conn.close()


def get_student_attendance(student_id: int) -> List[sqlite3.Row]:
    conn = get_connection()
    try:
        return conn.execute(
            "SELECT * FROM attendance WHERE student_id = ? ORDER BY attendance_date DESC, attendance_time DESC",
            (student_id,),
        ).fetchall()
    finally:
        conn.close()


def get_admin_user(username: str) -> Optional[sqlite3.Row]:
    conn = get_connection()
    try:
        return conn.execute("SELECT * FROM admin_users WHERE username = ?", (username,)).fetchone()
    finally:
        conn.close()


def add_camera(data: Dict[str, str]) -> Optional[int]:
    conn = get_connection()
    try:
        cursor = conn.execute(
            """
            INSERT INTO cameras (name, camera_type, stream_url, location, department)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                data.get("name", "").strip(),
                data.get("camera_type", "ip_camera").strip(),
                data.get("stream_url", "").strip(),
                data.get("location", "").strip(),
                data.get("department", "").strip(),
            ),
        )
        conn.commit()
        return int(cursor.lastrowid)
    except sqlite3.IntegrityError:
        conn.rollback()
        return None
    finally:
        conn.close()


def get_all_cameras() -> List[sqlite3.Row]:
    conn = get_connection()
    try:
        return conn.execute("SELECT * FROM cameras ORDER BY name ASC").fetchall()
    finally:
        conn.close()


def get_camera_by_id(camera_id: int) -> Optional[sqlite3.Row]:
    conn = get_connection()
    try:
        return conn.execute("SELECT * FROM cameras WHERE id = ?", (camera_id,)).fetchone()
    finally:
        conn.close()


def update_camera_status(camera_id: int, status: str, error: Optional[str] = None) -> None:
    conn = get_connection()
    try:
        conn.execute(
            """
            UPDATE cameras
            SET status = ?, last_error = ?, last_checked_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (status, error, camera_id),
        )
        conn.commit()
    finally:
        conn.close()


def delete_camera(camera_id: int) -> None:
    conn = get_connection()
    try:
        conn.execute("DELETE FROM cameras WHERE id = ?", (camera_id,))
        conn.commit()
    finally:
        conn.close()


def add_zone(data: Dict[str, Any]) -> Optional[int]:
    conn = get_connection()
    try:
        cursor = conn.execute(
            """
            INSERT INTO zones (camera_id, name, zone_type, geometry_json, severity, required_ppe_json, alert_enabled, recording_enabled)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (data["camera_id"], data["name"].strip(), data.get("zone_type", "restricted"), data["geometry_json"], data.get("severity", "HIGH"), data.get("required_ppe_json", "[]"), int(bool(data.get("alert_enabled", True))), int(bool(data.get("recording_enabled", False)))),
        )
        conn.commit()
        return int(cursor.lastrowid)
    except sqlite3.IntegrityError:
        conn.rollback()
        return None
    finally:
        conn.close()


def get_all_zones() -> List[sqlite3.Row]:
    conn = get_connection()
    try:
        return conn.execute("SELECT z.*, c.name AS camera_name FROM zones z JOIN cameras c ON c.id = z.camera_id ORDER BY z.created_at DESC").fetchall()
    finally:
        conn.close()


def get_zone_by_id(zone_id: int) -> Optional[sqlite3.Row]:
    conn = get_connection()
    try:
        return conn.execute("SELECT * FROM zones WHERE id = ?", (zone_id,)).fetchone()
    finally:
        conn.close()


def delete_zone(zone_id: int) -> bool:
    conn = get_connection()
    try:
        cursor = conn.execute("DELETE FROM zones WHERE id = ?", (zone_id,))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def create_safety_alert(data: Dict[str, Any], cooldown_seconds: int = 30) -> Optional[int]:
    conn = get_connection()
    try:
        duplicate = conn.execute(
            """
            SELECT id FROM safety_alerts
            WHERE alert_type = ? AND camera_id IS ? AND zone_id IS ? AND tracking_id IS ?
              AND status NOT IN ('RESOLVED', 'FALSE_POSITIVE')
              AND datetime(created_at) >= datetime('now', ?)
            ORDER BY id DESC LIMIT 1
            """,
            (
                data["alert_type"], data.get("camera_id"), data.get("zone_id"),
                data.get("tracking_id"), f"-{cooldown_seconds} seconds",
            ),
        ).fetchone()
        if duplicate:
            return None
        cursor = conn.execute(
            """
            INSERT INTO safety_alerts
            (alert_type, severity, camera_id, zone_id, tracking_id, confidence,
             description, snapshot_path, video_path, simulated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data["alert_type"], data["severity"], data.get("camera_id"), data.get("zone_id"),
                data.get("tracking_id"), data.get("confidence", 0.0), data["description"],
                data.get("snapshot_path"), data.get("video_path"), int(bool(data.get("simulated", False))),
            ),
        )
        conn.commit()
        return int(cursor.lastrowid)
    finally:
        conn.close()


def get_safety_alerts(status: Optional[str] = None) -> List[sqlite3.Row]:
    conn = get_connection()
    try:
        query = "SELECT a.*, c.name AS camera_name, c.location AS camera_location FROM safety_alerts a LEFT JOIN cameras c ON c.id = a.camera_id"
        params: List[Any] = []
        if status:
            query += " WHERE a.status = ?"
            params.append(status)
        query += " ORDER BY a.created_at DESC, a.id DESC LIMIT 100"
        return conn.execute(query, params).fetchall()
    finally:
        conn.close()


def update_alert_status(alert_id: int, status: str, username: str, resolution_note: Optional[str] = None) -> bool:
    conn = get_connection()
    try:
        existing = conn.execute("SELECT id FROM safety_alerts WHERE id = ?", (alert_id,)).fetchone()
        if not existing:
            return False
        if status == "ACKNOWLEDGED":
            conn.execute(
                "UPDATE safety_alerts SET status = ?, acknowledged_by = ?, acknowledged_at = CURRENT_TIMESTAMP WHERE id = ?",
                (status, username, alert_id),
            )
        elif status in {"RESOLVED", "FALSE_POSITIVE", "ESCALATED", "INVESTIGATING"}:
            conn.execute(
                "UPDATE safety_alerts SET status = ?, resolved_at = CASE WHEN ? IN ('RESOLVED', 'FALSE_POSITIVE') THEN CURRENT_TIMESTAMP ELSE resolved_at END, resolution_note = ? WHERE id = ?",
                (status, status, resolution_note, alert_id),
            )
        else:
            return False
        conn.commit()
        return True
    finally:
        conn.close()


def get_dashboard_stats() -> Dict[str, Any]:
    conn = get_connection()
    try:
        total_students = conn.execute("SELECT COUNT(*) AS total FROM students").fetchone()["total"]
        today = datetime.now().strftime("%Y-%m-%d")
        present_today = conn.execute("SELECT COUNT(*) AS total FROM attendance WHERE attendance_date = ?", (today,)).fetchone()["total"]
        late_today = conn.execute("SELECT COUNT(*) AS total FROM attendance WHERE attendance_date = ? AND status = 'Late'", (today,)).fetchone()["total"]
        absent_today = max(total_students - present_today, 0)
        percentage = (present_today / total_students * 100) if total_students else 0
        recent = conn.execute(
            """
            SELECT a.*, s.name, s.register_number
            FROM attendance a
            JOIN students s ON s.id = a.student_id
            ORDER BY a.created_at DESC
            LIMIT 8
            """
        ).fetchall()
        return {
            "total_students": total_students,
            "present_today": present_today,
            "late_today": late_today,
            "absent_today": absent_today,
            "attendance_percentage": round(percentage, 2),
            "recent_attendance": recent,
        }
    finally:
        conn.close()


def get_department_summary() -> List[sqlite3.Row]:
    conn = get_connection()
    try:
        return conn.execute(
            """
            SELECT s.department, COUNT(a.id) AS total_present
            FROM students s
            LEFT JOIN attendance a ON a.student_id = s.id AND a.attendance_date = ?
            GROUP BY s.department
            ORDER BY s.department ASC
            """,
            (datetime.now().strftime("%Y-%m-%d"),),
        ).fetchall()
    finally:
        conn.close()


def get_monthly_summary() -> List[sqlite3.Row]:
    conn = get_connection()
    try:
        return conn.execute(
            """
            SELECT substr(attendance_date, 1, 7) AS month, COUNT(*) AS total
            FROM attendance
            GROUP BY substr(attendance_date, 1, 7)
            ORDER BY month DESC
            LIMIT 12
            """
        ).fetchall()
    finally:
        conn.close()


def get_daily_summary() -> List[sqlite3.Row]:
    conn = get_connection()
    try:
        return conn.execute(
            """
            SELECT attendance_date, COUNT(*) AS total
            FROM attendance
            GROUP BY attendance_date
            ORDER BY attendance_date DESC
            LIMIT 14
            """
        ).fetchall()
    finally:
        conn.close()
