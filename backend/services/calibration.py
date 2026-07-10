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
from worker.fgo import coordinates as C
from worker.fgo.coordinates import Point


POINTS: dict[str, dict[str, Any]] = {
    "QUEST_DETAIL_START": {
        "label": "关卡入口页：点击关卡",
        "category": "关卡",
        "default": C.QUEST_DETAIL_START,
    },
    "QUEST_START_BUTTON": {
        "label": "队伍确认页：开始任务",
        "category": "关卡",
        "default": C.QUEST_START_BUTTON,
    },
    "ATTACK_BUTTON": {
        "label": "战斗：Attack",
        "category": "战斗指令",
        "default": C.ATTACK_BUTTON,
    },
    "SKILL_CONFIRM_BUTTON": {
        "label": "战斗：技能确认",
        "category": "战斗指令",
        "default": C.SKILL_CONFIRM_BUTTON,
    },
    **{
        f"SERVANT_SKILL_{slot}_{skill}": {
            "label": f"战斗：从者 {slot} 技能 {skill}",
            "category": "从者技能",
            "default": point,
        }
        for (slot, skill), point in C.SERVANT_SKILLS.items()
    },
    **{
        f"MASTER_SKILL_{skill}": {
            "label": f"战斗：御主技能 {skill}",
            "category": "御主技能",
            "default": point,
        }
        for skill, point in C.MASTER_SKILLS.items()
    },
    **{
        f"ENEMY_TARGET_{slot}": {
            "label": f"战斗：敌方目标 {slot}",
            "category": "目标选择",
            "default": point,
        }
        for slot, point in C.ENEMY_TARGETS.items()
    },
    **{
        f"PARTY_MEMBER_TARGET_{slot}": {
            "label": f"战斗：我方目标 {slot}",
            "category": "目标选择",
            "default": point,
        }
        for slot, point in C.PARTY_MEMBER_POSITIONS.items()
    },
    **{
        f"NP_CARD_{slot}": {
            "label": f"选卡：宝具卡 {slot}",
            "category": "选卡",
            "default": point,
        }
        for slot, point in C.NP_CARDS.items()
    },
    **{
        f"FACE_CARD_{pos}": {
            "label": f"选卡：指令卡 {pos}",
            "category": "选卡",
            "default": point,
        }
        for pos, point in C.FACE_CARD_POSITIONS.items()
    },
    **{
        f"ORDER_CHANGE_RESERVE_{slot}": {
            "label": f"换人：后排 {slot}",
            "category": "换人",
            "default": point,
        }
        for slot, point in C.ORDER_CHANGE_RESERVE.items()
    },
    **{
        f"ORDER_CHANGE_ACTIVE_{slot}": {
            "label": f"换人：前排 {slot}",
            "category": "换人",
            "default": point,
        }
        for slot, point in C.ORDER_CHANGE_ACTIVE.items()
    },
    "ORDER_CHANGE_CONFIRM": {
        "label": "换人：确认",
        "category": "换人",
        "default": C.ORDER_CHANGE_CONFIRM,
    },
    "SUPPORT_FIRST_RECOMMENDED": {
        "label": "助战：推荐第一个",
        "category": "助战",
        "default": C.SUPPORT_FIRST_RECOMMENDED,
    },
    **{
        f"SUPPORT_CLASS_{name.upper()}": {
            "label": f"助战：职阶 {name}",
            "category": "助战",
            "default": point,
        }
        for name, point in C.SUPPORT_CLASS_TABS.items()
    },
    "SUPPORT_SCROLL_START": {
        "label": "助战：滚动起点",
        "category": "助战",
        "default": C.SUPPORT_SCROLL_START,
    },
    "SUPPORT_SCROLL_END": {
        "label": "助战：滚动终点",
        "category": "助战",
        "default": C.SUPPORT_SCROLL_END,
    },
    "SUPPORT_REFRESH": {
        "label": "助战：刷新",
        "category": "助战",
        "default": C.SUPPORT_REFRESH,
    },
    "SUPPORT_REFRESH_CONFIRM": {
        "label": "助战：刷新确认",
        "category": "助战",
        "default": C.SUPPORT_REFRESH_CONFIRM,
    },
    "RESULT_NEXT": {
        "label": "结算：下一步",
        "category": "结算",
        "default": C.RESULT_NEXT,
    },
    "FRIEND_REQUEST_DECLINE": {
        "label": "好友申请：拒绝",
        "category": "结算",
        "default": C.FRIEND_REQUEST_DECLINE,
    },
    "REPEAT_CONFIRM_CONTINUE": {
        "label": "连续出击确认：连续出击",
        "category": "结算",
        "default": C.REPEAT_CONFIRM_CONTINUE,
    },
    "REPEAT_CONFIRM_CLOSE": {
        "label": "连续出击确认：关闭",
        "category": "结算",
        "default": C.REPEAT_CONFIRM_CLOSE,
    },
    **{
        f"AP_RECOVERY_ITEM_{tier.upper()}": {
            "label": f"AP 恢复：{tier} 道具",
            "category": "AP 恢复",
            "default": point,
        }
        for tier, point in C.AP_RECOVERY_ITEM_ROWS.items()
    },
    "AP_RECOVERY_CONFIRM": {
        "label": "AP 恢复：确认",
        "category": "AP 恢复",
        "default": C.AP_RECOVERY_CONFIRM,
    },
    "AP_RECOVERY_CLOSE": {
        "label": "AP 恢复：关闭",
        "category": "AP 恢复",
        "default": C.AP_RECOVERY_CLOSE,
    },
}


class CalibrationService:
    def __init__(self, config: AppConfig, path: Path = DEFAULT_COORDINATES_PATH) -> None:
        self.config = config
        self.path = path

    def list_points(self) -> dict[str, Any]:
        available = []
        for key, spec in POINTS.items():
            default: Point = spec["default"]
            override = self.config.coordinates.overrides.get(key)
            current = override or (default.x, default.y)
            available.append(
                {
                    "key": key,
                    "label": spec["label"],
                    "category": spec["category"],
                    "default": [default.x, default.y],
                    "current": [current[0], current[1]],
                    "overridden": override is not None,
                }
            )
        return {
            "available": available,
            "overrides": {
                key: [value[0], value[1]]
                for key, value in self.config.coordinates.overrides.items()
            },
        }

    def export_points(self) -> dict[str, Any]:
        points = {}
        for key, spec in POINTS.items():
            default: Point = spec["default"]
            override = self.config.coordinates.overrides.get(key)
            current = override or (default.x, default.y)
            points[key] = {
                "label": spec["label"],
                "category": spec["category"],
                "default": [default.x, default.y],
                "override": [override[0], override[1]] if override else None,
                "current": [current[0], current[1]],
            }
        return {
            "base_resolution": [C.BASE_WIDTH, C.BASE_HEIGHT],
            "points": points,
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
