"""Task endpoints: create + lifecycle (spec 4.4)."""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from backend.core import response
from backend.services.task_manager import TaskManager
from .deps import get_task_manager

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


class TaskIn(BaseModel):
    instance_id: str
    quest_profile_id: str
    support_profile_id: str
    battle_plan_id: str
    loop_config: Optional[dict[str, Any]] = None
    ap_recovery: Optional[dict[str, Any]] = None


@router.post("")
def create_task(data: TaskIn, tasks: TaskManager = Depends(get_task_manager)):
    return response.ok(tasks.create_task(data.model_dump()))


@router.get("")
def list_tasks(
    instance_id: Optional[str] = Query(default=None),
    tasks: TaskManager = Depends(get_task_manager),
):
    return response.ok(tasks.list_tasks(instance_id))


@router.get("/{task_id}")
def get_task(task_id: str, tasks: TaskManager = Depends(get_task_manager)):
    return response.ok(tasks.get_task(task_id))


@router.delete("/{task_id}")
def delete_task(task_id: str, tasks: TaskManager = Depends(get_task_manager)):
    return response.ok(tasks.delete(task_id))


@router.post("/{task_id}/start")
def start_task(task_id: str, tasks: TaskManager = Depends(get_task_manager)):
    return response.ok(tasks.start(task_id))


@router.post("/{task_id}/pause")
def pause_task(task_id: str, tasks: TaskManager = Depends(get_task_manager)):
    return response.ok(tasks.pause(task_id))


@router.post("/{task_id}/resume")
def resume_task(task_id: str, tasks: TaskManager = Depends(get_task_manager)):
    return response.ok(tasks.resume(task_id))


@router.post("/{task_id}/stop")
def stop_task(task_id: str, tasks: TaskManager = Depends(get_task_manager)):
    return response.ok(tasks.stop(task_id))


@router.post("/{task_id}/reset")
def reset_task(task_id: str, tasks: TaskManager = Depends(get_task_manager)):
    return response.ok(tasks.reset(task_id))
