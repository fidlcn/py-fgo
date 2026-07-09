"""Instance management endpoints (spec 4.2)."""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.core import response
from backend.core.errors import ConflictError
from backend.core.events import SCREENSHOT_UPDATED
from backend.db import repositories as r
from .deps import db_session, get_event_bus, get_instance_manager, get_worker_manager
from backend.core.events import EventBus
from backend.services.instance_manager import InstanceManager
from backend.services.worker_manager import WorkerManager

router = APIRouter(prefix="/api/instances", tags=["instances"])


class InstanceIn(BaseModel):
    name: str
    adb_device_id: str
    emulator_type: str = "mumu"
    resolution_width: int = 1280
    resolution_height: int = 720
    screenshot_interval_ms: int = 700


class InstancePatch(BaseModel):
    name: Optional[str] = None
    resolution_width: Optional[int] = None
    resolution_height: Optional[int] = None
    screenshot_interval_ms: Optional[int] = None
    status: Optional[str] = None


@router.get("")
def list_instances(
    db: Session = Depends(db_session),
    workers: WorkerManager = Depends(get_worker_manager),
):
    items = [i.to_dict() for i in r.list_instances(db)]
    # Overlay live worker status so the dashboard reflects real activity.
    for item in items:
        ctx = workers.get_context(item["id"])
        if ctx is not None:
            item["live_state"] = ctx.current_state.value
            item["live_completed"] = ctx.completed_count
            item["live_failure"] = ctx.failure_count
            item["live_action"] = ctx.last_action
    return response.ok(items)


@router.post("")
def create_instance(data: InstanceIn, db: Session = Depends(db_session)):
    inst = r.create_instance(db, data.model_dump())
    return response.ok(inst.to_dict())


@router.post("/scan-adb")
def scan_adb(instances: InstanceManager = Depends(get_instance_manager)):
    return response.ok(instances.scan_adb())


@router.post("/{instance_id}/test")
def test_instance(
    instance_id: str,
    db: Session = Depends(db_session),
    instances: InstanceManager = Depends(get_instance_manager),
):
    inst = r.get_instance(db, instance_id).to_dict()
    return response.ok(instances.test_connection(inst))


@router.get("/{instance_id}/screenshot")
def screenshot(
    instance_id: str,
    db: Session = Depends(db_session),
    instances: InstanceManager = Depends(get_instance_manager),
    bus: EventBus = Depends(get_event_bus),
):
    inst = r.get_instance(db, instance_id).to_dict()
    try:
        png = instances.capture_screenshot_png(inst)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=str(exc))
    bus.publish(SCREENSHOT_UPDATED, instance_id=instance_id)
    return Response(content=png, media_type="image/png")


@router.patch("/{instance_id}")
def update_instance(
    instance_id: str, data: InstancePatch, db: Session = Depends(db_session)
):
    inst = r.update_instance(db, instance_id, data.model_dump(exclude_none=True))
    return response.ok(inst.to_dict())


@router.delete("/{instance_id}")
def delete_instance(
    instance_id: str,
    db: Session = Depends(db_session),
    workers: WorkerManager = Depends(get_worker_manager),
):
    if workers.is_running(instance_id):
        raise ConflictError("cannot delete an instance with a running task")
    r.delete_instance(db, instance_id)
    return response.ok({"deleted": instance_id})
