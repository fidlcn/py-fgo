"""FastAPI dependencies backed by app-state singletons.

Singletons (config, db, worker/instance/task managers, event bus) are created
in ``app.create_app`` startup and attached to ``app.state``.
"""

from __future__ import annotations

from typing import Any, Generator

from fastapi import Request
from sqlalchemy.orm import Session

from backend.core.config import AppConfig
from backend.core.events import EventBus
from backend.db.session import Database
from backend.services.instance_manager import InstanceManager
from backend.services.calibration import CalibrationService
from backend.services.quick_start import QuickStartService
from backend.services.scheduler import Scheduler
from backend.services.task_manager import TaskManager
from backend.services.worker_manager import WorkerManager


def get_config(request: Request) -> AppConfig:
    return request.app.state.config


def get_database(request: Request) -> Database:
    return request.app.state.db


def db_session(request: Request) -> Generator[Session, Any, None]:
    """Yield a session; commit on success, rollback on error."""
    db: Database = request.app.state.db
    session = db.session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_worker_manager(request: Request) -> WorkerManager:
    return request.app.state.worker_manager


def get_instance_manager(request: Request) -> InstanceManager:
    return request.app.state.instance_manager


def get_task_manager(request: Request) -> TaskManager:
    return request.app.state.task_manager


def get_quick_start_service(request: Request) -> QuickStartService:
    return request.app.state.quick_start_service


def get_calibration_service(request: Request) -> CalibrationService:
    return request.app.state.calibration_service


def get_scheduler(request: Request) -> Scheduler:
    return request.app.state.scheduler


def get_event_bus(request: Request) -> EventBus:
    return request.app.state.bus
