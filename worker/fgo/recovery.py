"""AP recovery handler (spec section 10).

When AP is insufficient, optionally consume recovery items by priority up to
``max_items``. Disabling recovery or hitting the limit stops the task with
:class:`APInsufficientError`. Each use is logged:
``used recovery item: bronze, total_used=1``.
"""

from __future__ import annotations

from typing import Any

from backend.core.errors import APInsufficientError
from backend.core.logging import get_logger
from ..runtime import WorkerContext
from .enums import ALL_AP_TIERS

log = get_logger("worker.fgo.recovery")


class RecoveryHandler:
    def __init__(self, ctx: WorkerContext) -> None:
        self.ctx = ctx

    def handle_ap_insufficient(self, ap_recovery: dict[str, Any]) -> bool:
        """Try to recover AP. Returns True to retry the quest, raises to stop."""
        ctx = self.ctx
        if not ap_recovery or not ap_recovery.get("enabled"):
            raise APInsufficientError("AP insufficient and recovery is disabled")

        priority = list(ap_recovery.get("priority") or ALL_AP_TIERS)
        max_items = int(ap_recovery.get("max_items", 3))
        used = int(ap_recovery.get("used_items", 0)) + 1
        if used > max_items:
            raise APInsufficientError(
                f"AP recovery item limit reached (max_items={max_items})"
            )

        tier = priority[0] if priority else ALL_AP_TIERS[0]
        self._use_item(tier)
        ap_recovery["used_items"] = used
        ctx.record_action(f"used recovery item: {tier}, total_used={used}")
        log.info("used recovery item: %s, total_used=%d", tier, used)
        ctx.publish_status(ap_recovery_used=used, ap_recovery_tier=tier)
        return True

    def _use_item(self, tier: str) -> None:
        self.ctx.executor.tap_ap_recovery_item(tier)
        self.ctx.executor.tap_ap_recovery_confirm()
