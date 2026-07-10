"""Unit: RunTask status transitions via TaskManager (spec 14.1 / 4.4)."""

from __future__ import annotations

import pytest

from backend.db import repositories as r
from backend.db.session import get_db, reset_db
from backend.services.instance_manager import InstanceManager
from backend.services.task_manager import TaskManager


class FakeWorkerManager:
    def __init__(self):
        self.started = []
        self.paused = []
        self.resumed = []
        self.stopped = []
        self._running = set()
        self._on_done = None

    def is_running(self, instance_id):
        return instance_id in self._running

    def get_context(self, instance_id):
        return None

    def start(self, instance, task, *, quest_profile, support_profile, battle_plan, on_done=None):
        self.started.append(task["id"])
        self._running.add(instance["id"])
        self._on_done = on_done

    def request_pause(self, instance_id):
        self.paused.append(instance_id)
        self._running.discard(instance_id)

    def resume(self, instance_id):
        self.resumed.append(instance_id)
        self._running.add(instance_id)

    def request_stop(self, instance_id):
        self.stopped.append(instance_id)


class FakeInstanceManager:
    def test_connection(self, instance):
        return {"online": True, "device_id": instance["adb_device_id"]}


@pytest.fixture
def setup():
    reset_db(":memory:")
    db = get_db()
    s = db.session()
    inst = r.create_instance(s, {"name": "M1", "adb_device_id": "127.0.0.1:7555"})
    qp = r.create_quest_profile(s, {"name": "q"})
    sp = r.create_support_profile(s, {"name": "s"})
    bp = r.create_battle_plan(s, {"name": "b", "waves": [{"wave": 1, "turns": [{"turn": 1, "actions": []}]}]})
    s.commit()
    ids = {"instance": inst.id, "quest": qp.id, "support": sp.id, "battle": bp.id}
    s.close()
    workers = FakeWorkerManager()
    tm = TaskManager(workers, FakeInstanceManager())
    return tm, workers, ids


def test_create_task_pending(setup):
    tm, _, ids = setup
    task = tm.create_task(
        {
            "instance_id": ids["instance"],
            "quest_profile_id": ids["quest"],
            "support_profile_id": ids["support"],
            "battle_plan_id": ids["battle"],
            "loop_config": {"mode": "count", "count": 1},
        }
    )
    assert task["status"] == "pending"


def test_start_marks_running_and_calls_worker(setup):
    tm, workers, ids = setup
    task = tm.create_task(
        {
            "instance_id": ids["instance"],
            "quest_profile_id": ids["quest"],
            "support_profile_id": ids["support"],
            "battle_plan_id": ids["battle"],
        }
    )
    started = tm.start(task["id"])
    assert started["status"] == "running"
    assert task["id"] in workers.started


def test_pause_and_resume(setup):
    tm, workers, ids = setup
    task = tm.create_task(
        {
            "instance_id": ids["instance"],
            "quest_profile_id": ids["quest"],
            "support_profile_id": ids["support"],
            "battle_plan_id": ids["battle"],
        }
    )
    tm.start(task["id"])
    paused = tm.pause(task["id"])
    assert paused["status"] == "paused"
    assert ids["instance"] in workers.paused
    resumed = tm.resume(task["id"])
    assert resumed["status"] == "running"
    assert ids["instance"] in workers.resumed


def test_stop_sets_stopping(setup):
    tm, workers, ids = setup
    task = tm.create_task(
        {
            "instance_id": ids["instance"],
            "quest_profile_id": ids["quest"],
            "support_profile_id": ids["support"],
            "battle_plan_id": ids["battle"],
        }
    )
    tm.start(task["id"])
    stopped = tm.stop(task["id"])
    assert stopped["status"] == "stopping"
    assert ids["instance"] in workers.stopped


def test_start_recovers_stale_stopping_task(setup):
    tm, workers, ids = setup
    task = tm.create_task(
        {
            "instance_id": ids["instance"],
            "quest_profile_id": ids["quest"],
            "support_profile_id": ids["support"],
            "battle_plan_id": ids["battle"],
        }
    )
    db = get_db()
    s = db.session()
    r.update_task(s, task["id"], {"status": "stopping"})
    r.update_instance(s, ids["instance"], {"status": "running", "current_task_id": task["id"]})
    s.commit()
    s.close()

    started = tm.start(task["id"])

    assert started["status"] == "running"
    assert task["id"] in workers.started


def test_list_tasks_recovers_stale_stopping_task(setup):
    tm, _, ids = setup
    task = tm.create_task(
        {
            "instance_id": ids["instance"],
            "quest_profile_id": ids["quest"],
            "support_profile_id": ids["support"],
            "battle_plan_id": ids["battle"],
        }
    )
    db = get_db()
    s = db.session()
    r.update_task(s, task["id"], {"status": "stopping"})
    r.update_instance(s, ids["instance"], {"status": "running", "current_task_id": task["id"]})
    s.commit()
    s.close()

    listed = tm.list_tasks()

    assert listed[0]["id"] == task["id"]
    assert listed[0]["status"] == "stopped"


def test_reset_stale_stopping_task(setup):
    tm, _, ids = setup
    task = tm.create_task(
        {
            "instance_id": ids["instance"],
            "quest_profile_id": ids["quest"],
            "support_profile_id": ids["support"],
            "battle_plan_id": ids["battle"],
        }
    )
    db = get_db()
    s = db.session()
    r.update_task(s, task["id"], {"status": "stopping"})
    r.update_instance(s, ids["instance"], {"status": "running", "current_task_id": task["id"]})
    s.commit()
    s.close()

    reset = tm.reset(task["id"])

    assert reset["status"] == "stopped"


def test_on_done_finalizes_status(setup):
    tm, workers, ids = setup
    task = tm.create_task(
        {
            "instance_id": ids["instance"],
            "quest_profile_id": ids["quest"],
            "support_profile_id": ids["support"],
            "battle_plan_id": ids["battle"],
        }
    )
    tm.start(task["id"])

    class Ctx:
        instance_id = ids["instance"]
        last_error = None
        completed_count = 5
        failure_count = 1

    tm._on_task_done(task["id"], "completed", Ctx())
    final = tm.get_task(task["id"])
    assert final["status"] == "completed"
    assert final["completed_count"] == 5
    assert final["failure_count"] == 1


def test_create_task_rejects_missing_references(setup):
    tm, _, ids = setup
    from backend.core.errors import NotFoundError

    with pytest.raises(NotFoundError):
        tm.create_task(
            {
                "instance_id": "nope",
                "quest_profile_id": ids["quest"],
                "support_profile_id": ids["support"],
                "battle_plan_id": ids["battle"],
            }
        )
