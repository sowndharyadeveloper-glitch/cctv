import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = Path(os.getenv("DATABASE_PATH", BASE_DIR / "database" / "inspection.db"))
CAPTURED_DIR = Path(os.getenv("CAPTURED_DIR", BASE_DIR / "captured_images"))
REPORT_DIR = Path(os.getenv("REPORT_DIR", BASE_DIR / "reports" / "generated"))
CAMERA_SOURCE = os.getenv("CAMERA_SOURCE", "0")
CAMERA_ID = os.getenv("CAMERA_ID", "Assembly-Line-01")
SECRET_KEY = os.getenv("SECRET_KEY", "change-this-development-secret")
DEMO_MODE = os.getenv("DEMO_MODE", "true").lower() == "true"
INSPECTION_INTERVAL = float(os.getenv("INSPECTION_INTERVAL", "1.0"))
DETECTION_THRESHOLD = float(os.getenv("DETECTION_THRESHOLD", "0.08"))
SAVE_PASS_IMAGES = os.getenv("SAVE_PASS_IMAGES", "true").lower() == "true"
MAX_UPLOAD_MB = 8
ALLOWED_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png"}
DEFECT_CATEGORIES = (
	"Missing Component", "Wrong Component", "Incorrect Position", "Assembly Error",
	"Surface Defect", "Dimension/Alignment Issue", "Foreign Object", "Damaged Component", "Other"
)
