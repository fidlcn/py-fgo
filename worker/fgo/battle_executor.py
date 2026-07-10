"""Battle plan parsing + execution (spec sections 8, 3.4).

A plan is ``waves -> turns -> actions`` plus a per-turn ``card_policy``. NP
actions are *not* tapped immediately: they are queued and replayed in the
card-select phase (spec 8.3). Every action is preceded by a control
checkpoint so pause/stop take effect at safe points.
"""

from __future__ import annotations

import time
from typing import Any, Optional

from backend.core.errors import BattlePlanError
from backend.core.logging import get_logger
from ..runtime import WorkerContext
from . import coordinates as C
from . import state_machine as sm
from .card_policy import CardPolicy
from .enums import (
    ACTION_FACE_CARDS,
    ACTION_MASTER_SKILL,
    ACTION_NOBLE_PHANTASM,
    ACTION_ORDER_CHANGE,
    ACTION_SELECT_ENEMY,
    ACTION_SERVANT_SKILL,
    ACTION_WAIT_SECONDS,
    ACTION_WAIT_STATE,
    ALL_ACTION_TYPES,
    FgoState,
)

log = get_logger("worker.fgo.battle")


def parse_battle_plan(plan: dict[str, Any]) -> dict[str, Any]:
    """Validate and normalize a battle plan. Raises :class:`BattlePlanError`."""
    if not isinstance(plan, dict):
        raise BattlePlanError("battle plan must be a dict")
    waves = plan.get("waves") or []
    if not isinstance(waves, list):
        raise BattlePlanError("waves must be a list")
    parsed_waves: list[dict[str, Any]] = []
    for wi, wave in enumerate(waves):
        if not isinstance(wave, dict):
            raise BattlePlanError(f"wave {wi + 1} must be a dict")
        turns = wave.get("turns") or []
        if not isinstance(turns, list):
            raise BattlePlanError(f"wave {wi + 1}: turns must be a list")
        parsed_turns: list[dict[str, Any]] = []
        for ti, turn in enumerate(turns):
            if not isinstance(turn, dict):
                raise BattlePlanError(f"wave {wi + 1} turn {ti + 1} must be a dict")
            actions = turn.get("actions") or []
            for ai, action in enumerate(actions):
                if not isinstance(action, dict) or "type" not in action:
                    raise BattlePlanError(
                        f"wave {wi + 1} turn {ti + 1} action {ai + 1}: missing type"
                    )
                atype = action["type"]
                if atype not in ALL_ACTION_TYPES:
                    raise BattlePlanError(
                        f"wave {wi + 1} turn {ti + 1} action {ai + 1}: unknown type {atype!r}"
                    )
            parsed_turns.append(
                {
                    "turn": turn.get("turn", ti + 1),
                    "actions": actions,
                    "card_policy": CardPolicy.from_dict(turn.get("card_policy")),
                }
            )
        parsed_waves.append({"wave": wave.get("wave", wi + 1), "turns": parsed_turns})
    if not parsed_waves:
        raise BattlePlanError("battle plan has no waves")
    return {
        "name": plan.get("name", ""),
        "expected_party": plan.get("expected_party", {}),
        "waves": parsed_waves,
    }


