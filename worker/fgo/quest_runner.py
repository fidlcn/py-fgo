"""QuestRunner: drives a full quest and loops it (spec section 5 / MVP 1).

Single-instance, template-driven flow. Current-quest mode starts from the
support-selection screen; auto-navigation mode starts from the quest entry
screen. Each iteration: support -> party confirm -> battle -> result/AP
handling. Repeats per ``loop_config`` (count mode). Failures increment
``failure_count``; on ``stop_on_failure`` + ``max_failures`` the loop aborts.
Every failure saves an error screenshot (spec 13/17).
"""

from __future__ import annotations

import time
from datetime import datetime
from typing import Any, Optional

from backend.core.errors import (
    APInsufficientError,
    BattlePlanError,
    FgoError,
    SupportNotFoundError,
    TaskStoppedError,
)
from backend.core.logging import get_logger
from ..runtime import WorkerContext
from . import coordinates as C
from . import state_machine as sm
from .battle_executor import BattleExecutor
from .enums import FgoState
from .recovery import RecoveryHandler
from .support_selector import SupportSelector

log = get_logger("worker.fgo.quest")

# Result-like states that advance by tapping "next".
_RESULT_STATES = {
    FgoState.BATTLE_RESULT,
    FgoState.BOND_RESULT,
    FgoState.DROP_RESULT,
    FgoState.FRIEND_REQUEST,
}


