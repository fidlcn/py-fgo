"""Support (friend) selection (spec section 9).

Flow: optional class-filter tab -> search preferred across scroll pages and
refreshes -> fall back to first recommended (or stop). Preferred matching
needs servant/CE templates + OCR, a post-MVP enhancement; until templates
exist, :meth:`_match_on_screen` returns False and we fall through to the
configured fallback automatically.
"""

from __future__ import annotations

import time
from typing import Any

from backend.core.errors import SupportNotFoundError
from backend.core.logging import get_logger
from ..runtime import WorkerContext
from . import coordinates as C
from .enums import FgoState

log = get_logger("worker.fgo.support")


class SupportSelector:
    def __init__(self, ctx: WorkerContext) -> None:
        self.ctx = ctx

    def select(self, profile: dict[str, Any]) -> None:
        ctx = self.ctx
        self._wait(FgoState.SUPPORT_SELECT, timeout=15.0)

        class_filter = (profile.get("class_filter") or "all").lower()
        if class_filter and class_filter != "all":
            ctx.executor.tap_support_class_tab(class_filter)
            ctx.record_action(f"support class filter: {class_filter}")
            self._sleep(0.8)

        preferred = profile.get("preferred") or []
        max_scroll = int(profile.get("max_scroll_pages", 5))
        max_refresh = int(profile.get("max_refresh_count", 3))

        if preferred:
            if self._find_preferred(preferred, max_scroll, max_refresh):
                ctx.record_action("selected preferred support")
                return

        mode = (profile.get("fallback_mode") or "first_recommended").lower()
        if mode == "first_recommended":
            ctx.executor.tap_support_first_recommended()
            ctx.record_action("selected first recommended support (fallback)")
        elif mode == "stop":
            raise SupportNotFoundError("no preferred support matched and fallback is 'stop'")
        else:
            raise SupportNotFoundError(f"unknown fallback_mode: {mode}")

    # --- internal -------------------------------------------------------

    def _find_preferred(
        self, preferred: list[dict[str, Any]], max_scroll: int, max_refresh: int
    ) -> bool:
        attempts = max_refresh + 1
        for attempt in range(attempts):
            for page in range(max_scroll + 1):
                self.ctx.control.checkpoint()
                match = self._match_on_screen(preferred)
                if match is not None:
                    self.ctx.executor.tap_xy(match[0], match[1])
                    return True
                if page < max_scroll:
                    self.ctx.executor.scroll_support_list()
                    self._sleep(0.6)
            if attempt < max_refresh:
                self.ctx.executor.tap_support_refresh()
                self.ctx.executor.tap_point(C.SUPPORT_REFRESH_CONFIRM)
                self._sleep(0.8)
        return False

    def _match_on_screen(self, preferred: list[dict[str, Any]]) -> tuple[int, int] | None:
        """Return (x, y) of a matched preferred support, else None.

        MVP: vision/OCR for friend name + servant/CE is not calibrated, so we
        never match here and the caller falls back to first_recommended.
        """
        return None

    def _wait(self, target: FgoState, timeout: float) -> None:
        self.ctx.state_detector.wait_for_state(
            target,
            self.ctx.screenshots,
            timeout=timeout,
            should_stop=self.ctx.control.stop_requested,
        )

    def _sleep(self, seconds: float) -> None:
        time.sleep(max(0.0, seconds))
