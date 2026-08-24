import cv2
import numpy as np


def preprocess(frame: np.ndarray, max_width: int = 960) -> np.ndarray:
    height, width = frame.shape[:2]
    if width > max_width:
        scale = max_width / width
        frame = cv2.resize(frame, (max_width, int(height * scale)))
    return cv2.GaussianBlur(frame, (5, 5), 0)


def gray_edges(frame: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    return cv2.Canny(gray, 50, 150)
