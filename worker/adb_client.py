"""ADB command wrapper (spec section 5.1).

This is the *only* place subprocess is allowed to talk to ADB. Business logic
calls :class:`ADBClient`, never ``subprocess`` directly. Every command is
forced through ``-s <device_id>`` so multi-instance control is isolated by
construction. Timeouts and non-zero exits raise controlled exceptions.

The constructor accepts an injectable ``runner`` so tests can exercise command
construction without a real ``adb`` binary (spec 14.1).
"""

from __future__ import annotations

import subprocess
import re
from dataclasses import dataclass
from typing import Callable, Optional, Sequence, Union

from backend.core.errors import ADBError, ADBTimeoutError, DeviceOfflineError
from backend.core.logging import get_logger

log = get_logger("worker.adb")

Key = Union[str, int]


@dataclass
class CommandResult:
    returncode: int
    stdout: bytes
    stderr: bytes


# A runner takes (cmd, timeout) and returns a CommandResult.
Runner = Callable[[Sequence[str], float], CommandResult]


def _default_runner(cmd: Sequence[str], timeout: float) -> CommandResult:
    proc = subprocess.run(list(cmd), capture_output=True, timeout=timeout)
    return CommandResult(proc.returncode, proc.stdout or b"", proc.stderr or b"")


_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


class ADBClient:
    def __init__(
        self,
        adb_path: str,
        device_id: str,
        *,
        runner: Optional[Runner] = None,
        default_timeout: float = 10.0,
    ) -> None:
        self.adb_path = adb_path
        self.device_id = device_id
        self._runner: Runner = runner or _default_runner
        self.default_timeout = default_timeout

    # --- low level ------------------------------------------------------

    def _cmd(self, args: Sequence[str]) -> list[str]:
        """Build the full command, always pinning the device id."""
        return [self.adb_path, "-s", self.device_id, *[str(a) for a in args]]

    def run(self, args: Sequence[str], timeout: Optional[float] = None, *, binary: bool = False) -> bytes:
        """Run an adb subcommand and return stdout bytes (or text)."""
        to = self.default_timeout if timeout is None else timeout
        cmd = self._cmd(args)
        try:
            result = self._runner(cmd, to)
        except subprocess.TimeoutExpired as exc:
            raise ADBTimeoutError(f"adb command timed out after {to}s") from exc
        except FileNotFoundError as exc:
            raise ADBError(f"adb executable not found: {cmd[0] if cmd else '?'}") from exc
        if result.returncode != 0:
            err = result.stderr.decode(errors="replace").strip()
            msg = err or f"adb exited {result.returncode}"
            if "device not found" in msg or "device offline" in msg or "not found" in msg:
                raise DeviceOfflineError(f"device {self.device_id} not reachable: {msg}")
            raise ADBError(f"adb {args[0] if args else ''} failed: {msg}")
        return result.stdout if binary else result.stdout.decode(errors="replace")

    # --- high level (spec 5.1) -----------------------------------------

    def shell(self, args: Sequence[str], timeout: float = 10.0) -> str:
        return self.run(["shell", *[str(a) for a in args]], timeout=timeout)

    def screenshot_png(self, timeout: float = 10.0) -> bytes:
        """Capture a screenshot as raw PNG bytes via ``exec-out``.

        ``exec-out`` (vs ``shell``) avoids CRLF translation so the PNG stays
        intact on Windows.
        """
        data = self.run(["exec-out", "screencap", "-p"], timeout=timeout, binary=True)
        if not data or not data.startswith(_PNG_MAGIC):
            raise ADBError("screenshot returned empty or non-PNG data")
        return data

    def tap(self, x: int, y: int) -> None:
        self.shell(["input", "tap", str(x), str(y)])

    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration_ms: int) -> None:
        self.shell(["input", "swipe", str(x1), str(y1), str(x2), str(y2), str(duration_ms)])

    def keyevent(self, key: Key) -> None:
        self.shell(["input", "keyevent", str(key)])

    def is_online(self) -> bool:
        """Return True if the device state is ``device``."""
        try:
            state = self.run(["get-state"], timeout=5.0).strip()
        except (ADBError, DeviceOfflineError):
            return False
        return state == "device"

    def foreground_package(self, package_names: Sequence[str] = ()) -> Optional[str]:
        """Best-effort foreground Android package detection.

        The quick-start flow uses this as a preflight check: if MuMu is online
        but FGO is not the foreground app, fail fast with a clear message.
        Known package names win; otherwise parse common ``dumpsys window``
        focus lines.
        """
        try:
            out = self.shell(["dumpsys", "window"], timeout=5.0)
        except ADBError:
            out = self.shell(["dumpsys", "activity", "activities"], timeout=5.0)
        for package in package_names:
            if package and package in out:
                return package
        patterns = (
            r"mCurrentFocus=.*?\s([A-Za-z0-9_.]+)/",
            r"mFocusedApp=.*?\s([A-Za-z0-9_.]+)/",
            r"Window\{[^}]+\s([A-Za-z0-9_.]+)/",
        )
        for pattern in patterns:
            match = re.search(pattern, out)
            if match:
                return match.group(1)
        return None
