"""Settings: view + adjust runtime config (spec 4.x / section 11).

GET returns the active config tree. PATCH updates a small allow-list of
runtime-tunable fields in memory (persistence to YAML is a future enhancement).
"""

from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional

from backend.core import response
from backend.core.config import AppConfig
from .deps import get_config

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("")
def get_settings(config: AppConfig = Depends(get_config)):
    return response.ok(_config_to_dict(config))


class SettingsPatch(BaseModel):
    logging_level: Optional[str] = None
    screenshot_interval_ms: Optional[int] = None
    action_delay_ms: Optional[int] = None
    template_threshold: Optional[float] = None
    state_threshold: Optional[float] = None


@router.patch("")
def patch_settings(patch: SettingsPatch, config: AppConfig = Depends(get_config)):
    if patch.logging_level:
        config.logging.level = patch.logging_level.upper()
    if patch.screenshot_interval_ms is not None:
        config.runtime.screenshot_interval_ms = patch.screenshot_interval_ms
    if patch.action_delay_ms is not None:
        config.runtime.action_delay_ms = patch.action_delay_ms
    if patch.template_threshold is not None:
        config.vision.template_threshold = patch.template_threshold
    if patch.state_threshold is not None:
        config.vision.state_threshold = patch.state_threshold
    return response.ok(_config_to_dict(config))


def _config_to_dict(config: AppConfig) -> dict:
    return {
        "server": asdict(config.server),
        "adb": asdict(config.adb),
        "runtime": {**asdict(config.runtime), "base_resolution": list(config.runtime.base_resolution)},
        "vision": asdict(config.vision),
        "logging": asdict(config.logging),
    }
