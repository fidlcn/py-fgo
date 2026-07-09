"""FastAPI application factory.

Wires config, logging, database, services, and all routers. Run with:

    uvicorn backend.app:app --reload --port 8765

or use the provided ``scripts/start-dev`` helpers.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.core import response
from backend.core.config import AppConfig
from backend.core.errors import FgoError, NotFoundError
from backend.core.events import EventBus, bus as default_bus
from backend.core.logging import configure_logging, get_logger
from backend.db.session import Database, init_db
from backend.services.instance_manager import InstanceManager
from backend.services.quick_start import QuickStartService
from backend.services.scheduler import Scheduler
from backend.services.task_manager import TaskManager
from backend.services.worker_manager import WorkerManager

from .api import (
    battle_plans,
    instances,
    logs,
    quick_start,
    quest_profiles,
    settings,
    support_profiles,
    tasks,
    ws,
)

log = get_logger("backend.app")


def create_app(
    *,
    config: AppConfig | None = None,
    db: Database | None = None,
    event_bus: EventBus | None = None,
) -> FastAPI:
    config = config or AppConfig.load()
    config.ensure_dirs()
    configure_logging(level=config.logging.level, log_dir=config.log_dir)
    db = db or init_db(config.db_path)
    event_bus = event_bus or default_bus

    worker_manager = WorkerManager(config, event_bus=event_bus)
    instance_manager = InstanceManager(config)
    task_manager = TaskManager(worker_manager, instance_manager)
    quick_start_service = QuickStartService(config, instance_manager, task_manager)
    scheduler = Scheduler()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        log.info("backend ready on %s:%d", config.server.host, config.server.port)
        yield
        scheduler.shutdown()
        log.info("backend shutting down")

    app = FastAPI(title="FGO Bot", version="0.1.0", lifespan=lifespan)

    # Attach singletons immediately so they exist even if lifespan startup
    # is skipped (e.g. some test setups, or direct ASGI mounting).
    app.state.config = config
    app.state.db = db
    app.state.bus = event_bus
    app.state.worker_manager = worker_manager
    app.state.instance_manager = instance_manager
    app.state.task_manager = task_manager
    app.state.quick_start_service = quick_start_service
    app.state.scheduler = scheduler

    # CORS: allow the Vite dev server and LAN clients (spec section 11).
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # --- error handlers -> unified envelope ----------------------------

    @app.exception_handler(FgoError)
    async def fgo_error_handler(request: Request, exc: FgoError):
        status = 404 if isinstance(exc, NotFoundError) else 400
        if isinstance(exc, NotFoundError) or exc.code == "NOT_FOUND":
            status = 404
        elif exc.code in ("CONFLICT",):
            status = 409
        return JSONResponse(status_code=status, content=response.fail_from(exc))

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content=response.fail("HTTP_ERROR", str(exc.detail)),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        log.exception("unhandled error: %s", exc)
        return JSONResponse(
            status_code=500,
            content=response.fail("INTERNAL_ERROR", f"{type(exc).__name__}: {exc}"),
        )

    # --- routes ---------------------------------------------------------

    @app.get("/health", tags=["health"])
    def health():
        return response.ok({"status": "ok", "version": app.version})

    @app.get("/", tags=["health"])
    def root():
        return response.ok({"name": "FGO Bot", "docs": "/docs", "health": "/health"})

    app.include_router(quest_profiles.router)
    app.include_router(support_profiles.router)
    app.include_router(battle_plans.router)
    app.include_router(instances.router)
    app.include_router(tasks.router)
    app.include_router(quick_start.router)
    app.include_router(logs.router)
    app.include_router(settings.router)
    app.include_router(ws.router)

    return app


# Module-level app for `uvicorn backend.app:app`.
app = create_app()
