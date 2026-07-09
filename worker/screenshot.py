"""Screenshot provider: ADB PNG -> OpenCV frame (spec 5.2).

Keeps the ADB <-> OpenCV boundary in one place so the rest of the worker
works on :class:`Frame` objects and never touches raw bytes.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

import cv2
import numpy as np

from backend.core.errors import ADBError
from .adb_client import ADBClient


@dataclass
class Frame:
    """A decoded screenshot ready for vision processing."""

    image: "np.ndarray"
    width: int
    height: int
    captured_at: datetime
    source: str


class ScreenshotProvider:
    def __init__(self, adb: ADBClient) -> None:
        self.adb = adb

    def capture(self) -> Frame:
        png = self.adb.screenshot_png()
        arr = np.frombuffer(png, dtype=np.uint8)
        image = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if image is None:
            raise ADBError("failed to decode screenshot PNG")
        height, width = image.shape[:2]
        return Frame(
            image=image,
            width=width,
            height=height,
            captured_at=datetime.now(timezone.utc),
            source=f"adb:{self.adb.device_id}",
        )
