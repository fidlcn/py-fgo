"""Sense-think-act primitives for the worker loop (spec section 5.4).

The FGO flow is procedural (enter -> support -> party -> battle -> result), so
the orchestration lives in :class:`QuestRunner`. This module holds the
per-tick sense helper (capture + detect + publish) and a state-wait wrapper,
both honoring pause/stop at safe points.
"""

from __future__ import annotations

from typing import Optional

from ..runtime import WorkerContext
from ..screenshot import Frame
from .enums import FgoState


def sense(ctx: WorkerContext) -> tuple[FgoState, Frame]:
    """One loop tick: capture, detect state, publish status. Returns both."""
    ctx.control.checkpoint()
    frame = ctx.screenshots.capture()
    state, conf, matched = ctx.state_detector.detect(frame)
    ctx.current_state = state
    ctx.publish_status(confidence=round(conf, 3), matched_template=matched)
    return state, frame


def wait_state(
    ctx: WorkerContext,
    target: FgoState,
    timeout: Optional[float] = None,
    interval_ms: int = 700,
) -> FgoState:
    """Block until ``target`` is detected (or timeout). Honors stop."""
    return ctx.state_detector.wait_for_state(
        target,
        ctx.screenshots,
        timeout=timeout,
        interval_ms=interval_ms,
        should_stop=ctx.control.stop_requested,
    )
