"""Template registry: maps a logical template id to a grayscale image on disk.

Template ids use a ``group/name`` form, e.g. ``battle/attack_button``. The
registry resolves them to ``<template_dir>/<group>/<name>.png`` and caches the
decoded grayscale image. Missing templates resolve to ``None`` so the rest of
the system degrades to "cannot detect this" instead of crashing — essential
during development before real templates are captured (spec section 7: "真实
坐标后续要通过截图校准").
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import cv2
import numpy as np

from backend.core.logging import get_logger

log = get_logger("worker.vision.templates")


class TemplateRegistry:
    def __init__(self, template_dir: str | Path, *, warn_missing: bool = True) -> None:
        self.template_dir = Path(template_dir)
        self._cache: dict[str, Optional[np.ndarray]] = {}
        self._warn_missing = warn_missing

    def resolve_path(self, template_id: str) -> Path:
        """``battle/attack_button`` -> ``<dir>/battle/attack_button.png``."""
        if template_id.endswith(".png"):
            return self.template_dir / template_id
        return self.template_dir / f"{template_id}.png"

    def get(self, template_id: str) -> Optional[np.ndarray]:
        path = self.resolve_path(template_id)
        if template_id in self._cache:
            cached = self._cache[template_id]
            if cached is not None or not path.exists():
                return cached
            # A template may be captured while the backend is already running.
            # Reload missing entries once their file appears on disk.
        if not path.exists():
            if self._warn_missing:
                log.debug("template missing: %s", template_id)
            self._cache[template_id] = None
            return None
        img = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
        if img is None:
            log.warning("template unreadable: %s", path)
        self._cache[template_id] = img
        return img

    def preload(self, template_ids: list[str]) -> None:
        for tid in template_ids:
            self.get(tid)
