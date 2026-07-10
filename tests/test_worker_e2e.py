"""End-to-end worker test: one battle turn driven by synthetic screenshots.

Builds template images, feeds scripted PNG frames through the real
ScreenshotProvider/VisionDetector pipeline, and asserts the executor emits the
correct tap sequence (servant skill -> attack -> NP card -> face cards).
No real ADB or emulator is involved.
"""

from __future__ import annotations

import cv2
import numpy as np

from backend.core.config import AppConfig
from worker.adb_client import CommandResult
from worker.fgo.battle_executor import BattleExecutor
from worker.runtime import build_worker_context
from worker.vision.detector import CardDetection


def _marker_frame(text):
    """A frame with a distinct deterministic noise marker keyed by text."""
    seed = sum(ord(c) for c in text)
    rng = np.random.RandomState(seed)
    block = rng.randint(0, 256, (100, 280), dtype=np.uint8)
    img = np.zeros((720, 1280, 3), dtype=np.uint8)
    img[100:200, 90:370, :] = block[:, :, None]
    return img


def _png(img):
    ok, buf = cv2.imencode(".png", img)
    assert ok
    return buf.tobytes()


class ScriptedRunner:
    """Returns queued PNGs for screencap, empty-success for everything else."""

    def __init__(self, frames_png):
        self.frames_png = list(frames_png)
        self.commands = []

    def __call__(self, cmd, timeout):
        self.commands.append(list(cmd))
        if "screencap" in cmd and self.frames_png:
            return CommandResult(0, self.frames_png.pop(0), b"")
        if "get-state" in cmd:
            return CommandResult(0, b"device", b"")
        return CommandResult(0, b"", b"")


def test_battle_turn_tap_sequence(tmp_path):
    # 1. Build templates matching the default state registry ids.
    cmd_frame = _marker_frame("ATTACK")
    card_frame = _marker_frame("CARDS")
    battle_dir = tmp_path / "battle"
    battle_dir.mkdir()
    cv2.imwrite(str(battle_dir / "attack_button.png"), cmd_frame[100:200, 90:370])
    cv2.imwrite(str(battle_dir / "card_select_title.png"), card_frame[100:200, 90:370])

    # 2. Configure + build context with a scripted ADB runner.
    cfg = AppConfig.default()
    cfg.template_dir = tmp_path
    cfg.runtime.action_delay_ms = 0
    cfg.runtime.screenshot_interval_ms = 50
    inst = {"id": "inst_t", "adb_device_id": "127.0.0.1:7555", "resolution_width": 1280, "resolution_height": 720}
    runner = ScriptedRunner(
        [
            _png(cmd_frame),
            _png(cmd_frame),
            _png(cmd_frame),
            _png(card_frame),
            _png(card_frame),
            _png(card_frame),
        ]
    )
    ctx = build_worker_context(inst, cfg, runner=runner)
    ctx.vision.is_skill_ready = lambda frame, servant_slot, skill: True  # type: ignore[method-assign]
    ctx.vision.is_np_ready = lambda frame, servant_slot: True  # type: ignore[method-assign]
    ctx.vision.find_all_cards = lambda frame: [  # type: ignore[method-assign]
        CardDetection(position=1, color="Arts", servant_slot=1),
        CardDetection(position=2, color="Buster", servant_slot=2),
        CardDetection(position=3, color="Quick", servant_slot=3),
    ]

    # 3. Run a single turn: servant skill(1,1) + NP(3); 2 recognized face cards.
    plan = {
        "name": "t",
        "waves": [
            {
                "wave": 1,
                "turns": [
                    {
                        "turn": 1,
                        "actions": [
                            {"type": "servant_skill", "servant_slot": 1, "skill": 1},
                            {"type": "noble_phantasm", "servant_slot": 3},
                        ],
                        "card_policy": {
                            "np_order": [],
                            "face_card_count": 2,
                            "fallback_positions": [1, 2, 3, 4, 5],
                        },
                    }
                ],
            }
        ],
    }
    BattleExecutor(ctx).run_plan(plan)

    # 4. Collect input-tap commands in order.
    taps = []
    for cmd in runner.commands:
        if "input" in cmd and "tap" in cmd:
            idx = cmd.index("tap")
            taps.append((cmd[idx + 1], cmd[idx + 2]))

    expected = [
        ("165", "560"),   # servant skill (1,1)
        ("1130", "640"),  # attack button
        ("890", "300"),   # NP card slot 3
        ("180", "560"),   # face card 1
        ("410", "560"),   # face card 2
    ]
    assert taps == expected, f"tap sequence mismatch: {taps}"
