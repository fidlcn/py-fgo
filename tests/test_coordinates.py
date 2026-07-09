"""Unit: coordinate scaling + ActionExecutor tap scaling (spec 14.1 / 7)."""

from __future__ import annotations

from worker.adb_client import ADBClient, CommandResult
from worker.fgo import coordinates as C
from worker.fgo.action_executor import ActionExecutor


def _recording_adb():
    calls: list[list[str]] = []

    def runner(cmd, timeout):
        calls.append(list(cmd))
        return CommandResult(0, b"", b"")

    return ADBClient("adb", "127.0.0.1:7555", runner=runner), calls


def test_scale_point_identity():
    assert C.scale_point(640, 360, 1280, 720) == (640, 360)


def test_scale_point_doubles_at_2x_resolution():
    assert C.scale_point(640, 360, 2560, 1440) == (1280, 720)


def test_scale_point_rounds():
    # 1130/1280 * 1639 ~ 1446.x -> round
    x, y = C.scale_point(1130, 640, 1639, 921)
    assert x == round(1130 * 1639 / 1280)
    assert y == round(640 * 921 / 720)


def test_action_executor_taps_scaled_coordinates():
    adb, calls = _recording_adb()
    ex = ActionExecutor(adb, 2560, 1440, action_delay_ms=0)
    ex.tap_attack()
    ex.tap_np_card(3)
    ex.tap_face_card(5)
    # Each command pins the device id.
    for cmd in calls:
        assert cmd[1] == "-s" and cmd[2] == "127.0.0.1:7555"
    # ATTACK_BUTTON (1130,640) -> doubled at 2560x1440.
    attack_xy = calls[0][-2:]
    assert attack_xy == ["2260", "1280"]
    # NP card slot 3 (890,300) -> doubled.
    assert calls[1][-2:] == ["1780", "600"]
    # Face card 5 (1100,560) -> doubled.
    assert calls[2][-2:] == ["2200", "1120"]


def test_action_executor_servant_skill_uses_grid():
    adb, calls = _recording_adb()
    ex = ActionExecutor(adb, 1280, 720, action_delay_ms=0)
    ex.tap_servant_skill(2, 1)  # cluster slot2 -> 165 + 370 = 535
    assert calls[-1][-2:] == ["535", "560"]
    ex.tap_servant_skill(3, 3)  # 305 + 740 = 1045
    assert calls[-1][-2:] == ["1045", "560"]