class BattleExecutor:
    def __init__(self, ctx: WorkerContext) -> None:
        self.ctx = ctx
        self.state = ctx.state_detector
        self.exec_ = ctx.executor

    # --- entry point ----------------------------------------------------

    def run_plan(self, plan: dict[str, Any]) -> None:
        parsed = parse_battle_plan(plan)
        for wave in parsed["waves"]:
            self.ctx.control.checkpoint()
            log.info("wave %s: %d turn(s)", wave["wave"], len(wave["turns"]))
            for turn in wave["turns"]:
                self._run_turn(turn)

    # --- single turn ----------------------------------------------------

    def _run_turn(self, turn: dict[str, Any]) -> None:
        ctx = self.ctx
        ctx.control.checkpoint()

        # 1. Wait for the command phase.
        self._wait(FgoState.BATTLE_COMMAND, timeout=20.0)
        ctx.record_action(f"turn {turn['turn']}: command phase")

        policy: CardPolicy = turn["card_policy"]
        np_slots: list[int] = []

        # 2. Execute skill/enemy actions; queue NP actions for card-select.
        for action in turn["actions"]:
            ctx.control.checkpoint()
            self._dispatch_action(action, policy, np_slots)

        # 3. Resolve NP order: queued NPs win, else the policy default.
        np_order = np_slots if np_slots else list(policy.np_order)

        # 4. Open the card-select phase.
        self.exec_.tap_attack()
        ctx.record_action("tap attack")

        # 5. Wait for card select.
        self._wait(FgoState.BATTLE_CARD_SELECT, timeout=15.0)

        # 6. Tap NP cards (spec 8.3: NP is selected here, not during command).
        for slot in np_order:
            ctx.control.checkpoint()
            self.exec_.tap_np_card(slot)
            ctx.record_action(f"tap NP card slot {slot}")

        # 7. Fill remaining slots with face cards via the policy.
        face_needed = max(0, 3 - len(np_order))
        if face_needed > 0:
            cards = ctx.vision.find_all_cards(ctx.screenshots.capture())
            positions = policy.select_face_cards(cards)
            # Honor the turn's own face_card_count if it asked for fewer.
            positions = positions[: face_needed if policy.face_card_count == 0 else policy.face_card_count]
            for pos in positions:
                ctx.control.checkpoint()
                self.exec_.tap_face_card(pos)
                ctx.record_action(f"tap face card {pos}")

        ctx.publish_status(turn=turn["turn"])

    # --- action dispatch ------------------------------------------------

    def _dispatch_action(self, action: dict[str, Any], policy: CardPolicy, np_slots: list[int]) -> None:
        ctx = self.ctx
        atype = action["type"]

        if atype == ACTION_SERVANT_SKILL:
            slot = int(action["servant_slot"])
            skill = int(action["skill"])
            self.exec_.tap_servant_skill(slot, skill)
            ctx.record_action(f"servant_skill slot={slot} skill={skill}")
            self._maybe_select_target(action.get("target_slot"))

        elif atype == ACTION_MASTER_SKILL:
            skill = int(action["skill"])
            self.exec_.tap_master_skill(skill)
            ctx.record_action(f"master_skill skill={skill}")
            self._maybe_select_target(action.get("target_slot"))

        elif atype == ACTION_SELECT_ENEMY:
            slot = int(action["target_slot"])
            self.exec_.tap_enemy(slot)
            ctx.record_action(f"select_enemy slot={slot}")

        elif atype == ACTION_NOBLE_PHANTASM:
            slot = int(action["servant_slot"])
            np_slots.append(slot)
            ctx.record_action(f"queue NP slot={slot}")

        elif atype == ACTION_FACE_CARDS:
            # Face cards are resolved from the card_policy at card-select.
            pass

        elif atype == ACTION_WAIT_SECONDS:
            seconds = float(action.get("seconds", action.get("value", 0)) or 0)
            ctx.record_action(f"wait {seconds}s")
            self._sleep_interruptible(seconds)

        elif atype == ACTION_WAIT_STATE:
            target = FgoState.from_value(action.get("state", "UNKNOWN"))
            self._wait(target, timeout=float(action.get("timeout", 15.0)))

        elif atype == ACTION_ORDER_CHANGE:
            self._order_change(action)

        else:  # pragma: no cover - parse_battle_plan rejects unknown types
            raise BattlePlanError(f"unsupported action type: {atype}")

    def _maybe_select_target(self, target_slot: Optional[Any]) -> None:
        if target_slot in (None, ""):
            return
        pt = C.PARTY_MEMBER_POSITIONS.get(int(target_slot))
        if pt is not None:
            self.exec_.tap_point(pt)
            self.ctx.record_action(f"  -> target party member {target_slot}")

    def _order_change(self, action: dict[str, Any]) -> None:
        self.exec_.tap_master_skill(3)  # open order-change panel (plugsuit)
        reserve = int(action.get("reserve_slot", 1))
        active = int(action.get("active_slot", 1))
        pr = C.ORDER_CHANGE_RESERVE.get(reserve)
        pa = C.ORDER_CHANGE_ACTIVE.get(active)
        if pr:
            self.exec_.tap_point(pr)
        if pa:
            self.exec_.tap_point(pa)
        self.exec_.tap_xy(640, 640)  # confirm
        self.ctx.record_action(f"order_change reserve={reserve} active={active}")

    # --- helpers --------------------------------------------------------

    def _wait(self, target: FgoState, timeout: float) -> None:
        sm.wait_state(self.ctx, target, timeout=timeout)

    def _sleep_interruptible(self, seconds: float) -> None:
        """Sleep in small increments so stop/pause are responsive."""
        end = time.monotonic() + max(0.0, seconds)
        while time.monotonic() < end:
            self.ctx.control.checkpoint()
            time.sleep(min(0.2, end - time.monotonic()))
