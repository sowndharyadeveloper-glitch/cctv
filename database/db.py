import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Iterator

from config import DATABASE_PATH

SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS inspections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    inspection_time TEXT NOT NULL,
    product_id TEXT,
    camera_id TEXT NOT NULL,
    result TEXT NOT NULL CHECK(result IN ('PASS', 'FAIL', 'UNKNOWN')),
    defect_type TEXT,
    confidence REAL,
    image_path TEXT,
    processing_time REAL NOT NULL,
    is_demo INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS defect_summary (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    defect_type TEXT NOT NULL UNIQUE,
    count INTEGER NOT NULL DEFAULT 0,
    last_detected TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS system_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    log_time TEXT NOT NULL,
    level TEXT NOT NULL,
    message TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_inspection_time ON inspections(inspection_time);
CREATE INDEX IF NOT EXISTS idx_inspection_result ON inspections(result);
CREATE INDEX IF NOT EXISTS idx_inspection_defect ON inspections(defect_type);
"""


def init_db() -> None:
    Path(DATABASE_PATH).parent.mkdir(parents=True, exist_ok=True)
    with get_db() as connection:
        connection.executescript(SCHEMA)


@contextmanager
def get_db() -> Iterator[sqlite3.Connection]:
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def log_event(level: str, message: str) -> None:
    with get_db() as db:
        db.execute("INSERT INTO system_logs(log_time, level, message) VALUES (?, ?, ?)", (now_iso(), level, message))
