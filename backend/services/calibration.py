"""Coordinate calibration storage.

Coordinates are captured from ADB screenshots in base-space semantics. They are
stored in ``configs/coordinates.json`` and loaded into ``AppConfig`` so workers
can prefer calibrated points over hard-coded defaults.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from backend.core.config import AppConfig, DEFAULT_COORDINATES_PATH
from backend.core.errors import ValidationError


POINTS: dict[str, str] = {
    "QUEST_DETAIL_START": "关卡详情页：开始任务",
    "QUEST_START_BUTTON": "队伍确认页：开始任务",
    "QUEST_AUTO_BURN_CONFIRM": "自动变还弹窗：决定",
    "ATTACK_BUTTON": "战斗：Attack",
    "SUPPORT_FIRST_RECOMMENDED": "助战：推荐第一个",
    "RESULT_NEXT": "结算：下一步",
    "FRIEND_REQUEST_DECLINE": "好友申请：拒绝",
}


class CalibrationService:
    def __init__(self, config: AppConfig, path: Path = DEFAULT_COORDINATES_PATH) -> None:
        self.config = config
        self.path = path

    def list_points(self) -> dict[str, Any]:
        return {
            "available": [{"key": key, "label": label} for key, label in POINTS.items()],
            "overrides": {
                key: [value[0], value[1]]
                for key, value in self.config.coordinates.overrides.items()
            },
        }

    def set_point(self, key: str, x: int, y: int) -> dict[str, Any]:
        if key not in POINTS:
            raise ValidationError(f"unknown calibration point: {key}")
        if x < 0 or y < 0:
            raise ValidationError("coordinate must be non-negative")
        self.config.coordinates.overrides[key] = (int(x), int(y))
        self._save()
        return self.list_points()

    def clear_point(self, key: str) -> dict[str, Any]:
        self.config.coordinates.overrides.pop(key, None)
        self._save()
        return self.list_points()

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            key: [value[0], value[1]]
            for key, value in sorted(self.config.coordinates.overrides.items())
        }
        self.path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
