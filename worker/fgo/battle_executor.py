"""Battle plan parsing + execution (spec sections 8, 3.4).

A plan is ``waves -> turns -> actions`` plus a per-turn ``card_policy``. NP
actions are *not* tapped immediately: they are queued and replayed in the
card-select phase (spec 8.3). Every action is preceded by a control
checkpoint so pause/stop take effect at safe points.
"""

from __future__ import annotations

import time
from typing import Any

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

TARGET_NONE = "none"
TARGET_ALLY = "ally"
TARGET_ENEMY = "enemy"
VALID_TARGET_TYPES = {TARGET_NONE, TARGET_ALLY, TARGET_ENEMY}

CONFIRM_AUTO = "auto"
CONFIRM_ALWAYS = "always"
CONFIRM_NEVER = "never"
VALID_CONFIRM_MODES = {CONFIRM_AUTO, CONFIRM_ALWAYS, CONFIRM_NEVER}


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
            parsed_actions: list[dict[str, Any]] = []
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
                parsed_actions.append(_normalize_action(action, wi + 1, ti + 1, ai + 1))
            parsed_turns.append(
                {
                    "turn": turn.get("turn", ti + 1),
                    "actions": parsed_actions,
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


def _normalize_action(action: dict[str, Any], wave: int, turn: int, index: int) -> dict[str, Any]:
    parsed = dict(action)
    parsed["action_index"] = index
    atype = parsed["type"]

    if atype in (ACTION_SERVANT_SKILL, ACTION_MASTER_SKILL):
        if atype == ACTION_SERVANT_SKILL:
            _require_slot(parsed, "servant_slot", wave, turn, index, valid={1, 2, 3})
        _require_slot(parsed, "skill", wave, turn, index, valid={1, 2, 3})
        target_slot = int(parsed.get("target_slot") or 0)
        target_type = (parsed.get("target_type") or "").lower()
        if not target_type:
            target_type = TARGET_ALLY if target_slot in (1, 2, 3) else TARGET_NONE
        if target_type not in VALID_TARGET_TYPES:
            raise BattlePlanError(
                f"wave {wave} turn {turn} action {index}: invalid target_type {target_type!r}"
            )
        if target_type == TARGET_NONE:
            target_slot = 0
        elif target_slot not in (1, 2, 3):
            raise BattlePlanError(
                f"wave {wave} turn {turn} action {index}: target_slot must be 1..3 for {target_type}"
            )
        confirm = parsed.get("confirm", CONFIRM_AUTO)
        if isinstance(confirm, bool):
            confirm = CONFIRM_ALWAYS if confirm else CONFIRM_NEVER
        confirm = str(confirm or CONFIRM_AUTO).lower()
        if confirm not in VALID_CONFIRM_MODES:
            raise BattlePlanError(
                f"wave {wave} turn {turn} action {index}: invalid confirm mode {confirm!r}"
            )
        parsed["target_type"] = target_type
        parsed["target_slot"] = target_slot
        parsed["confirm"] = confirm
        parsed["timeout"] = float(parsed.get("timeout", 8.0) or 8.0)

    elif atype == ACTION_SELECT_ENEMY:
        _require_slot(parsed, "target_slot", wave, turn, index, valid={1, 2, 3})

    elif atype == ACTION_NOBLE_PHANTASM:
        _require_slot(parsed, "servant_slot", wave, turn, index, valid={1, 2, 3})

    elif atype == ACTION_ORDER_CHANGE:
        _require_slot(parsed, "reserve_slot", wave, turn, index, valid={1, 2, 3})
        _require_slot(parsed, "active_slot", wave, turn, index, valid={1, 2, 3})
        parsed["timeout"] = float(parsed.get("timeout", 8.0) or 8.0)

    return parsed


def _require_slot(
    action: dict[str, Any],
    key: str,
    wave: int,
    turn: int,
    index: int,
    *,
    valid: set[int],
) -> int:
    try:
        value = int(action[key])
    except (KeyError, TypeError, ValueError) as exc:
        raise BattlePlanError(
            f"wave {wave} turn {turn} action {index}: {key} is required"
        ) from exc
    if value not in valid:
        raise BattlePlanError(
            f"wave {wave} turn {turn} action {index}: {key} must be one of {sorted(valid)}"
        )
    action[key] = value
    return value


class BattleExecutor:
    def __init__(self, ctx: WorkerContext) -> None:
        self.ctx = ctx
        self.exec_ = ctx.executor

    # --- entry point ----------------------------------------------------

    def run_plan(self, plan: dict[str, Any]) -> None:
        parsed = parse_battle_plan(plan)
        for wave in parsed["waves"]:
            self.ctx.control.checkpoint()
            log.info("wave %s: %d turn(s)", wave["wave"], len(wave["turns"]))
            for turn in wave["turns"]:
                self._run_turn(wave["wave"], turn)

    # --- single turn ----------------------------------------------------

    def _run_turn(self, wave_no: int, turn: dict[str, Any]) -> None:
        ctx = self.ctx
        ctx.control.checkpoint()

        # 1. Wait for the command phase.
        self._wait(FgoState.BATTLE_COMMAND, timeout=20.0)
        ctx.record_action(f"turn {turn['turn']}: command phase")
        ctx.publish_status(wave=wave_no, turn=turn["turn"], action_index=0)

        policy: CardPolicy = turn["card_policy"]
        np_slots: list[int] = []

        # 2. Execute skill/enemy actions; queue NP actions for card-select.
        for action in turn["actions"]:
            ctx.control.checkpoint()
            self._dispatch_action(action, policy, np_slots, wave_no, turn["turn"])

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
            frame = ctx.screenshots.capture()
            if not ctx.vision.is_np_ready(frame, slot):
                self._fail(wave_no, turn["turn"], 0, ACTION_NOBLE_PHANTASM, f"np slot {slot} is not ready")
            self.exec_.tap_np_card(slot)
            ctx.record_action(f"tap NP card slot {slot}")
            ctx.publish_status(wave=wave_no, turn=turn["turn"], action=ACTION_NOBLE_PHANTASM)

        # 7. Fill remaining slots with face cards via the policy.
        face_needed = max(0, 3 - len(np_order))
        if face_needed > 0:
            cards = ctx.vision.find_all_cards(ctx.screenshots.capture())
            positions = policy.select_face_cards(cards)
            positions = positions[:face_needed]
            if len(positions) < face_needed:
                self._fail(
                    wave_no,
                    turn["turn"],
                    0,
                    ACTION_FACE_CARDS,
                    f"not enough recognized face cards: need={face_needed}, got={len(positions)}",
                )
            for pos in positions:
                ctx.control.checkpoint()
                self.exec_.tap_face_card(pos)
                ctx.record_action(f"tap face card {pos}")
                ctx.publish_status(wave=wave_no, turn=turn["turn"], action=ACTION_FACE_CARDS)

        ctx.publish_status(turn=turn["turn"])

    # --- action dispatch ------------------------------------------------

    def _dispatch_action(
        self,
        action: dict[str, Any],
        policy: CardPolicy,
        np_slots: list[int],
        wave: int,
        turn: int,
    ) -> None:
        ctx = self.ctx
        atype = action["type"]
        action_index = int(action.get("action_index", 0))
        ctx.publish_status(wave=wave, turn=turn, action_index=action_index, action=atype)

        if atype == ACTION_SERVANT_SKILL:
            self._use_skill(action, wave, turn)

        elif atype == ACTION_MASTER_SKILL:
            self._use_skill(action, wave, turn)

        elif atype == ACTION_SELECT_ENEMY:
            slot = int(action["target_slot"])
            self.exec_.tap_enemy(slot)
            ctx.record_action(f"select_enemy slot={slot}")
            ctx.publish_status(wave=wave, turn=turn, action_index=action_index, action=atype)

        elif atype == ACTION_NOBLE_PHANTASM:
            slot = int(action["servant_slot"])
            np_slots.append(slot)
            ctx.record_action(f"queue NP slot={slot}")
            ctx.publish_status(wave=wave, turn=turn, action_index=action_index, action=atype)

        elif atype == ACTION_FACE_CARDS:
            # Face cards are resolved from the card_policy at card-select.
            pass

        elif atype == ACTION_WAIT_SECONDS:
            seconds = float(action.get("seconds", action.get("value", 0)) or 0)
            ctx.record_action(f"wait {seconds}s")
            ctx.publish_status(wave=wave, turn=turn, action_index=action_index, action=atype)
            self._sleep_interruptible(seconds)

        elif atype == ACTION_WAIT_STATE:
            target = FgoState.from_value(action.get("state", "UNKNOWN"))
            self._wait(target, timeout=float(action.get("timeout", 15.0)))

        elif atype == ACTION_ORDER_CHANGE:
            self._order_change(action, wave, turn)

        else:  # pragma: no cover - parse_battle_plan rejects unknown types
            raise BattlePlanError(f"unsupported action type: {atype}")

    def _use_skill(self, action: dict[str, Any], wave: int, turn: int) -> None:
        atype = action["type"]
        action_index = int(action.get("action_index", 0))
        skill = int(action["skill"])
        frame = self.ctx.screenshots.capture()
        if atype == ACTION_SERVANT_SKILL:
            slot = int(action["servant_slot"])
            if not self.ctx.vision.is_skill_ready(frame, slot, skill):
                self._fail(wave, turn, action_index, atype, f"servant {slot} skill {skill} is not ready")
            self.exec_.tap_servant_skill(slot, skill)
            self.ctx.record_action(f"servant_skill slot={slot} skill={skill}")
        else:
            if not self.ctx.vision.is_skill_ready(frame, 0, skill):
                self._fail(wave, turn, action_index, atype, f"master skill {skill} is not ready")
            self.exec_.tap_master_skill(skill)
            self.ctx.record_action(f"master_skill skill={skill}")
        self.ctx.publish_status(wave=wave, turn=turn, action_index=action_index, action=atype)
        self._resolve_skill_dialogs(action, wave, turn)

    def _resolve_skill_dialogs(self, action: dict[str, Any], wave: int, turn: int) -> None:
        target_type = action["target_type"]
        target_slot = int(action["target_slot"])
        confirm = action["confirm"]
        action_index = int(action.get("action_index", 0))
        atype = action["type"]
        deadline = time.monotonic() + float(action.get("timeout", 8.0))
        confirmed = False
        selected_target = False

        while time.monotonic() < deadline:
            self.ctx.control.checkpoint()
            state, _ = sm.sense(self.ctx)
            if state == FgoState.SKILL_CONFIRM:
                if confirm == CONFIRM_NEVER:
                    self._fail(wave, turn, action_index, atype, "unexpected skill confirmation dialog")
                self.exec_.tap_skill_confirm()
                confirmed = True
                self.ctx.record_action("tap skill confirm")
                self.ctx.publish_status(wave=wave, turn=turn, action_index=action_index, action=atype)
            elif state == FgoState.ALLY_TARGET_SELECT:
                if target_type != TARGET_ALLY:
                    self._fail(wave, turn, action_index, atype, "unexpected ally target selection")
                self.exec_.tap_party_member_target(target_slot)
                selected_target = True
                self.ctx.record_action(f"target ally slot={target_slot}")
                self.ctx.publish_status(wave=wave, turn=turn, action_index=action_index, action=atype)
            elif state == FgoState.ENEMY_TARGET_SELECT:
                if target_type != TARGET_ENEMY:
                    self._fail(wave, turn, action_index, atype, "unexpected enemy target selection")
                self.exec_.tap_enemy(target_slot)
                selected_target = True
                self.ctx.record_action(f"target enemy slot={target_slot}")
                self.ctx.publish_status(wave=wave, turn=turn, action_index=action_index, action=atype)
            elif state == FgoState.BATTLE_COMMAND:
                if confirm == CONFIRM_ALWAYS and not confirmed:
                    self._fail(wave, turn, action_index, atype, "expected skill confirmation dialog")
                if target_type != TARGET_NONE and not selected_target:
                    self._fail(wave, turn, action_index, atype, f"expected {target_type} target selection")
                return
            time.sleep(0.25)

        self._fail(wave, turn, action_index, atype, "timed out resolving skill dialogs")

    def _order_change(self, action: dict[str, Any], wave: int, turn: int) -> None:
        action_index = int(action.get("action_index", 0))
        self.exec_.tap_master_skill(3)  # open order-change panel (plugsuit)
        try:
            self._wait(FgoState.ORDER_CHANGE_SELECT, timeout=float(action.get("timeout", 8.0)))
        except Exception as exc:
            self._fail(wave, turn, action_index, ACTION_ORDER_CHANGE, str(exc))
        reserve = int(action.get("reserve_slot", 1))
        active = int(action.get("active_slot", 1))
        if reserve in C.ORDER_CHANGE_RESERVE:
            self.exec_.tap_order_change_reserve(reserve)
        if active in C.ORDER_CHANGE_ACTIVE:
            self.exec_.tap_order_change_active(active)
        self.exec_.tap_order_change_confirm()
        self.ctx.record_action(f"order_change reserve={reserve} active={active}")
        self.ctx.publish_status(wave=wave, turn=turn, action_index=action_index, action=ACTION_ORDER_CHANGE)

    def _fail(self, wave: int, turn: int, action_index: int, action: str, reason: str) -> None:
        raise BattlePlanError(
            f"battle action failed: wave={wave} turn={turn} "
            f"action_index={action_index} action={action} reason={reason}"
        )

    # --- helpers --------------------------------------------------------

    def _wait(self, target: FgoState, timeout: float) -> None:
        sm.wait_state(self.ctx, target, timeout=timeout)

    def _sleep_interruptible(self, seconds: float) -> None:
        """Sleep in small increments so stop/pause are responsive."""
        end = time.monotonic() + max(0.0, seconds)
        while time.monotonic() < end:
            self.ctx.control.checkpoint()
            time.sleep(min(0.2, end - time.monotonic()))
