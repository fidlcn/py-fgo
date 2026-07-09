"""Worker lifecycle: runs one QuestRunner per instance in a daemon thread.

Pause/stop are cooperative (Control flags checked at safe points) — never a
hard thread kill (spec prohibition 16). Status updates are fanned out to the
event bus and throttled-persisted to the DB.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Any, Callable, Optional

from backend.core.config import AppConfig
from backend.core.errors import FgoError, TaskStoppedError
from backend.core.events import INSTANCE_STATUS, EventBus, bus
from backend.core.logging import get_logger
from backend.db import repositories as r
from backend.db.session import Database, get_db
from worker.adb_client import Runner
from worker.fgo.quest_runner import QuestRunner
from worker.runtime import WorkerContext, build_worker_context

log = get_logger("services.worker")

StatusPersist = Callable[[str, dict[str, Any]], None]


@dataclass
class _WorkerSlot:
    ctx: WorkerContext
    thread: threading.Thread
    task_id: str


class WorkerManager:
    def __init__(
        self,
        config: AppConfig,
        *,
        db_factory: Optional[Callable[[], Database]] = None,
        event_bus: Optional[EventBus] = None,
        runner: Optional["Runner"] = None,
    ) -> None:
        self.config = config
        self._db_factory = db_factory or get_db
        self._bus = event_bus or bus
        self._runner = runner  # injectable ADB runner (tests); None = real adb
        self._slots: dict[str, _WorkerSlot] = {}
        self._lock = threading.Lock()
        # Throttle persistence: (completed, failure, last_state, last_ts).
        self._last_persisted: dict[str, tuple[int, int, str, float]] = {}

    # --- queries --------------------------------------------------------

    def is_running(self, instance_id: str) -> bool:
        with self._lock:
            slot = self._slots.get(instance_id)
            return slot is not None and slot.thread.is_alive()

    def get_context(self, instance_id: str) -> Optional[WorkerContext]:
        with self._lock:
            slot = self._slots.get(instance_id)
            return slot.ctx if slot else None

    def running_instances(self) -> list[str]:
        with self._lock:
            return [iid for iid, slot in self._slots.items() if slot.thread.is_alive()]

    # --- lifecycle ------------------------------------------------------

    def start(
        self,
        instance: dict[str, Any],
        task: dict[str, Any],
        *,
        support_profile: dict[str, Any],
        battle_plan: dict[str, Any],
        on_done: Optional[Callable[[str, str, WorkerContext], None]] = None,
    ) -> WorkerContext:
        instance_id = instance["id"]
        if self.is_running(instance_id):
            raise RuntimeError(f"instance {instance_id} already has a running task")

        ctx = build_worker_context(
            instance,
            self.config,
            runner=self._runner,
            status_sink=lambda p: self._on_status(instance_id, p),
        )
        ctx.task_id = task["id"]
        runner = QuestRunner(
            ctx,
            support_profile=support_profile,
            battle_plan=battle_plan,
            loop_config=task.get("loop_config", {}),
            ap_recovery=task.get("ap_recovery", {}),
        )

        def target() -> None:
            final = "completed"
            try:
                runner.run()
            except TaskStoppedError:
                final = "stopped"
                log.info("task %s stopped", task["id"])
            except FgoError as exc:
                ctx.last_error = str(exc)
                final = "failed"
                log.warning("task %s failed: %s", task["id"], exc)
            except Exception as exc:  # noqa: BLE001
                ctx.last_error = f"{type(exc).__name__}: {exc}"
                final = "failed"
                log.exception("task %s crashed", task["id"])
            finally:
                self._cleanup(instance_id)
                if on_done:
                    try:
                        on_done(task["id"], final, ctx)
                    except Exception:  # noqa: BLE001
                        log.exception("on_done callback failed")

        thread = threading.Thread(target=target, name=f"worker-{instance_id}", daemon=True)
        with self._lock:
            self._slots[instance_id] = _WorkerSlot(ctx=ctx, thread=thread, task_id=task["id"])
        thread.start()
        log.info("started worker for instance %s (task %s)", instance_id, task["id"])
        return ctx

    def request_pause(self, instance_id: str) -> None:
        ctx = self.get_context(instance_id)
        if ctx:
            ctx.control.request_pause()

    def resume(self, instance_id: str) -> None:
        ctx = self.get_context(instance_id)
        if ctx:
            ctx.control.resume()

    def request_stop(self, instance_id: str) -> None:
        ctx = self.get_context(instance_id)
        if ctx:
            ctx.control.request_stop()

    # --- internal -------------------------------------------------------

    def _on_status(self, instance_id: str, payload: dict[str, Any]) -> None:
        event_payload = dict(payload)
        event_payload["instance_id"] = instance_id
        self._bus.publish(INSTANCE_STATUS, **event_payload)
        self._maybe_persist(instance_id, payload)

    def _maybe_persist(self, instance_id: str, payload: dict[str, Any]) -> None:
        completed = int(payload.get("completed_count", 0))
        failure = int(payload.get("failure_count", 0))
        state = str(payload.get("state", ""))
        now = time.monotonic()
        last = self._last_persisted.get(instance_id)
        # Persist when counts change, when state changes, or every ~5s.
        counts_changed = last is None or last[0] != completed or last[1] != failure
        state_changed = last is None or last[2] != state
        timed = last is None or (now - last[3]) > 5.0
        if not (counts_changed or state_changed or timed):
            return
        self._last_persisted[instance_id] = (completed, failure, state, now)
        try:
            db = self._db_factory()
            s = db.session()
            try:
                task_id = payload.get("task_id")
                if task_id:
                    r.update_task(
                        s,
                        task_id,
                        {
                            "completed_count": completed,
                            "failure_count": failure,
                            "last_error": payload.get("error"),
                        },
                    )
                r.update_instance(s, instance_id, {"status": "running"})
                s.commit()
            finally:
                s.close()
        except Exception:  # noqa: BLE001
            log.debug("status persist failed", exc_info=True)

    def _cleanup(self, instance_id: str) -> None:
        with self._lock:
            self._slots.pop(instance_id, None)
            self._last_persisted.pop(instance_id, None)
