import cv2
import numpy as np
from config import CAMERA_SOURCE


def source_value(source: str | int | None = None):
    value = str(CAMERA_SOURCE if source is None else source)
    return int(value) if value.isdigit() else value


class Camera:
    def __init__(self, source=None):
        self.source = source_value(source)
        self.capture = None
        self.status = "DISCONNECTED"

    def connect(self) -> bool:
        self.status = "RECONNECTING"
        self.capture = cv2.VideoCapture(self.source)
        if self.capture.isOpened():
            self.status = "CONNECTED"
            return True
        self.status = "DISCONNECTED"
        self.release()
        return False

    def read(self) -> tuple[bool, np.ndarray | None]:
        if self.capture is None and not self.connect():
            return False, None
        ok, frame = self.capture.read()
        if not ok:
            self.status = "DISCONNECTED"
        return ok, frame if ok else None

    def release(self) -> None:
        if self.capture is not None:
            self.capture.release()
        self.capture = None
