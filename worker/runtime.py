"""Worker runtime: builds all per-instance components and holds control state.

One :class:`WorkerContext` corresponds to one emulator instance running one
task. The :class:`Control` object implements cooperative pause/stop: the
worker thread calls :meth:`Control.checkpoint` at safe points (between
actions, while waiting for state). Stop is a control-flow signal
(:class:`TaskStoppedError`), never a hard thread kill (spec prohibition 16).
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from backend.core.config import AppConfig
from backend.core.errors import TaskStoppedError
from backend.core.logging import get_logger
from .adb_client import ADBClient, Runner
from .fgo.action_executor import ActionExecutor
from .fgo.enums import FgoState
from .fgo.state_detector import StateDetector
from .screenshot import ScreenshotProvider
from .vision.detector import VisionDetector
from .vision.templates import TemplateRegistry

log = get_logger("worker.runtime")

# A status sink receives a dict payload (mirrors the instance_status event).
StatusSink = Callable[[dict[str, Any]], None]

PHASE_LABELS: dict[str, str] = {
    "idle": "空闲",
    "quest_entry": "关卡入口",
    "support_select": "助战选择",
    "party_confirm": "队伍确认",
    "battle": "战斗执行",
    "result": "结算处理",
    "ap_recovery": "AP 恢复",
    "loop_complete": "回到入口",
    "failed": "任务失败",
}


def _noop_sink(_payload: dict[str, Any]) -> None:
    pass


class Control:
    """Cooperative pause/stop flags for a worker thread."""

    def __init__(self) -> None:
        self._stop = threading.Event()
        self._pause = threading.Event()
        self._lock = threading.Lock()

    def request_stop(self) -> None:
        log.info("stop requested")
        self._stop.set()
        self._pause.clear()  # release a paused worker so it can observe stop

    def request_pause(self) -> None:
        log.info("pause requested")
        self._pause.set()

    def resume(self) -> None:
        log.info("resume requested")
        self._pause.clear()

    @property
    def stop_requested(self) -> bool:
        return self._stop.is_set()

    @property
    def is_paused(self) -> bool:
        return self._pause.is_set()

    def checkpoint(self, poll_seconds: float = 0.2) -> None:
        """Safe-point hook. Blocks while paused; raises on stop."""
        if self._stop.is_set():
            raise TaskStoppedError("stop requested")
        while self._pause.is_set() and not self._stop.is_set():
            time.sleep(poll_seconds)
        if self._stop.is_set():
            raise TaskStoppedError("stop requested")


@dataclass
class WorkerContext:
    """Everything a quest runner / battle executor needs for one instance."""

    instance: dict[str, Any]
    config: AppConfig
    adb: ADBClient
    screenshots: ScreenshotProvider
    vision: VisionDetector
    state_detector: StateDetector
    executor: ActionExecutor
    control: Control
    status_sink: StatusSink = field(default=_noop_sink)

    # Mutable runtime state (updated as the worker progresses).
    task_id: Optional[str] = None
    current_state: FgoState = FgoState.UNKNOWN
    last_action: str = ""
    current_phase: str = "idle"
    phase_error: Optional[str] = None
    completed_count: int = 0
    failure_count: int = 0
    last_error: Optional[str] = None

    @property
    def instance_id(self) -> str:
        return self.instance["id"]

    def record_action(self, description: str) -> None:
        self.last_action = description
        log.debug("[%s] %s", self.instance_id, description)

    def set_phase(self, phase: str, *, clear_error: bool = True) -> None:
        self.current_phase = phase
        if clear_error:
            self.phase_error = None
        self.publish_status()

    def set_phase_error(self, error: str) -> None:
        self.phase_error = error
        self.publish_status()

    def publish_status(self, **extra: Any) -> None:
        payload: dict[str, Any] = {
            "instance_id": self.instance_id,
            "task_id": self.task_id,
            "state": self.current_state.value,
            "phase": self.current_phase,
            "phase_label": PHASE_LABELS.get(self.current_phase, self.current_phase),
            "phase_error": self.phase_error,
            "completed_count": self.completed_count,
            "failure_count": self.failure_count,
            "last_action": self.last_action,
        }
        payload.update(extra)
        try:
            self.status_sink(payload)
        except Exception:  # noqa: BLE001 - status publishing must never break the loop
            log.exception("status sink failed")


def build_worker_context(
    instance: dict[str, Any],
    config: AppConfig,
    *,
    runner: Optional[Runner] = None,
    status_sink: Optional[StatusSink] = None,
) -> WorkerContext:
    """Construct a fully wired WorkerContext for an instance + config."""
    adb = ADBClient(
        config.adb.path,
        instance["adb_device_id"],
        runner=runner,
        default_timeout=config.adb.command_timeout_seconds,
    )
    screenshots = ScreenshotProvider(adb)
    templates = TemplateRegistry(config.template_dir)
    vision = VisionDetector(
        templates,
        base_resolution=tuple(config.runtime.base_resolution),
        state_threshold=config.vision.state_threshold,
        template_threshold=config.vision.template_threshold,
    )
    state_detector = StateDetector(vision)
    width = instance.get("resolution_width", 1280)
    height = instance.get("resolution_height", 720)
    executor = ActionExecutor(
        adb,
        width,
        height,
        action_delay_ms=config.runtime.action_delay_ms,
        coordinate_overrides=config.coordinates.overrides,
    )
    control = Control()
    return WorkerContext(
        instance=instance,
        config=config,
        adb=adb,
        screenshots=screenshots,
        vision=vision,
        state_detector=state_detector,
        executor=executor,
        control=control,
        status_sink=status_sink or _noop_sink,
    )
