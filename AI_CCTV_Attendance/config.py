import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATABASE_DIR = BASE_DIR / "database"
DATASET_DIR = BASE_DIR / "dataset"
ENCODING_DIR = BASE_DIR / "encodings"
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"

SECRET_KEY = os.environ.get("SECRET_KEY", "ai-cctv-attendance-dev-key")
DB_PATH = os.environ.get("DATABASE_PATH", str(BASE_DIR / "database" / "attendance.db"))
CAMERA_SOURCE = os.environ.get("CAMERA_SOURCE", "0")
CAMERA_ID = os.environ.get("CAMERA_ID", "Classroom-01")
RECOGNITION_THRESHOLD = float(os.environ.get("RECOGNITION_THRESHOLD", "75.0"))
REQUIRED_CONFIRMATION_FRAMES = int(os.environ.get("REQUIRED_CONFIRMATION_FRAMES", "3"))
ATTENDANCE_START_TIME = os.environ.get("ATTENDANCE_START_TIME", "09:00")
LATE_AFTER = os.environ.get("LATE_AFTER", "09:15")
MAX_IMAGE_SIZE = int(os.environ.get("MAX_IMAGE_SIZE", "5242880"))
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg"}

for directory in [DATABASE_DIR, DATASET_DIR, ENCODING_DIR, STATIC_DIR, TEMPLATES_DIR]:
    directory.mkdir(parents=True, exist_ok=True)
