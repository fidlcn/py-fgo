"""Sense-think-act primitives for the worker loop (spec section 5.4).

The FGO flow is procedural (enter -> support -> party -> battle -> result), so
the orchestration lives in :class:`QuestRunner`. This module holds the
per-tick sense helper (capture + detect + publish) and a state-wait wrapper,
both honoring pause/stop at safe points.
"""

from __future__ import annotations

import time
from typing import Optional

from backend.core.errors import StateDetectionError
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
    """Block until ``target`` is detected (or timeout). Honors stop.

    Unlike :meth:`StateDetector.wait_for_state`, this wrapper updates the
    worker context on every polling tick, so the UI can show the real current
    state, confidence and matched template while a task is waiting.
    """
    state_def = ctx.state_detector.registry.get(target)
    deadline_timeout = (
        timeout
        if timeout is not None
        else state_def.timeout_seconds
        if state_def is not None
        else 15.0
    )
    deadline = time.monotonic() + deadline_timeout
    interval = max(0.1, interval_ms / 1000.0)
    last = FgoState.UNKNOWN

    while time.monotonic() < deadline:
        if ctx.control.stop_requested:
            raise StateDetectionError(f"interrupted while waiting for {target.value}")
        last, _ = sense(ctx)
        if last == target:
            return last
        time.sleep(interval)

    missing = ctx.state_detector._missing_templates(target)
    detail = f" missing_templates={missing}" if missing else ""
    msg = (
        f"timed out after {deadline_timeout:.1f}s waiting for {target.value} "
        f"(last={last.value}){detail}"
    )
    ctx.set_phase_error(msg)
    raise StateDetectionError(msg)
