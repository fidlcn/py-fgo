"""Coordinate system for 1280x720 base resolution (spec section 7).

All coordinates here are in base space. The ActionExecutor scales them to the
emulator's real resolution with :func:`scale_point` before tapping. These
values are starting estimates; real ones are calibrated from screenshots later
(spec: "真实坐标后续要通过截图校准，不要求第一版完全准确").
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class Point:
    x: int
    y: int


BASE_WIDTH = 1280
BASE_HEIGHT = 720


def scale_point(x: int, y: int, actual_w: int, actual_h: int) -> Tuple[int, int]:
    """Scale a base-resolution point to the actual emulator resolution."""
    return round(x * actual_w / BASE_WIDTH), round(y * actual_h / BASE_HEIGHT)


# --- Battle: command phase --------------------------------------------------

ATTACK_BUTTON = Point(1130, 640)

# (servant_slot, skill_index) -> Point. Servant skill clusters along the
# bottom row; slot 1 values are the spec defaults, slots 2/3 extrapolated.
SERVANT_SKILLS: dict[tuple[int, int], Point] = {}
_SkillClusterX = {1: 165, 2: 235, 3: 305}
for _slot, _x_offset in ((1, 0), (2, 370), (3, 740)):
    for _skill, _x in _SkillClusterX.items():
        SERVANT_SKILLS[(_slot, _skill)] = Point(_x + _x_offset, 560)

# Master skill indices 1..3 (plugsuit), bottom-right area.
MASTER_SKILLS: dict[int, Point] = {
    1: Point(853, 660),
    2: Point(925, 660),
    3: Point(997, 660),
}

# Order-change (plugsuit master skill 3) opens a sub-panel; the two columns
# of selectable servants map to reserve positions 1-3 and active 1-3.
ORDER_CHANGE_RESERVE: dict[int, Point] = {
    1: Point(360, 200),
    2: Point(360, 360),
    3: Point(360, 520),
}
ORDER_CHANGE_ACTIVE: dict[int, Point] = {
    1: Point(920, 200),
    2: Point(920, 360),
    3: Point(920, 520),
}

# --- Battle: card-select phase ----------------------------------------------

# NP card per servant slot (top row of the card-select screen).
NP_CARDS: dict[int, Point] = {
    1: Point(390, 300),
    2: Point(640, 300),
    3: Point(890, 300),
}

# Face card positions 1..5 (bottom row).
FACE_CARD_POSITIONS: dict[int, Point] = {
    1: Point(180, 560),
    2: Point(410, 560),
    3: Point(640, 560),
    4: Point(870, 560),
    5: Point(1100, 560),
}

# Enemy target slots 1..3 (top area).
ENEMY_TARGETS: dict[int, Point] = {
    1: Point(300, 160),
    2: Point(640, 160),
    3: Point(980, 160),
}

# Active party member positions (left side) for skill target selection.
PARTY_MEMBER_POSITIONS: dict[int, Point] = {
    1: Point(140, 300),
    2: Point(140, 460),
    3: Point(140, 620),
}

# --- Support selection ------------------------------------------------------

SUPPORT_FIRST_RECOMMENDED = Point(640, 360)
# Vertical swipe to scroll the support list.
SUPPORT_SCROLL_START = Point(640, 500)
SUPPORT_SCROLL_END = Point(640, 200)
SUPPORT_REFRESH = Point(1180, 120)

# Class-filter tab row (approximate x centers; "all" is leftmost).
SUPPORT_CLASS_TABS: dict[str, Point] = {
    "all": Point(120, 60),
    "saber": Point(220, 60),
    "archer": Point(300, 60),
    "lancer": Point(380, 60),
    "rider": Point(460, 60),
    "caster": Point(540, 60),
    "assassin": Point(620, 60),
    "berserker": Point(700, 60),
    "extra": Point(780, 60),
}
SUPPORT_REFRESH_CONFIRM = Point(640, 480)  # "OK" on the refresh dialog

# --- Quest entry ----------------------------------------------------------

QUEST_DETAIL_START = Point(1130, 640)  # Quest entry button on the quest list/entry screen.

# --- AP recovery ----------------------------------------------------------

AP_RECOVERY_ITEM_ROWS: dict[str, Point] = {
    "bronze": Point(320, 320),
    "silver": Point(640, 320),
    "gold": Point(960, 320),
}
AP_RECOVERY_CONFIRM = Point(1100, 640)
AP_RECOVERY_CLOSE = Point(640, 660)

# --- Results / flow ---------------------------------------------------------

RESULT_NEXT = Point(1100, 640)  # "Next" / continue button on result screens
FRIEND_REQUEST_DECLINE = Point(400, 600)
QUEST_START_BUTTON = Point(1130, 640)  # party confirm "Start Quest"
