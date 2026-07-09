"""Repository functions for each domain entity.

Stateless functions taking a :class:`~sqlalchemy.orm.Session`. They never
commit — the caller owns the transaction so endpoints can compose multiple
operations atomically.
"""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.errors import ConflictError, NotFoundError
from .models import (
    BattlePlan,
    EmulatorInstance,
    QuestProfile,
    RunTask,
    SupportProfile,
    new_id,
)


# ---------------------------------------------------------------------------
# EmulatorInstance
# ---------------------------------------------------------------------------


def list_instances(db: Session) -> list[EmulatorInstance]:
    return list(db.scalars(select(EmulatorInstance).order_by(EmulatorInstance.created_at)))


def get_instance(db: Session, instance_id: str) -> EmulatorInstance:
    inst = db.get(EmulatorInstance, instance_id)
    if inst is None:
        raise NotFoundError(f"Instance not found: {instance_id}")
    return inst


def get_instance_by_device(db: Session, adb_device_id: str) -> Optional[EmulatorInstance]:
    return db.scalar(select(EmulatorInstance).where(EmulatorInstance.adb_device_id == adb_device_id))


def create_instance(db: Session, data: dict[str, Any]) -> EmulatorInstance:
    if get_instance_by_device(db, data["adb_device_id"]):
        raise ConflictError(
            f"adb_device_id already bound to another instance: {data['adb_device_id']}"
        )
    inst = EmulatorInstance(
        id=new_id("inst"),
        name=data["name"],
        emulator_type=data.get("emulator_type", "mumu"),
        adb_device_id=data["adb_device_id"],
        resolution_width=data.get("resolution_width", 1280),
        resolution_height=data.get("resolution_height", 720),
        screenshot_interval_ms=data.get("screenshot_interval_ms", 700),
        status=data.get("status", "offline"),
    )
    db.add(inst)
    db.flush()
    return inst


def update_instance(db: Session, instance_id: str, data: dict[str, Any]) -> EmulatorInstance:
    inst = get_instance(db, instance_id)
    for key in ("name", "resolution_width", "resolution_height", "screenshot_interval_ms", "status"):
        if key in data and data[key] is not None:
            setattr(inst, key, data[key])
    db.flush()
    return inst


def delete_instance(db: Session, instance_id: str) -> None:
    inst = get_instance(db, instance_id)
    db.delete(inst)
    db.flush()


# ---------------------------------------------------------------------------
# QuestProfile
# ---------------------------------------------------------------------------


def list_quest_profiles(db: Session) -> list[QuestProfile]:
    return list(db.scalars(select(QuestProfile).order_by(QuestProfile.created_at)))


def get_quest_profile(db: Session, profile_id: str) -> QuestProfile:
    qp = db.get(QuestProfile, profile_id)
    if qp is None:
        raise NotFoundError(f"Quest profile not found: {profile_id}")
    return qp


def create_quest_profile(db: Session, data: dict[str, Any]) -> QuestProfile:
    qp = QuestProfile(
        id=new_id("quest"),
        name=data["name"],
        category=data.get("category", "custom"),
        entry_mode=data.get("entry_mode", "current_quest"),
        server_region=data.get("server_region", "cn"),
        navigation_config=data.get("navigation_config", {}),
    )
    db.add(qp)
    db.flush()
    return qp


def update_quest_profile(db: Session, profile_id: str, data: dict[str, Any]) -> QuestProfile:
    qp = get_quest_profile(db, profile_id)
    for key in ("name", "category", "entry_mode", "server_region", "navigation_config"):
        if key in data:
            setattr(qp, key, data[key])
    db.flush()
    return qp


def delete_quest_profile(db: Session, profile_id: str) -> None:
    qp = get_quest_profile(db, profile_id)
    db.delete(qp)
    db.flush()


# ---------------------------------------------------------------------------
# SupportProfile
# ---------------------------------------------------------------------------


def list_support_profiles(db: Session) -> list[SupportProfile]:
    return list(db.scalars(select(SupportProfile).order_by(SupportProfile.created_at)))


