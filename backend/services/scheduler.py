"""Lightweight task scheduler (spec lists a scheduler under FastAPI services).

In MVP, quest repetition is driven by ``loop_config`` inside the worker. This
scheduler adds optional timed starts (e.g. "start task T every day at 09:00").
Schedules live in memory; a background checker thread starts only when at
least one schedule is added. Real cron/timezone handling is a future
enhancement.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Callable, Optional

from backend.core.logging import get_logger

log = get_logger("services.scheduler")


@dataclass
class Schedule:
    id: str
    task_id: str
    interval_seconds: float  # repeat every N seconds (simple model)
    last_run_at: float = 0.0
    enabled: bool = True


class Scheduler:
    def __init__(self, runner: Optional[Callable[[str], None]] = None) -> None:
        self._runner = runner
        self._schedules: dict[str, Schedule] = {}
        self._lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()

    def add(self, schedule: Schedule) -> Schedule:
        with self._lock:
            self._schedules[schedule.id] = schedule
        self._ensure_running()
        return schedule

    def remove(self, schedule_id: str) -> None:
        with self._lock:
            self._schedules.pop(schedule_id, None)

    def list(self) -> list[Schedule]:
        with self._lock:
            return list(self._schedules.values())

    def due(self, now: Optional[float] = None) -> list[Schedule]:
        now = now if now is not None else time.monotonic()
        with self._lock:
            return [
                s
                for s in self._schedules.values()
                if s.enabled and (now - s.last_run_at) >= s.interval_seconds
            ]

    def tick(self) -> list[str]:
        """Fire all due schedules. Returns the task ids that were triggered."""
        fired: list[str] = []
        for s in self.due():
            s.last_run_at = time.monotonic()
            if self._runner:
                try:
                    self._runner(s.task_id)
                    fired.append(s.task_id)
                except Exception:  # noqa: BLE001
                    log.exception("scheduled run failed for task %s", s.task_id)
        return fired

    # --- background checker (started lazily) ---------------------------

    def _ensure_running(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, name="scheduler", daemon=True)
        self._thread.start()

    def _loop(self) -> None:
        while not self._stop.is_set():
            with self._lock:
                has = bool(self._schedules)
            if has:
                self.tick()
            time.sleep(15.0)

    def shutdown(self) -> None:
        self._stop.set()
