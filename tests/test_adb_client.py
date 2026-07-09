"""Unit: ADBClient command construction + error mapping (spec 14.1 / 5.1).

Uses an injectable fake runner — no real adb binary required.
"""

from __future__ import annotations

import pytest

from backend.core.errors import ADBError, ADBTimeoutError, DeviceOfflineError
from worker.adb_client import ADBClient, CommandResult

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64


def test_every_command_pins_device_id():
    calls = []

    def runner(cmd, timeout):
        calls.append(list(cmd))
        return CommandResult(0, PNG if "screencap" in cmd else b"device", b"")

    c = ADBClient("adb", "127.0.0.1:7555", runner=runner)
    c.tap(10, 20)
    c.swipe(1, 2, 3, 4, 100)
    c.keyevent(4)
    c.screenshot_png()
    c.is_online()
    for cmd in calls:
        assert cmd[0] == "adb"
        assert cmd[1] == "-s"
        assert cmd[2] == "127.0.0.1:7555"


def test_screenshot_validates_png():
    def runner(cmd, timeout):
        return CommandResult(0, PNG, b"")

    c = ADBClient("adb", "dev", runner=runner)
    assert c.screenshot_png().startswith(b"\x89PNG")


def test_screenshot_rejects_non_png():
    def runner(cmd, timeout):
        return CommandResult(0, b"not a png", b"")

    c = ADBClient("adb", "dev", runner=runner)
    with pytest.raises(ADBError):
        c.screenshot_png()


def test_nonzero_exit_raises_adb_error():
    def runner(cmd, timeout):
        return CommandResult(1, b"", b"some failure")

    c = ADBClient("adb", "dev", runner=runner)
    with pytest.raises(ADBError):
        c.shell(["ls"])


def test_device_offline_message_maps_to_device_error():
    def runner(cmd, timeout):
        return CommandResult(1, b"", b"error: device offline")

    c = ADBClient("adb", "dev", runner=runner)
    with pytest.raises(DeviceOfflineError):
        c.shell(["ls"])


def test_timeout_is_raised():
    import subprocess

    def runner(cmd, timeout):
        raise subprocess.TimeoutExpired(cmd=cmd, timeout=timeout)

    # ADBClient uses the default runner when none provided; inject timeout
    # by wrapping. Here we simulate via the _default_runner path indirectly:
    c = ADBClient("adb", "dev", runner=runner)
    with pytest.raises(ADBTimeoutError):
        c.shell(["ls"])


def test_is_online_true_when_state_device():
    def runner(cmd, timeout):
        return CommandResult(0, b"device", b"")

    assert ADBClient("adb", "dev", runner=runner).is_online() is True


def test_is_online_false_on_error():
    def runner(cmd, timeout):
        return CommandResult(1, b"", b"no devices")

    assert ADBClient("adb", "dev", runner=runner).is_online() is False


def test_foreground_package_prefers_known_package():
    def runner(cmd, timeout):
        assert cmd[:3] == ["adb", "-s", "dev"]
        return CommandResult(
            0,
            b"mCurrentFocus=Window{abc u0 com.bilibili.fatego/com.unity3d.player.UnityPlayerActivity}",
            b"",
        )

    assert ADBClient("adb", "dev", runner=runner).foreground_package(
        ["com.bilibili.fatego"]
    ) == "com.bilibili.fatego"
