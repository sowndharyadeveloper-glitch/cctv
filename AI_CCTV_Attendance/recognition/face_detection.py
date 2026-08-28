import cv2
import numpy as np
from PIL import Image, ImageFilter
from werkzeug.datastructures import FileStorage

from config import ALLOWED_EXTENSIONS, MAX_IMAGE_SIZE


def validate_image_file(file: FileStorage) -> bool:
    if not file or not file.filename:
        return False
    if "." not in file.filename:
        return False
    ext = file.filename.rsplit(".", 1)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return False
    return True


def is_blurry(gray_image: np.ndarray, threshold: float = 100.0) -> bool:
    laplacian = cv2.Laplacian(gray_image, cv2.CV_64F)
    variance = laplacian.var()
    return variance < threshold


def detect_faces(frame: np.ndarray):
    if frame is None or frame.size == 0:
        return []

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gray = cv2.equalizeHist(gray)
    cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    if cascade.empty():
        raise RuntimeError("OpenCV face cascade could not be loaded.")

    faces = cascade.detectMultiScale(
        gray,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(60, 60),
    )
    valid_faces = []
    for (x, y, w, h) in faces:
        face_roi = gray[y:y + h, x:x + w]
        if face_roi.size == 0 or is_blurry(face_roi):
            continue
        valid_faces.append((int(x), int(y), int(w), int(h)))
    return valid_faces
