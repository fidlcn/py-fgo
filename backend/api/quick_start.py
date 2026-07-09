"""One-click quick-start endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from backend.core import response
from backend.services.quick_start import QuickStartService

from .deps import get_quick_start_service

router = APIRouter(prefix="/api/quick-start", tags=["quick-start"])


@router.post("/preflight")
def preflight(quick: QuickStartService = Depends(get_quick_start_service)):
    return response.ok(quick.preflight())


@router.post("")
def start(quick: QuickStartService = Depends(get_quick_start_service)):
    return response.ok(quick.start())
