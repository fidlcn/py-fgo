"""One-click startup orchestration.

Quick start is intentionally conservative: it scans online ADB devices, picks
one where FGO is the foreground app, verifies the current screen is a safe
entry state, ensures default profiles exist, creates a task, then starts it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from backend.core.config import AppConfig
from backend.core.errors import ConflictError, ValidationError
from backend.core.logging import get_logger
from backend.db import repositories as r
from backend.db.session import get_db
from worker.adb_client import ADBClient
from worker.fgo.enums import FgoState
from worker.runtime import build_worker_context

from .instance_manager import InstanceManager
from .task_manager import TaskManager

log = get_logger("services.quick_start")


SAFE_START_STATES = {
    FgoState.QUEST_DETAIL,
    FgoState.SUPPORT_SELECT,
    FgoState.PARTY_CONFIRM,
}


@dataclass
class PreflightResult:
    instance: dict[str, Any]
    package_name: str
    state: FgoState
    confidence: float
    matched_template: Optional[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "instance": self.instance,
            "package_name": self.package_name,
            "state": self.state.value,
            "confidence": self.confidence,
            "matched_template": self.matched_template,
        }


class QuickStartService:
    def __init__(
        self,
        config: AppConfig,
        instance_manager: InstanceManager,
        task_manager: TaskManager,
        *,
        db_factory=None,
    ) -> None:
        self.config = config
        self.instances = instance_manager
        self.tasks = task_manager
        self._db_factory = db_factory or get_db

    def preflight(self) -> dict[str, Any]:
        return self._run_preflight().to_dict()

    def start(self) -> dict[str, Any]:
        preflight = self._run_preflight()
        defaults = self._ensure_default_profiles()
        task = self.tasks.create_task(
            {
                "instance_id": preflight.instance["id"],
                "quest_profile_id": defaults["quest_profile_id"],
                "support_profile_id": defaults["support_profile_id"],
                "battle_plan_id": defaults["battle_plan_id"],
                "loop_config": {"mode": "count", "count": 1, "stop_on_failure": True, "max_failures": 1},
                "ap_recovery": {"enabled": False, "priority": ["bronze", "silver", "gold"], "max_items": 0},
            }
        )
        started = self.tasks.start(task["id"])
        return {
            "preflight": preflight.to_dict(),
            "task": started,
            "defaults": defaults,
        }

    def _run_preflight(self) -> PreflightResult:
        candidates = [d for d in self.instances.scan_adb() if d.get("state") == "device"]
        if not candidates:
            raise ValidationError(
                "未检测到在线的 MuMu/ADB 设备，请先启动模拟器并确认 adb devices 可见。",
                code="NO_ADB_DEVICE",
            )

        package_names = tuple(self.config.fgo.package_names)
        fgo_device: Optional[dict[str, str]] = None
        package_name: Optional[str] = None
        for device in candidates:
            client = ADBClient(
                self.config.adb.path,
                device["device_id"],
                default_timeout=self.config.adb.command_timeout_seconds,
            )
            if not client.is_online():
                continue
            try:
                current = client.foreground_package(package_names)
            except Exception as exc:  # noqa: BLE001
                log.debug("foreground package check failed for %s: %s", device["device_id"], exc)
                continue
            if current in package_names:
                fgo_device = device
                package_name = current
                break

        if fgo_device is None or package_name is None:
            raise ValidationError(
                "检测到模拟器，但前台不是 FGO。请先在 MuMu 中打开 FGO，并停留在关卡入口、助战选择或队伍确认页。",
                code="FGO_NOT_RUNNING",
            )

        instance = self._ensure_instance(fgo_device["device_id"])
        ctx = build_worker_context(instance, self.config)
        frame = ctx.screenshots.capture()
        state, confidence, matched_template = ctx.state_detector.detect(frame)
        if state not in SAFE_START_STATES:
            raise ValidationError(
                f"FGO 已运行，但当前界面不支持一键启动：{state.value}。请进入关卡入口、助战选择或队伍确认页后重试。",
                code="UNSUPPORTED_START_STATE",
            )
        return PreflightResult(instance, package_name, state, confidence, matched_template)

    def _ensure_instance(self, adb_device_id: str) -> dict[str, Any]:
        db = self._db_factory()
        s = db.session()
        try:
            inst = r.get_instance_by_device(s, adb_device_id)
            if inst is None:
                inst = r.create_instance(
                    s,
                    {
                        "name": f"MuMu {adb_device_id}",
                        "emulator_type": "mumu",
                        "adb_device_id": adb_device_id,
                        "resolution_width": self.config.runtime.base_resolution[0],
                        "resolution_height": self.config.runtime.base_resolution[1],
                        "screenshot_interval_ms": self.config.runtime.screenshot_interval_ms,
                        "status": "idle",
                    },
                )
                s.commit()
            return inst.to_dict()
        finally:
            s.close()

    def _ensure_default_profiles(self) -> dict[str, str]:
        db = self._db_factory()
        s = db.session()
        try:
            quest = next((q for q in r.list_quest_profiles(s) if q.name == "一键启动：当前关卡"), None)
            if quest is None:
                quest = r.create_quest_profile(
                    s,
                    {
                        "name": "一键启动：当前关卡",
                        "category": "daily",
                        "entry_mode": "current_quest",
                        "server_region": "cn",
                        "navigation_config": {},
                    },
                )

            support = next((p for p in r.list_support_profiles(s) if p.name == "一键启动：推荐助战"), None)
            if support is None:
                support = r.create_support_profile(
                    s,
                    {
                        "name": "一键启动：推荐助战",
                        "class_filter": "all",
                        "preferred": [],
                        "fallback_mode": "first_recommended",
                        "max_scroll_pages": 0,
                        "max_refresh_count": 0,
                    },
                )

            battle = next((b for b in r.list_battle_plans(s) if b.name == "一键启动：默认补卡"), None)
            if battle is None:
                battle = r.create_battle_plan(
                    s,
                    {
                        "name": "一键启动：默认补卡",
                        "expected_party": {},
                        "waves": [
                            {
                                "wave": 1,
                                "turns": [
                                    {
                                        "turn": 1,
                                        "actions": [{"type": "face_cards"}],
                                        "card_policy": {
                                            "face_card_count": 3,
                                            "fallback_positions": [1, 2, 3],
                                        },
                                    }
                                ],
                            }
                        ],
                        "version": 1,
                    },
                )

            s.commit()
            return {
                "quest_profile_id": quest.id,
                "support_profile_id": support.id,
                "battle_plan_id": battle.id,
            }
        except ConflictError:
            s.rollback()
            raise
        finally:
            s.close()
