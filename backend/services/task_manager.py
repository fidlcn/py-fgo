"""Task orchestration: create, validate, start/pause/resume/stop, finalize.

Enforces the spec rules: an instance must be idle to start a task; pause/stop
set flags the worker honors at safe points; final status is written when the
worker thread exits. Counts are reconciled from the worker context.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from backend.core.errors import ConflictError, NotFoundError, ValidationError
from backend.core.events import TASK_STATUS, bus
from backend.core.logging import get_logger
from backend.db import repositories as r
from backend.db.session import Database, get_db
from .instance_manager import InstanceManager
from .worker_manager import WorkerManager

log = get_logger("services.task")


class TaskManager:
    def __init__(
        self,
        worker_manager: WorkerManager,
        instance_manager: InstanceManager,
        *,
        db_factory=None,
    ) -> None:
        self._db_factory = db_factory or get_db
        self.workers = worker_manager
        self.instances = instance_manager

    # --- create ---------------------------------------------------------

    def create_task(self, data: dict[str, Any]) -> dict[str, Any]:
        self._validate_references(data)
        db = self._db_factory()
        s = db.session()
        try:
            task = r.create_task(s, data)
            s.commit()
            return task.to_dict()
        finally:
            s.close()

    def _validate_references(self, data: dict[str, Any]) -> None:
        required = ("instance_id", "quest_profile_id", "support_profile_id", "battle_plan_id")
        for key in required:
            if not data.get(key):
                raise ValidationError(f"missing required field: {key}")
        db = self._db_factory()
        s = db.session()
        try:
            # Raises NotFoundError if any reference is missing.
            r.get_instance(s, data["instance_id"])
            r.get_quest_profile(s, data["quest_profile_id"])
            r.get_support_profile(s, data["support_profile_id"])
            r.get_battle_plan(s, data["battle_plan_id"])
        finally:
            s.close()

    # --- queries --------------------------------------------------------

    def list_tasks(self, instance_id: Optional[str] = None) -> list[dict[str, Any]]:
        db = self._db_factory()
        s = db.session()
        try:
            tasks = r.list_tasks(s, instance_id)
            changed = False
            for task in tasks:
                if task.status == "stopping" and not self.workers.is_running(task.instance_id):
                    r.update_task(
                        s,
                        task.id,
                        {"status": "stopped", "finished_at": datetime.utcnow()},
                    )
                    r.update_instance(
                        s,
                        task.instance_id,
                        {"status": "idle", "current_task_id": None},
                    )
                    changed = True
            if changed:
                s.commit()
            return [t.to_dict() for t in tasks]
        finally:
            s.close()

    def get_task(self, task_id: str) -> dict[str, Any]:
        db = self._db_factory()
        s = db.session()
        try:
            return r.get_task(s, task_id).to_dict()
        finally:
            s.close()

    def delete(self, task_id: str) -> dict[str, str]:
        db = self._db_factory()
        s = db.session()
        try:
            task = r.get_task(s, task_id)
            if self.workers.is_running(task.instance_id) or task.status in (
                "running",
                "paused",
                "stopping",
            ):
                raise ConflictError("cannot delete a running, paused, or stopping task")
            r.delete_task(s, task_id)
            s.commit()
        finally:
            s.close()
        bus.publish(TASK_STATUS, task_id=task_id, status="deleted")
        return {"deleted": task_id}

    # --- lifecycle ------------------------------------------------------

    def start(self, task_id: str) -> dict[str, Any]:
        db = self._db_factory()
        s = db.session()
        try:
            task = r.get_task(s, task_id)
            inst = r.get_instance(s, task.instance_id)
            if self.workers.is_running(inst.id):
                raise ConflictError("instance already has a running task")
            if task.status == "stopping":
                r.update_task(s, task_id, {"status": "stopped", "finished_at": datetime.utcnow()})
                r.update_instance(s, inst.id, {"status": "idle", "current_task_id": None})
                s.commit()
                task = r.get_task(s, task_id)
            if task.status not in ("pending", "paused", "stopped", "failed", "completed"):
                raise ConflictError(f"cannot start task in status '{task.status}'")

            # Best-effort online check (spec: instance must be online & idle).
            try:
                online = self.instances.test_connection(inst.to_dict())["online"]
            except Exception:  # noqa: BLE001
                online = True  # don't block start on a flaky ADB check
            if not online:
                raise ConflictError(f"instance {inst.id} is offline")

            support = r.get_support_profile(s, task.support_profile_id).to_dict()
            bp = r.get_battle_plan(s, task.battle_plan_id)
            battle_plan = {"name": bp.name, "expected_party": bp.expected_party, "waves": bp.waves}

            now = datetime.utcnow()
            r.update_task(s, task_id, {"status": "running", "started_at": now})
            r.update_instance(s, inst.id, {"status": "running", "current_task_id": task_id})
            s.commit()

            task_dict = task.to_dict()
            inst_dict = inst.to_dict()
        finally:
            s.close()

        self.workers.start(
            inst_dict,
            task_dict,
            support_profile=support,
            battle_plan=battle_plan,
            on_done=self._on_task_done,
        )
        bus.publish(TASK_STATUS, task_id=task_id, status="running")
        return self.get_task(task_id)

    def pause(self, task_id: str) -> dict[str, Any]:
        return self._flag(task_id, "paused", lambda iid: self.workers.request_pause(iid))

    def resume(self, task_id: str) -> dict[str, Any]:
        return self._flag(task_id, "running", lambda iid: self.workers.resume(iid))

    def stop(self, task_id: str) -> dict[str, Any]:
        return self._flag(task_id, "stopping", lambda iid: self.workers.request_stop(iid))

    def reset(self, task_id: str) -> dict[str, Any]:
        db = self._db_factory()
        s = db.session()
        try:
            task = r.get_task(s, task_id)
            if self.workers.is_running(task.instance_id):
                raise ConflictError("cannot reset a task while worker is still running")
            r.update_task(s, task_id, {"status": "stopped", "finished_at": datetime.utcnow()})
            r.update_instance(s, task.instance_id, {"status": "idle", "current_task_id": None})
            s.commit()
        finally:
            s.close()
        bus.publish(TASK_STATUS, task_id=task_id, status="stopped")
        return self.get_task(task_id)

    def _flag(self, task_id: str, new_status: str, worker_op) -> dict[str, Any]:
        db = self._db_factory()
        s = db.session()
        try:
            task = r.get_task(s, task_id)
            inst_id = task.instance_id
            r.update_task(s, task_id, {"status": new_status})
            if new_status == "running":
                r.update_instance(s, inst_id, {"status": "running"})
            elif new_status == "paused":
                r.update_instance(s, inst_id, {"status": "paused"})
            s.commit()
        finally:
            s.close()
        worker_op(inst_id)
        bus.publish(TASK_STATUS, task_id=task_id, status=new_status)
        return self.get_task(task_id)

    # --- finalization ---------------------------------------------------

    def _on_task_done(self, task_id: str, final: str, ctx) -> None:
        db = self._db_factory()
        s = db.session()
        try:
            r.update_task(
                s,
                task_id,
                {
                    "status": final,
                    "finished_at": datetime.utcnow(),
                    "last_error": ctx.last_error,
                    "completed_count": ctx.completed_count,
                    "failure_count": ctx.failure_count,
                },
            )
            r.update_instance(s, ctx.instance_id, {"status": "idle", "current_task_id": None})
            s.commit()
        finally:
            s.close()
        bus.publish(
            TASK_STATUS,
            task_id=task_id,
            status=final,
            completed_count=ctx.completed_count,
            failure_count=ctx.failure_count,
            error=ctx.last_error,
        )
        log.info("task %s finished: %s (completed=%d)", task_id, final, ctx.completed_count)
