import pickle
from pathlib import Path
from typing import Dict, Optional, Tuple

import cv2
import numpy as np

try:
    import face_recognition
except ImportError:  # pragma: no cover
    face_recognition = None

from config import ENCODING_DIR

ENCODINGS_FILE = Path(__file__).resolve().parents[1] / "encodings" / "face_encodings.pkl"
KNOWN_EMBEDDINGS: Dict[str, np.ndarray] = {}


def compute_face_embedding(face_image: np.ndarray) -> Optional[np.ndarray]:
    if face_image is None or face_image.size == 0:
        return None

    if face_recognition is not None:
        rgb = cv2.cvtColor(face_image, cv2.COLOR_BGR2RGB)
        encodings = face_recognition.face_encodings(rgb)
        if encodings:
            return np.asarray(encodings[0], dtype=np.float32)

    gray = cv2.cvtColor(face_image, cv2.COLOR_BGR2GRAY)
    gray = cv2.resize(gray, (128, 128))
    grad_x = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    grad_y = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    features = np.concatenate([
        gray.ravel().astype(np.float32),
        grad_x.ravel().astype(np.float32),
        grad_y.ravel().astype(np.float32),
    ])
    norm = np.linalg.norm(features)
    if norm == 0:
        return None
    return features / norm


def load_known_embeddings() -> Dict[str, np.ndarray]:
    global KNOWN_EMBEDDINGS
    ENCODING_DIR.mkdir(parents=True, exist_ok=True)
    ENCODINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not ENCODINGS_FILE.exists():
        with open(ENCODINGS_FILE, "wb") as file:
            pickle.dump({}, file)

    with open(ENCODINGS_FILE, "rb") as file:
        data = pickle.load(file)

    KNOWN_EMBEDDINGS = {
        str(student_id): np.asarray(values, dtype=np.float32)
        for student_id, values in data.items()
    }
    return KNOWN_EMBEDDINGS


def save_known_embeddings(data: Dict[str, list]) -> None:
    ENCODINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(ENCODINGS_FILE, "wb") as file:
        pickle.dump(data, file)


def refresh_known_embeddings() -> Dict[str, np.ndarray]:
    return load_known_embeddings()


def detect_student_in_frame(candidate_embedding: np.ndarray) -> Tuple[str, float]:
    best_name = "Unknown"
    best_score = 0.0

    for student_id, known_embedding in KNOWN_EMBEDDINGS.items():
        if candidate_embedding is None or known_embedding is None:
            continue
        distance = float(np.linalg.norm(candidate_embedding - known_embedding))
        confidence = max(0.0, 100.0 - distance * 1.6)
        if confidence > best_score:
            best_score = confidence
            best_name = student_id

    if best_score < 75.0:
        return "Unknown", best_score
    return best_name, best_score
