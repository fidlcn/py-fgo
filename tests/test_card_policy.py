"""Unit: CardPolicy selection logic (spec 14.1 / 8.4)."""

from __future__ import annotations

from worker.fgo.card_policy import CardPolicy
from worker.vision.detector import CardDetection


def test_from_dict_defaults():
    p = CardPolicy.from_dict({})
    assert p.face_card_count == 0
    assert p.color_priority == ["Arts", "Buster", "Quick"]
    assert p.fallback_positions == [1, 2, 3]


def test_select_face_cards_uses_fallback_when_no_detections():
    p = CardPolicy(face_card_count=3, fallback_positions=[1, 2, 3, 4, 5])
    assert p.select_face_cards([]) == [1, 2, 3]


def test_select_face_cards_respects_count():
    p = CardPolicy(face_card_count=2, fallback_positions=[1, 2, 3])
    assert p.select_face_cards([]) == [1, 2]


def test_select_face_cards_orders_by_color_then_servant():
    p = CardPolicy(
        face_card_count=2,
        color_priority=["Buster", "Arts", "Quick"],
        servant_priority=[2, 1, 3],
        fallback_positions=[1, 2, 3],
    )
    cards = [
        CardDetection(position=1, color="Arts", servant_slot=1),
        CardDetection(position=2, color="Buster", servant_slot=3),
        CardDetection(position=3, color="Buster", servant_slot=2),
        CardDetection(position=4, color="Quick", servant_slot=1),
    ]
    # Buster first; among Buster, servant_priority [2,1,3] -> slot 2 then 3.
    assert p.select_face_cards(cards) == [3, 2]


def test_select_face_cards_pads_with_fallback():
    p = CardPolicy(face_card_count=3, fallback_positions=[1, 2, 3])
    cards = [CardDetection(position=5, color="Arts", servant_slot=1)]
    result = p.select_face_cards(cards)
    assert result[0] == 5
    assert len(result) == 3
