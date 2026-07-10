"""Card selection policy (spec section 8.4).

Priority when choosing face cards:
1. Recognized cards are ordered by ``color_priority`` then ``servant_priority``.
2. If recognition does not yield enough cards, callers should fail the action.
   ``fallback_positions`` remains a stored configuration field for future
   explicit fallback modes, but it is no longer used silently.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from ..vision.detector import CardDetection
from .enums import ALL_CARD_COLORS

DEFAULT_COLOR_PRIORITY = ["Arts", "Buster", "Quick"]


@dataclass
class CardPolicy:
    np_order: list[int] = field(default_factory=list)
    face_card_count: int = 0
    color_priority: list[str] = field(default_factory=lambda: list(DEFAULT_COLOR_PRIORITY))
    servant_priority: list[int] = field(default_factory=list)
    fallback_positions: list[int] = field(default_factory=lambda: [1, 2, 3])

    @classmethod
    def from_dict(cls, data: Optional[dict]) -> "CardPolicy":
        data = data or {}
        return cls(
            np_order=[int(s) for s in (data.get("np_order") or [])],
            face_card_count=int(data.get("face_card_count", 0) or 0),
            color_priority=list(data.get("color_priority") or DEFAULT_COLOR_PRIORITY),
            servant_priority=[int(s) for s in (data.get("servant_priority") or [])],
            fallback_positions=[int(p) for p in (data.get("fallback_positions") or [1, 2, 3])],
        )

    def color_rank(self, color: Optional[str]) -> int:
        if not color:
            return len(self.color_priority) + 1
        try:
            return self.color_priority.index(color)
        except ValueError:
            return len(self.color_priority)

    def servant_rank(self, slot: Optional[int]) -> int:
        slot = slot or 0
        try:
            return self.servant_priority.index(slot)
        except ValueError:
            return len(self.servant_priority) + slot

    def select_face_cards(self, cards: list[CardDetection]) -> list[int]:
        """Return the face-card positions (1..5) to tap this turn."""
        need = max(0, self.face_card_count)
        if need == 0:
            return []
        ranked = sorted(
            cards,
            key=lambda c: (self.color_rank(c.color), self.servant_rank(c.servant_slot)),
        )
        return [c.position for c in ranked[:need]]