class QuestRunner:
    def __init__(
        self,
        ctx: WorkerContext,
        *,
        quest_profile: Optional[dict[str, Any]] = None,
        support_profile: Optional[dict[str, Any]] = None,
        battle_plan: Optional[dict[str, Any]] = None,
        loop_config: Optional[dict[str, Any]] = None,
        ap_recovery: Optional[dict[str, Any]] = None,
    ) -> None:
        self.ctx = ctx
        self.support = SupportSelector(ctx)
        self.battle = BattleExecutor(ctx)
        self.recovery = RecoveryHandler(ctx)
        self.quest_profile: dict[str, Any] = quest_profile or {}
        self.support_profile: dict[str, Any] = support_profile or {}
        self.battle_plan: dict[str, Any] = battle_plan or {}
        self.loop_config: dict[str, Any] = loop_config or {}
        self.ap_recovery: dict[str, Any] = ap_recovery or {}

    # --- public entry ---------------------------------------------------

    def run(self) -> None:
        cfg = self.loop_config or {}
        mode = cfg.get("mode", "count")
        target = int(cfg.get("count", 1)) if mode == "count" else None
        stop_on_failure = bool(cfg.get("stop_on_failure", True))
        max_failures = int(cfg.get("max_failures", 3))

        while True:
            self.ctx.control.checkpoint()
            if mode == "count" and target is not None and self.ctx.completed_count >= target:
                log.info("reached target count %d", target)
                return
            try:
                self.run_quest()
                self.ctx.completed_count += 1
                self.ctx.last_error = None
                self.ctx.set_phase("loop_complete")
                self.ctx.publish_status(event="quest_completed")
            except TaskStoppedError:
                raise
            except APInsufficientError as exc:
                # Recovery exhausted or disabled: stop the task.
                self.ctx.last_error = str(exc)
                self.ctx.set_phase_error(self.ctx.last_error)
                self._save_error_screenshot(exc)
                raise
            except (SupportNotFoundError, BattlePlanError) as exc:
                self._handle_failure(exc, stop_on_failure, max_failures)
                raise  # these are not safely retryable
            except FgoError as exc:
                if self._handle_failure(exc, stop_on_failure, max_failures):
                    raise
                continue
            except Exception as exc:  # noqa: BLE001 - last resort, never swallow silently
                if self._handle_failure(exc, stop_on_failure, max_failures):
                    raise
                continue

    def run_quest(self) -> None:
        """Run exactly one quest: enter -> support -> party -> battle -> result."""
        entry_mode = (self.quest_profile.get("entry_mode") or "current_quest").lower()
        state, _ = sm.sense(self.ctx)
        if state == FgoState.PARTY_CONFIRM:
            self.ctx.set_phase("party_confirm")
            self.ctx.record_action("start from party confirm")
        else:
            if entry_mode == "current_quest":
                self.ctx.set_phase(
                    "support_select",
                    detail="当前关卡模式：等待助战选择状态 SUPPORT_SELECT",
                )
            elif state != FgoState.SUPPORT_SELECT:
                self._enter_quest()
            self.ctx.set_phase("support_select", detail="等待并选择助战")
            self.support.select(self.support_profile)
        self._confirm_party()
        self.ctx.set_phase("battle", detail="执行战斗方案")
        self.battle.run_plan(self.battle_plan)
        self.ctx.set_phase("result", detail="处理战斗结算")
        self._finish_result()

    # --- phases ---------------------------------------------------------

    def _enter_quest(self) -> None:
        ctx = self.ctx
        ctx.set_phase("quest_entry", detail="自动入口模式：等待关卡入口页，后续可扩展 OCR 找关卡")
        state, _ = sm.sense(ctx)
        if state in (FgoState.SUPPORT_SELECT, FgoState.PARTY_CONFIRM):
            return
        if state != FgoState.QUEST_DETAIL:
            ctx.set_phase_detail("等待关卡入口状态 QUEST_DETAIL")
            sm.wait_state(ctx, FgoState.QUEST_DETAIL, timeout=10.0)
        ctx.executor.tap_named("QUEST_DETAIL_START", C.QUEST_DETAIL_START)
        ctx.record_action("tap quest entry")
        ctx.set_phase("support_select", detail="已点击关卡，等待助战选择状态 SUPPORT_SELECT")
        sm.wait_state(ctx, FgoState.SUPPORT_SELECT, timeout=15.0)

    def _confirm_party(self) -> None:
        ctx = self.ctx
        ctx.set_phase("party_confirm", detail="等待队伍确认状态 PARTY_CONFIRM")
        state, _ = sm.sense(ctx)
        if state != FgoState.PARTY_CONFIRM:
            sm.wait_state(ctx, FgoState.PARTY_CONFIRM, timeout=10.0)
        ctx.executor.tap_quest_start()
        ctx.record_action("tap quest start (party confirm)")
        ctx.set_phase("battle", detail="已点击开始任务，等待战斗指令状态 BATTLE_COMMAND")
        sm.wait_state(ctx, FgoState.BATTLE_COMMAND, timeout=30.0)

    def _finish_result(self) -> None:
        """Tap through result screens; handle AP / friend requests; stop at quest entry."""
        ctx = self.ctx
        ticks = 0
        max_ticks = 60
        while ticks < max_ticks:
            ctx.control.checkpoint()
            state, _ = sm.sense(ctx)
            if state == FgoState.QUEST_DETAIL:
                ctx.record_action("back to quest entry; ready to repeat")
                return
            if state == FgoState.AP_INSUFFICIENT:
                ctx.set_phase("ap_recovery", detail="检测到 AP 不足，准备恢复 AP")
                if self.recovery.handle_ap_insufficient(self.ap_recovery):
                    return  # AP recovered; outer loop will re-enter the quest
                return
            if state == FgoState.FRIEND_REQUEST:
                ctx.executor.decline_friend_request()
                ctx.record_action("decline friend request")
            elif state in _RESULT_STATES:
                ctx.executor.tap_result_next()
                ctx.record_action("tap result next")
            elif state == FgoState.BATTLE_COMMAND:
                # More waves than the plan described: keep fighting with the
                # last turn's policy is unsafe; for MVP, tap attack and use
                # fallback face cards to progress.
                ctx.executor.tap_attack()
                time.sleep(1.0)
                for pos in (1, 2, 3):
                    ctx.executor.tap_face_card(pos)
                ctx.record_action("extra battle turn (fallback cards)")
            else:
                # UNKNOWN / loading: nudge with a small wait.
                time.sleep(0.7)
            ticks += 1
        log.warning("result phase did not reach quest entry after %d ticks", max_ticks)

    # --- failure handling ----------------------------------------------

    def _handle_failure(self, exc: Exception, stop_on_failure: bool, max_failures: int) -> bool:
        """Record a failure. Returns True if the loop should abort."""
        self.ctx.failure_count += 1
        self.ctx.last_error = f"{type(exc).__name__}: {exc}"
        self.ctx.set_phase_error(self.ctx.last_error)
        self._save_error_screenshot(exc)
        log.warning(
            "quest failed (%d/%d): %s",
            self.ctx.failure_count,
            max_failures,
            self.ctx.last_error,
        )
        self.ctx.publish_status(event="quest_failed", error=self.ctx.last_error)
        if stop_on_failure and self.ctx.failure_count >= max_failures:
            return True
        return not stop_on_failure

    def _save_error_screenshot(self, exc: Exception) -> Optional[str]:
        """Capture + persist the current frame for post-mortem (spec 13/17)."""
        try:
            frame = self.ctx.screenshots.capture()
        except Exception:  # noqa: BLE001
            log.exception("could not capture error screenshot")
            return None
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = self.ctx.config.screenshot_dir / f"error_{self.ctx.instance_id}_{stamp}.png"
        try:
            import cv2

            cv2.imwrite(str(path), frame.image)
        except Exception:  # noqa: BLE001
            log.exception("could not write error screenshot")
            return None
        log.info("saved error screenshot: %s (cause: %s)", path, exc)
        return str(path)
