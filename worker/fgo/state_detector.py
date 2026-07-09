"""FGO state detection config + detector (spec section 6).

Each state is described by: templates, optional ROI, minimum confidence,
timeout, and an on-timeout policy. The :class:`StateDetector` adapts the
generic :class:`VisionDetector` to the FGO enum and adds ``wait_for_state``
which polls screenshots until a state is seen or the timeout fires.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

from backend.core.errors import StateDetectionError
from backend.core.logging import get_logger
from ..screenshot import Frame, ScreenshotProvider
from ..vision.detector import DetectionResult, StateDef, VisionDetector
from ..vision.roi import ROI
from .enums import FgoState

log = get_logger("worker.fgo.state")

# on_timeout policies
ON_TIMEOUT_RETRY = "retry"
ON_TIMEOUT_ERROR = "error"
ON_TIMEOUT_RECOVER = "recover"


@dataclass
class FgoStateDef:
    state: FgoState
    templates: list[str]
    roi: Optional[ROI] = None
    minimum_confidence: float = 0.85
    timeout_seconds: float = 15.0
    on_timeout: str = ON_TIMEOUT_ERROR


# State registry. Template ids resolve under assets/templates/<id>.png.
# MVP focus states are populated; others are present but optional to detect.
STATE_REGISTRY: dict[FgoState, FgoStateDef] = {
    FgoState.QUEST_DETAIL: FgoStateDef(
        FgoState.QUEST_DETAIL,
        ["quest/detail_start_quest"],
        minimum_confidence=0.85,
        timeout_seconds=15.0,
        on_timeout=ON_TIMEOUT_ERROR,
    ),
    FgoState.SUPPORT_SELECT: FgoStateDef(
        FgoState.SUPPORT_SELECT,
        ["support/select_title"],
        minimum_confidence=0.85,
        timeout_seconds=15.0,
        on_timeout=ON_TIMEOUT_ERROR,
    ),
    FgoState.PARTY_CONFIRM: FgoStateDef(
        FgoState.PARTY_CONFIRM,
        ["party/confirm_start"],
        minimum_confidence=0.85,
        timeout_seconds=15.0,
        on_timeout=ON_TIMEOUT_ERROR,
    ),
    FgoState.BATTLE_COMMAND: FgoStateDef(
        FgoState.BATTLE_COMMAND,
        ["battle/attack_button"],
        minimum_confidence=0.85,
        timeout_seconds=20.0,
        on_timeout=ON_TIMEOUT_ERROR,
    ),
    FgoState.BATTLE_CARD_SELECT: FgoStateDef(
        FgoState.BATTLE_CARD_SELECT,
        ["battle/card_select_title"],
        minimum_confidence=0.85,
        timeout_seconds=15.0,
        on_timeout=ON_TIMEOUT_ERROR,
    ),
    FgoState.BATTLE_RESULT: FgoStateDef(
        FgoState.BATTLE_RESULT,
        ["battle/result_next"],
        minimum_confidence=0.85,
        timeout_seconds=20.0,
        on_timeout=ON_TIMEOUT_ERROR,
    ),
    FgoState.AP_INSUFFICIENT: FgoStateDef(
        FgoState.AP_INSUFFICIENT,
        ["recovery/ap_insufficient_title"],
        minimum_confidence=0.85,
        timeout_seconds=10.0,
        on_timeout=ON_TIMEOUT_RETRY,
    ),
    # Lower-priority / informational states (no template required for MVP).
    FgoState.HOME: FgoStateDef(FgoState.HOME, ["common/home_menu"]),
    FgoState.QUEST_LIST: FgoStateDef(FgoState.QUEST_LIST, ["quest/list_title"]),
    FgoState.BATTLE_LOADING: FgoStateDef(FgoState.BATTLE_LOADING, ["battle/loading"]),
    FgoState.BOND_RESULT: FgoStateDef(FgoState.BOND_RESULT, ["battle/bond_result"]),
    FgoState.DROP_RESULT: FgoStateDef(FgoState.DROP_RESULT, ["battle/drop_result"]),
    FgoState.FRIEND_REQUEST: FgoStateDef(FgoState.FRIEND_REQUEST, ["battle/friend_request"]),
    FgoState.NETWORK_ERROR: FgoStateDef(FgoState.NETWORK_ERROR, ["common/network_error"]),
    FgoState.APP_CRASHED: FgoStateDef(FgoState.APP_CRASHED, ["common/app_crashed"]),
}


def _to_vision_defs(registry: dict[FgoState, FgoStateDef]) -> list[StateDef]:
    return [
        StateDef(
            state=d.state.value,
            templates=d.templates,
            roi=d.roi,
            min_confidence=d.minimum_confidence,
        )
        for d in registry.values()
    ]


class StateDetector:
    """Bridges the generic VisionDetector and the FgoState enum."""

    def __init__(
        self,
        vision: VisionDetector,
        registry: Optional[dict[FgoState, FgoStateDef]] = None,
    ) -> None:
        self.vision = vision
        self.registry = registry if registry is not None else dict(STATE_REGISTRY)
        self.vision.set_state_defs(_to_vision_defs(self.registry))

    def detect(self, frame: Frame) -> tuple[FgoState, float, Optional[str]]:
        res: DetectionResult = self.vision.detect_state(frame)
        return FgoState.from_value(res.state), res.confidence, res.matched_template

    def wait_for_state(
        self,
        target: FgoState,
        screenshots: ScreenshotProvider,
        *,
        timeout: Optional[float] = None,
        interval_ms: int = 700,
        should_stop: Optional[Callable[[], bool]] = None,
    ) -> FgoState:
        """Poll until ``target`` is detected or the timeout fires.

        Raises :class:`StateDetectionError` on timeout. Honors an external
        ``should_stop`` so pause/stop requests interrupt waiting.
        """
        import time

        state_def = self.registry.get(target)
        deadline_timeout = state_def.timeout_seconds if state_def else 15.0
        if timeout is not None:
            deadline_timeout = timeout
        deadline = time.monotonic() + deadline_timeout
        interval = max(0.1, interval_ms / 1000.0)
        last = FgoState.UNKNOWN
        while time.monotonic() < deadline:
            if should_stop and should_stop():
                raise StateDetectionError(f"interrupted while waiting for {target.value}")
            frame = screenshots.capture()
            last, conf, _ = self.detect(frame)
            log.debug("wait_for_state %s: now=%s conf=%.2f", target.value, last.value, conf)
            if last == target:
                return last
            time.sleep(interval)
        raise StateDetectionError(
            f"timed out after {deadline_timeout:.1f}s waiting for {target.value} (last={last.value})"
        )
