"""Unit: BattlePlan parsing/validation (spec 14.1 / 3.4)."""

from __future__ import annotations

import pytest

from backend.core.errors import BattlePlanError
from worker.fgo.battle_executor import parse_battle_plan


def test_parse_valid_plan():
    plan = {
        "name": "3T",
        "waves": [
            {
                "wave": 1,
                "turns": [
                    {
                        "turn": 1,
                        "actions": [
                            {"type": "servant_skill", "servant_slot": 1, "skill": 1, "target_slot": 3},
                            {"type": "noble_phantasm", "servant_slot": 3},
                        ],
                        "card_policy": {"np_order": [3], "face_card_count": 2},
                    }
                ],
            }
        ],
    }
    parsed = parse_battle_plan(plan)
    assert len(parsed["waves"]) == 1
    turn = parsed["waves"][0]["turns"][0]
    assert turn["turn"] == 1
    assert len(turn["actions"]) == 2
    assert turn["actions"][0]["target_type"] == "ally"
    assert turn["actions"][0]["target_slot"] == 3
    assert turn["actions"][0]["confirm"] == "auto"
    assert turn["card_policy"].np_order == [3]


def test_parse_supports_enemy_target_skill():
    parsed = parse_battle_plan(
        {
            "name": "enemy target",
            "waves": [
                {
                    "turns": [
                        {
                            "actions": [
                                {
                                    "type": "servant_skill",
                                    "servant_slot": 1,
                                    "skill": 2,
                                    "target_type": "enemy",
                                    "target_slot": 2,
                                    "confirm": "always",
                                }
                            ]
                        }
                    ]
                }
            ],
        }
    )
    action = parsed["waves"][0]["turns"][0]["actions"][0]
    assert action["target_type"] == "enemy"
    assert action["target_slot"] == 2
    assert action["confirm"] == "always"


def test_parse_rejects_unknown_action_type():
    with pytest.raises(BattlePlanError):
        parse_battle_plan(
            {"name": "x", "waves": [{"turns": [{"actions": [{"type": "explode"}]}]}]}
        )


def test_parse_rejects_missing_type():
    with pytest.raises(BattlePlanError):
        parse_battle_plan({"name": "x", "waves": [{"turns": [{"actions": [{"servant_slot": 1}]}]}]})


def test_parse_rejects_empty_waves():
    with pytest.raises(BattlePlanError):
        parse_battle_plan({"name": "x", "waves": []})


def test_parse_rejects_non_list_waves():
    with pytest.raises(BattlePlanError):
        parse_battle_plan({"name": "x", "waves": "nope"})


def test_parse_accepts_all_action_types():
    plan = {
        "name": "all",
        "waves": [
            {
                "turns": [
                    {
                        "actions": [
                            {"type": "servant_skill", "servant_slot": 1, "skill": 1},
                            {"type": "master_skill", "skill": 1},
                            {"type": "order_change", "reserve_slot": 1, "active_slot": 1},
                            {"type": "select_enemy", "target_slot": 1},
                            {"type": "noble_phantasm", "servant_slot": 1},
                            {"type": "face_cards"},
                            {"type": "wait_seconds", "seconds": 1},
                            {"type": "wait_state", "state": "BATTLE_COMMAND"},
                        ]
                    }
                ]
            }
        ],
    }
    parsed = parse_battle_plan(plan)
    assert len(parsed["waves"][0]["turns"][0]["actions"]) == 8
