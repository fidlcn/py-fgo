"""QuestRunner: drives a full quest and loops it (spec section 5 / MVP 1).

Single-instance, starts from the current quest-detail screen. Each iteration:
enter -> support -> party confirm -> battle -> result/AP handling. Repeats per
``loop_config`` (count mode). Failures increment ``failure_count``; on
``stop_on_failure`` + ``max_failures`` the loop aborts. Every failure saves an
error screenshot (spec 13/17).
"""

from __future__ import annotations

import time
from datetime import datetime
from typing import Any, Optional

from backend.core.errors import (
    APInsufficientError,
    BattlePlanError,
    FgoError,
    StateDetectionError,
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
        support_profile: Optional[dict[str, Any]] = None,
        battle_plan: Optional[dict[str, Any]] = None,
        loop_config: Optional[dict[str, Any]] = None,
        ap_recovery: Optional[dict[str, Any]] = None,
    ) -> None:
        self.ctx = ctx
        self.support = SupportSelector(ctx)
        self.battle = BattleExecutor(ctx)
        self.recovery = RecoveryHandler(ctx)
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
                self.ctx.publish_status(event="quest_completed")
            except TaskStoppedError:
                raise
            except APInsufficientError as exc:
                # Recovery exhausted or disabled: stop the task.
                self.ctx.last_error = str(exc)
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
        self._enter_quest()
        self.support.select(self.support_profile)
        self._confirm_party()
        self.battle.run_plan(self.battle_plan)
        self._finish_result()

    # --- phases ---------------------------------------------------------

    def _enter_quest(self) -> None:
        ctx = self.ctx
        state, _ = sm.sense(ctx)
        if state == FgoState.SUPPORT_SELECT:
            return
        if state != FgoState.QUEST_DETAIL:
            try:
                sm.wait_state(ctx, FgoState.QUEST_DETAIL, timeout=10.0)
            except Exception:  # noqa: BLE001 - proceed optimistically
                log.warning("not on QUEST_DETAIL; proceeding optimistically")
        ctx.executor.tap_point(C.QUEST_DETAIL_START)
        ctx.record_action("tap quest start (from detail)")
        try:
            sm.wait_state(ctx, FgoState.SUPPORT_SELECT, timeout=12.0)
        except StateDetectionError:
            # FGO can show the "auto-burn target" confirmation dialog before
            # support selection. It is not a normal persistent state, so use a
            # conservative coordinate fallback only after support did not appear.
            ctx.executor.tap_point(C.QUEST_AUTO_BURN_CONFIRM)
            ctx.record_action("confirm auto-burn target dialog")
            sm.wait_state(ctx, FgoState.SUPPORT_SELECT, timeout=15.0)

    def _confirm_party(self) -> None:
        ctx = self.ctx
        state, _ = sm.sense(ctx)
        if state != FgoState.PARTY_CONFIRM:
            try:
                sm.wait_state(ctx, FgoState.PARTY_CONFIRM, timeout=10.0)
            except Exception:  # noqa: BLE001
                pass
        ctx.executor.tap_quest_start()
        ctx.record_action("tap quest start (party confirm)")
        sm.wait_state(ctx, FgoState.BATTLE_COMMAND, timeout=30.0)

    def _finish_result(self) -> None:
        """Tap through result screens; handle AP / friend requests; stop at detail."""
        ctx = self.ctx
        ticks = 0
        max_ticks = 60
        while ticks < max_ticks:
            ctx.control.checkpoint()
            state, _ = sm.sense(ctx)
            if state == FgoState.QUEST_DETAIL:
                ctx.record_action("back to quest detail; ready to repeat")
                return
            if state == FgoState.AP_INSUFFICIENT:
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
        log.warning("result phase did not reach QUEST_DETAIL after %d ticks", max_ticks)

    # --- failure handling ----------------------------------------------

    def _handle_failure(self, exc: Exception, stop_on_failure: bool, max_failures: int) -> bool:
        """Record a failure. Returns True if the loop should abort."""
        self.ctx.failure_count += 1
        self.ctx.last_error = f"{type(exc).__name__}: {exc}"
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
