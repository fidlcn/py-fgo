"""Instance-level ADB operations: connection test, screenshot, device scan.

Keeps ADB usage out of the API routers. The worker manager owns long-running
quests; this manager handles the short, synchronous diagnostics.
"""

from __future__ import annotations

from typing import Any

from backend.core.config import AppConfig
from backend.core.logging import get_logger
from worker.adb_client import ADBClient
from worker.mumu_provider import list_devices, restart_adb_server

log = get_logger("services.instance")


class InstanceManager:
    def __init__(self, config: AppConfig) -> None:
        self.config = config

    def _client(self, instance: dict[str, Any]) -> ADBClient:
        return ADBClient(
            self.config.adb.path,
            instance["adb_device_id"],
            default_timeout=self.config.adb.command_timeout_seconds,
        )

    def test_connection(self, instance: dict[str, Any]) -> dict[str, Any]:
        client = self._client(instance)
        try:
            online = client.is_online()
        except Exception as exc:  # noqa: BLE001
            log.warning("connection test failed for %s: %s", instance["adb_device_id"], exc)
            online = False
        return {"online": online, "device_id": instance["adb_device_id"]}

    def capture_screenshot_png(self, instance: dict[str, Any]) -> bytes:
        client = self._client(instance)
        return client.screenshot_png()

    def scan_adb(self) -> list[dict[str, str]]:
        devices = list_devices(self.config.adb.path)
        return [{"device_id": d.device_id, "state": d.state} for d in devices]

    def restart_adb(self) -> list[dict[str, str]]:
        devices = restart_adb_server(self.config.adb.path)
        return [{"device_id": d.device_id, "state": d.state} for d in devices]
