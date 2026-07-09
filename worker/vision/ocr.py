"""Optional OCR backend (spec: ``use_ocr: false`` by default).

OCR is only needed for friend-name matching, a post-MVP enhancement. To keep
the dependency optional, we define a backend protocol and a no-op default.
A real backend (e.g. PaddleOCR / RapidOCR) can be plugged in later without
touching the detector.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

import numpy as np


@runtime_checkable
class OCRBackend(Protocol):
    def recognize(self, image: np.ndarray) -> str:
        """Return recognized text from an image region, or '' if nothing found."""
        ...


class NoOpOCR:
    """Default backend: recognizes nothing. Used when ``use_ocr`` is false."""

    def recognize(self, image: np.ndarray) -> str:  # noqa: D401
        return ""


# Module-level default backend.
_default: OCRBackend = NoOpOCR()


def get_default() -> OCRBackend:
    return _default


def set_default(backend: OCRBackend) -> None:
    global _default
    _default = backend
