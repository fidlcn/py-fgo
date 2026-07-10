"""VisionDetector (spec section 5.3).

Generic, FGO-agnostic: it matches templates in base-resolution (1280x720)
space and reports the best-matching configured state. The ``worker.fgo``
layer supplies the state definitions and the enum mapping.

Battle vision is intentionally strict for execution-critical checks: if a
template needed to prove skill/NP readiness is missing or not matched, callers
receive ``False`` and should stop instead of continuing with unsafe fallback.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import cv2
import numpy as np

from ..screenshot import Frame
from .matching import MatchResult, match_template
from .ocr import OCRBackend, get_default
from .roi import ROI
from .templates import TemplateRegistry


@dataclass
class StateDef:
    """How to recognize a single UI state."""

    state: str
    templates: list[str]
    roi: Optional[ROI] = None
    min_confidence: float = 0.85


@dataclass
class CardDetection:
    position: int  # 1..5
    color: Optional[str] = None  # "Arts" | "Buster" | "Quick"
    servant_slot: Optional[int] = None
    confidence: float = 0.0


@dataclass
class DetectionResult:
    state: str = "UNKNOWN"
    confidence: float = 0.0
    matched_template: Optional[str] = None


class VisionDetector:
    def __init__(
        self,
        templates: TemplateRegistry,
        state_defs: Optional[list[StateDef]] = None,
        *,
        base_resolution: tuple[int, int] = (1280, 720),
        state_threshold: float = 0.85,
        template_threshold: float = 0.82,
        ocr: Optional[OCRBackend] = None,
    ) -> None:
        self.templates = templates
        self.state_defs: list[StateDef] = list(state_defs or [])
        self.base_w, self.base_h = base_resolution
        self.state_threshold = state_threshold
        self.template_threshold = template_threshold
        self.ocr = ocr or get_default()

    def set_state_defs(self, defs: list[StateDef]) -> None:
        self.state_defs = list(defs)

    # --- internal -------------------------------------------------------

    def _gray_base(self, frame: Frame) -> np.ndarray:
        """Return the frame resized to base resolution and converted to gray.

        Cached on the Frame object itself (not on id(), which CPython may
        reuse for a freed array and return a stale image).
        """
        cached = getattr(frame, "_gray_base", None)
        if cached is not None and cached.shape[:2] == (self.base_h, self.base_w):
            return cached
        img = frame.image
        if img.shape[1] != self.base_w or img.shape[0] != self.base_h:
            img = cv2.resize(img, (self.base_w, self.base_h))
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        frame._gray_base = gray  # type: ignore[attr-defined]
        return gray

    # --- public API (spec 5.3) -----------------------------------------

    def find_template(
        self, frame: Frame, template_id: str, roi: Optional[ROI] = None
    ) -> MatchResult:
        gray = self._gray_base(frame)
        tmpl = self.templates.get(template_id)
        m = match_template(gray, tmpl, roi=roi)
        m.template_id = template_id
        m.found = m.confidence >= self.template_threshold
        return m

    def detect_state(self, frame: Frame) -> DetectionResult:
        gray = self._gray_base(frame)
        best = DetectionResult()
        for sd in self.state_defs:
            threshold = sd.min_confidence or self.state_threshold
            for tid in sd.templates:
                tmpl = self.templates.get(tid)
                m = match_template(gray, tmpl, roi=sd.roi)
                if m.confidence >= threshold and m.confidence > best.confidence:
                    best = DetectionResult(
                        state=sd.state, confidence=m.confidence, matched_template=tid
                    )
        return best

    def find_all_cards(self, frame: Frame) -> list[CardDetection]:
        """MVP: card-color recognition is not calibrated. Returns empty list."""
        return []

    def is_skill_ready(self, frame: Frame, servant_slot: int, skill: int) -> bool:
        template_id = (
            f"battle/skill_ready_{servant_slot}_{skill}"
            if servant_slot > 0
            else f"battle/master_skill_ready_{skill}"
        )
        tmpl = self.templates.get(template_id)
        if tmpl is None:
            return False
        return self.find_template(frame, template_id).found

    def is_np_ready(self, frame: Frame, servant_slot: int) -> bool:
        template_id = f"battle/np_ready_{servant_slot}"
        tmpl = self.templates.get(template_id)
        if tmpl is None:
            return False
        return self.find_template(frame, template_id).found
