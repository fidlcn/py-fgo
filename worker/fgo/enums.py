"""FGO enums: UI states, action types, card colors, class filters (spec 3.3 / 6 / 8)."""

from __future__ import annotations

from enum import Enum


class FgoState(str, Enum):
    """Recognizable FGO UI states (spec section 6)."""

    UNKNOWN = "UNKNOWN"
    HOME = "HOME"
    QUEST_LIST = "QUEST_LIST"
    QUEST_DETAIL = "QUEST_DETAIL"
    SUPPORT_SELECT = "SUPPORT_SELECT"
    PARTY_CONFIRM = "PARTY_CONFIRM"
    BATTLE_LOADING = "BATTLE_LOADING"
    BATTLE_COMMAND = "BATTLE_COMMAND"
    BATTLE_CARD_SELECT = "BATTLE_CARD_SELECT"
    BATTLE_RESULT = "BATTLE_RESULT"
    BOND_RESULT = "BOND_RESULT"
    DROP_RESULT = "DROP_RESULT"
    FRIEND_REQUEST = "FRIEND_REQUEST"
    REPEAT_CONFIRM = "REPEAT_CONFIRM"
    AP_INSUFFICIENT = "AP_INSUFFICIENT"
    NETWORK_ERROR = "NETWORK_ERROR"
    APP_CRASHED = "APP_CRASHED"
    TASK_DONE = "TASK_DONE"

    @classmethod
    def from_value(cls, value: str) -> "FgoState":
        """Safe constructor; unknown strings collapse to UNKNOWN."""
        try:
            return cls(value)
        except ValueError:
            return cls.UNKNOWN


# Action types supported by battle plans (spec 3.4 / 8).
ACTION_SERVANT_SKILL = "servant_skill"
ACTION_MASTER_SKILL = "master_skill"
ACTION_ORDER_CHANGE = "order_change"
ACTION_SELECT_ENEMY = "select_enemy"
ACTION_NOBLE_PHANTASM = "noble_phantasm"
ACTION_FACE_CARDS = "face_cards"
ACTION_WAIT_SECONDS = "wait_seconds"
ACTION_WAIT_STATE = "wait_state"

ALL_ACTION_TYPES = frozenset(
    {
        ACTION_SERVANT_SKILL,
        ACTION_MASTER_SKILL,
        ACTION_ORDER_CHANGE,
        ACTION_SELECT_ENEMY,
        ACTION_NOBLE_PHANTASM,
        ACTION_FACE_CARDS,
        ACTION_WAIT_SECONDS,
        ACTION_WAIT_STATE,
    }
)

# MVP-mandatory action types (spec 3.4).
MVP_ACTION_TYPES = frozenset(
    {
        ACTION_SERVANT_SKILL,
        ACTION_MASTER_SKILL,
        ACTION_NOBLE_PHANTASM,
        ACTION_FACE_CARDS,
        ACTION_WAIT_SECONDS,
    }
)

# Card colors in priority order (spec 8.4).
CARD_ARTS = "Arts"
CARD_BUSTER = "Buster"
CARD_QUICK = "Quick"
ALL_CARD_COLORS = (CARD_ARTS, CARD_BUSTER, CARD_QUICK)

# Support class filters (spec 3.3).
CLASS_SABER = "saber"
CLASS_ARCHER = "archer"
CLASS_LANCER = "lancer"
CLASS_RIDER = "rider"
CLASS_CASTER = "caster"
CLASS_ASSASSIN = "assassin"
CLASS_BERSERKER = "berserker"
CLASS_EXTRA = "extra"
CLASS_ALL = "all"
ALL_CLASS_FILTERS = (
    CLASS_SABER,
    CLASS_ARCHER,
    CLASS_LANCER,
    CLASS_RIDER,
    CLASS_CASTER,
    CLASS_ASSASSIN,
    CLASS_BERSERKER,
    CLASS_EXTRA,
    CLASS_ALL,
)

# AP recovery item tiers (spec 10).
AP_BRONZE = "bronze"
AP_SILVER = "silver"
AP_GOLD = "gold"
ALL_AP_TIERS = (AP_BRONZE, AP_SILVER, AP_GOLD)
