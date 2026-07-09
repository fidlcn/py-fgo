"""MuMu emulator discovery helpers.

The backend's ``scan-adb`` endpoint only runs ``adb devices`` (spec 4.2). This
module adds MuMu-specific knowledge: default ADB ports and hostnames, useful
for diagnostics and the "add instance" UI suggestion. Nothing here is required
for the core loop to work.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from typing import Optional

# MuMu player default ADB ports (varies by MuMu major version).
# MuMu 12 uses 16384 + index; MuMu Pro / older use 7555 + index*10.
MUMU_DEFAULT_PORTS = [7555, 7556, 7565, 7575, 16384, 16416, 16448]
MUMU_DEFAULT_HOST = "127.0.0.1"


@dataclass
class AdbDevice:
    device_id: str
    state: str  # device | offline | unauthorized


def list_devices(adb_path: str = "adb", timeout: float = 5.0) -> list[AdbDevice]:
    """Run ``adb devices`` and parse the result. Does not create instances."""
    try:
        proc = subprocess.run(
            [adb_path, "devices"], capture_output=True, timeout=timeout
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return []
    out = proc.stdout.decode(errors="replace")
    devices: list[AdbDevice] = []
    for line in out.splitlines()[1:]:
        line = line.strip()
        if not line or line.startswith("*"):
            continue
        parts = line.split()
        if len(parts) >= 2:
            devices.append(AdbDevice(device_id=parts[0], state=parts[1]))
    return devices


def restart_adb_server(adb_path: str = "adb", timeout: float = 10.0) -> list[AdbDevice]:
    """Run ``adb kill-server``, ``adb start-server``, then return ``adb devices``.

    Used by the UI troubleshooting button when MuMu is running but ADB state is
    stale. Failures are deliberately swallowed into an empty device list so the
    API can return a predictable shape.
    """
    for args in (["kill-server"], ["start-server"]):
        try:
            subprocess.run([adb_path, *args], capture_output=True, timeout=timeout)
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return []
    return list_devices(adb_path, timeout=timeout)


def candidate_mumu_endpoints(host: str = MUMU_DEFAULT_HOST) -> list[str]:
    """Return likely ``host:port`` device ids for MuMu on the given host."""
    return [f"{host}:{port}" for port in MUMU_DEFAULT_PORTS]


def find_device(adb_path: str, device_id: str) -> Optional[AdbDevice]:
    return next((d for d in list_devices(adb_path) if d.device_id == device_id), None)
