"""Screenshot-based coordinate calibration endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from backend.core import response
from backend.services.calibration import CalibrationService

from .deps import get_calibration_service

router = APIRouter(prefix="/api/calibration", tags=["calibration"])


class PointIn(BaseModel):
    key: str
    x: int
    y: int


@router.get("")
def list_points(service: CalibrationService = Depends(get_calibration_service)):
    return response.ok(service.list_points())


@router.get("/export")
def export_points(service: CalibrationService = Depends(get_calibration_service)):
    return response.ok(service.export_points())


@router.post("")
def set_point(data: PointIn, service: CalibrationService = Depends(get_calibration_service)):
    return response.ok(service.set_point(data.key, data.x, data.y))


@router.delete("/{key}")
def clear_point(key: str, service: CalibrationService = Depends(get_calibration_service)):
    return response.ok(service.clear_point(key))
