"""OpenCV template-matching primitives.

Everything operates on grayscale images in base-resolution space. Returns
:class:`MatchResult` with a confidence so callers can decide thresholds.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import cv2
import numpy as np

from .roi import ROI


@dataclass
class MatchResult:
    found: bool = False
    confidence: float = 0.0
    template_id: Optional[str] = None
    x: int = 0  # top-left x in base-resolution space
    y: int = 0
    w: int = 0
    h: int = 0

    def center(self) -> tuple[int, int]:
        return (self.x + self.w // 2, self.y + self.h // 2)


def match_template(
    image_gray: np.ndarray,
    template_gray: Optional[np.ndarray],
    *,
    roi: Optional[ROI] = None,
) -> MatchResult:
    """Single-scale TM_CCOEFF_NORMED match. Returns best location + confidence."""
    if template_gray is None or image_gray is None:
        return MatchResult()

    search = image_gray
    offset_x, offset_y = 0, 0
    if roi is not None:
        search = roi.crop(image_gray)
        offset_x, offset_y = roi.x, roi.y

    th, tw = template_gray.shape[:2]
    if th > search.shape[0] or tw > search.shape[1]:
        return MatchResult()

    result = cv2.matchTemplate(search, template_gray, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(result)
    return MatchResult(
        confidence=float(max_val),
        x=int(max_loc[0]) + offset_x,
        y=int(max_loc[1]) + offset_y,
        w=int(tw),
        h=int(th),
    )


def best_of(
    image_gray: np.ndarray,
    candidates: list[np.ndarray],
    *,
    roi: Optional[ROI] = None,
) -> tuple[int, MatchResult]:
    """Return (index, MatchResult) of the highest-confidence candidate."""
    best_idx, best = -1, MatchResult()
    for idx, tmpl in enumerate(candidates):
        m = match_template(image_gray, tmpl, roi=roi)
        if m.confidence > best.confidence:
            best, best_idx = m, idx
    return best_idx, best