def get_support_profile(db: Session, profile_id: str) -> SupportProfile:
    sp = db.get(SupportProfile, profile_id)
    if sp is None:
        raise NotFoundError(f"Support profile not found: {profile_id}")
    return sp


def create_support_profile(db: Session, data: dict[str, Any]) -> SupportProfile:
    sp = SupportProfile(
        id=new_id("support"),
        name=data["name"],
        class_filter=data.get("class_filter", "all"),
        preferred=data.get("preferred", []),
        fallback_mode=data.get("fallback_mode", "first_recommended"),
        max_scroll_pages=data.get("max_scroll_pages", 5),
        max_refresh_count=data.get("max_refresh_count", 3),
    )
    db.add(sp)
    db.flush()
    return sp


def update_support_profile(db: Session, profile_id: str, data: dict[str, Any]) -> SupportProfile:
    sp = get_support_profile(db, profile_id)
    for key in (
        "name",
        "class_filter",
        "preferred",
        "fallback_mode",
        "max_scroll_pages",
        "max_refresh_count",
    ):
        if key in data:
            setattr(sp, key, data[key])
    db.flush()
    return sp


def delete_support_profile(db: Session, profile_id: str) -> None:
    sp = get_support_profile(db, profile_id)
    db.delete(sp)
    db.flush()


# ---------------------------------------------------------------------------
# BattlePlan
# ---------------------------------------------------------------------------


def list_battle_plans(db: Session) -> list[BattlePlan]:
    return list(db.scalars(select(BattlePlan).order_by(BattlePlan.created_at)))


def get_battle_plan(db: Session, plan_id: str) -> BattlePlan:
    bp = db.get(BattlePlan, plan_id)
    if bp is None:
        raise NotFoundError(f"Battle plan not found: {plan_id}")
    return bp


def create_battle_plan(db: Session, data: dict[str, Any]) -> BattlePlan:
    bp = BattlePlan(
        id=new_id("plan"),
        name=data["name"],
        expected_party=data.get("expected_party", {}),
        waves=data.get("waves", []),
        version=data.get("version", 1),
    )
    db.add(bp)
    db.flush()
    return bp


def update_battle_plan(db: Session, plan_id: str, data: dict[str, Any]) -> BattlePlan:
    bp = get_battle_plan(db, plan_id)
    for key in ("name", "expected_party", "waves", "version"):
        if key in data:
            setattr(bp, key, data[key])
    db.flush()
    return bp


def delete_battle_plan(db: Session, plan_id: str) -> None:
    bp = get_battle_plan(db, plan_id)
    db.delete(bp)
    db.flush()


# ---------------------------------------------------------------------------
# RunTask
# ---------------------------------------------------------------------------


def list_tasks(db: Session, instance_id: Optional[str] = None) -> list[RunTask]:
    stmt = select(RunTask).order_by(RunTask.created_at.desc())
    if instance_id:
        stmt = stmt.where(RunTask.instance_id == instance_id)
    return list(db.scalars(stmt))


def get_task(db: Session, task_id: str) -> RunTask:
    task = db.get(RunTask, task_id)
    if task is None:
        raise NotFoundError(f"Task not found: {task_id}")
    return task


def create_task(db: Session, data: dict[str, Any]) -> RunTask:
    task = RunTask(
        id=new_id("task"),
        instance_id=data["instance_id"],
        quest_profile_id=data["quest_profile_id"],
        support_profile_id=data["support_profile_id"],
        battle_plan_id=data["battle_plan_id"],
        status=data.get("status", "pending"),
        loop_config=data.get("loop_config", {}),
        ap_recovery=data.get("ap_recovery", {}),
    )
    db.add(task)
    db.flush()
    return task


def update_task(db: Session, task_id: str, data: dict[str, Any]) -> RunTask:
    task = get_task(db, task_id)
    for key in (
        "status",
        "loop_config",
        "ap_recovery",
        "completed_count",
        "failure_count",
        "last_error",
        "started_at",
        "finished_at",
    ):
        if key in data:
            setattr(task, key, data[key])
    db.flush()
    return task


def delete_task(db: Session, task_id: str) -> None:
    task = get_task(db, task_id)
    db.delete(task)
    db.flush()
