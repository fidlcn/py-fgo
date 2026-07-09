"""Fixed-coordinate action executor (spec step 4 / section 7).

Wraps :class:`ADBClient` with base-resolution coordinate helpers and a
configurable post-action delay. All semantic taps go through here so no raw
coordinates leak into the state machine or battle executor.
"""

from __future__ import annotations

import time
from typing import Optional

from backend.core.errors import ActionExecutionError
from backend.core.logging import get_logger
from ..adb_client import ADBClient
from . import coordinates as C
from .coordinates import Point

log = get_logger("worker.fgo.action")


class ActionExecutor:
    def __init__(
        self,
        adb: ADBClient,
        actual_w: int,
        actual_h: int,
        *,
        action_delay_ms: int = 350,
        coordinate_overrides: Optional[dict[str, tuple[int, int]]] = None,
    ) -> None:
        self.adb = adb
        self.actual_w = actual_w
        self.actual_h = actual_h
        self.action_delay_ms = action_delay_ms
        self.coordinate_overrides = coordinate_overrides or {}

    # --- primitives -----------------------------------------------------

    def tap_point(self, pt: Point) -> None:
        x, y = C.scale_point(pt.x, pt.y, self.actual_w, self.actual_h)
        self._safe(lambda: self.adb.tap(x, y))

    def point(self, key: str, default: Point) -> Point:
        override = self.coordinate_overrides.get(key)
        if override is None:
            return default
        return Point(int(override[0]), int(override[1]))

    def tap_named(self, key: str, default: Point) -> None:
        self.tap_point(self.point(key, default))

    def tap_xy(self, x: int, y: int) -> None:
        sx, sy = C.scale_point(x, y, self.actual_w, self.actual_h)
        self._safe(lambda: self.adb.tap(sx, sy))

    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration_ms: int) -> None:
        sx1, sy1 = C.scale_point(x1, y1, self.actual_w, self.actual_h)
        sx2, sy2 = C.scale_point(x2, y2, self.actual_w, self.actual_h)
        self._safe(lambda: self.adb.swipe(sx1, sy1, sx2, sy2, duration_ms))

    def _safe(self, fn) -> None:
        try:
            fn()
        except Exception as exc:  # noqa: BLE001 - wrap into a controlled error
            raise ActionExecutionError(str(exc)) from exc
        self._delay()

    def _delay(self) -> None:
        if self.action_delay_ms > 0:
            time.sleep(self.action_delay_ms / 1000.0)

    # --- battle command phase ------------------------------------------

    def tap_attack(self) -> None:
        self.tap_named("ATTACK_BUTTON", C.ATTACK_BUTTON)

    def tap_servant_skill(self, slot: int, skill: int) -> None:
        pt = C.SERVANT_SKILLS.get((slot, skill))
        if pt is None:
            raise ActionExecutionError(f"no coordinate for servant skill ({slot},{skill})")
        self.tap_named(f"SERVANT_SKILL_{slot}_{skill}", pt)

    def tap_master_skill(self, skill: int) -> None:
        pt = C.MASTER_SKILLS.get(skill)
        if pt is None:
            raise ActionExecutionError(f"no coordinate for master skill {skill}")
        self.tap_named(f"MASTER_SKILL_{skill}", pt)

    def tap_enemy(self, slot: int) -> None:
        pt = C.ENEMY_TARGETS.get(slot)
        if pt is None:
            raise ActionExecutionError(f"no coordinate for enemy target {slot}")
        self.tap_named(f"ENEMY_TARGET_{slot}", pt)

    # --- battle card-select phase --------------------------------------

    def tap_np_card(self, slot: int) -> None:
        pt = C.NP_CARDS.get(slot)
        if pt is None:
            raise ActionExecutionError(f"no coordinate for NP card slot {slot}")
        self.tap_named(f"NP_CARD_{slot}", pt)

    def tap_face_card(self, position: int) -> None:
        pt = C.FACE_CARD_POSITIONS.get(position)
        if pt is None:
            raise ActionExecutionError(f"no coordinate for face card {position}")
        self.tap_named(f"FACE_CARD_{position}", pt)

    # --- support --------------------------------------------------------

    def tap_support_first_recommended(self) -> None:
        self.tap_named("SUPPORT_FIRST_RECOMMENDED", C.SUPPORT_FIRST_RECOMMENDED)

    def tap_support_class_tab(self, class_filter: str) -> None:
        pt = C.SUPPORT_CLASS_TABS.get(class_filter)
        if pt is not None:
            self.tap_named(f"SUPPORT_CLASS_{class_filter.upper()}", pt)

    def scroll_support_list(self, duration_ms: int = 300) -> None:
        s, e = C.SUPPORT_SCROLL_START, C.SUPPORT_SCROLL_END
        self.swipe(s.x, s.y, e.x, e.y, duration_ms)

    def tap_support_refresh(self) -> None:
        self.tap_named("SUPPORT_REFRESH", C.SUPPORT_REFRESH)

    # --- results / flow -------------------------------------------------

    def tap_result_next(self) -> None:
        self.tap_named("RESULT_NEXT", C.RESULT_NEXT)

    def tap_quest_start(self) -> None:
        self.tap_named("QUEST_START_BUTTON", C.QUEST_START_BUTTON)

    def decline_friend_request(self) -> None:
        self.tap_named("FRIEND_REQUEST_DECLINE", C.FRIEND_REQUEST_DECLINE)
