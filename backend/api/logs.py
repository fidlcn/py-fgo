"""Logs + screenshot diagnostics (spec 4.5 / section 9 run monitor)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse

from backend.core import response
from backend.core.events import EventBus
from .deps import get_config, get_event_bus

router = APIRouter(prefix="/api/logs", tags=["logs"])


@router.get("")
def get_logs(
    lines: int = 200,
    config=Depends(get_config),
    bus: EventBus = Depends(get_event_bus),
):
    """Tail the application log + recent event-bus history."""
    log_path = config.log_dir / "fgobot.log"
    tail: list[str] = []
    if log_path.exists():
        try:
            with log_path.open("r", encoding="utf-8") as fh:
                all_lines = fh.readlines()
            tail = [ln.rstrip("\n") for ln in all_lines[-lines:]]
        except OSError:
            tail = []
    return response.ok({"log": tail, "events": bus.recent(limit=100)})


@router.get("/screenshots")
def list_screenshots(config=Depends(get_config)):
    """List saved screenshots (errors first, then most recent)."""
    directory = config.screenshot_dir
    items = []
    if directory.exists():
        for path in sorted(directory.glob("*.png"), key=lambda p: p.stat().st_mtime, reverse=True):
            stat = path.stat()
            items.append(
                {
                    "name": path.name,
                    "size": stat.st_size,
                    "is_error": path.name.startswith("error_"),
                    "url": f"/api/logs/screenshots/{path.name}",
                }
            )
    return response.ok(items)


@router.get("/screenshots/{name}")
def get_screenshot(name: str, config=Depends(get_config)):
    path = config.screenshot_dir / name
    if not path.exists() or not path.is_file():
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="screenshot not found")
    return FileResponse(str(path), media_type="image/png")
