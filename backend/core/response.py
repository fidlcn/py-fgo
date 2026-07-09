"""Unified API response envelope (spec section 4).

All endpoints return ``{"ok": bool, "data": ..., "error": ...}``.
"""

from __future__ import annotations

from typing import Any

from .errors import FgoError


def ok(data: Any = None) -> dict[str, Any]:
    return {"ok": True, "data": data, "error": None}


def fail(code: str, message: str, *, data: Any = None) -> dict[str, Any]:
    return {"ok": False, "data": data, "error": {"code": code, "message": message}}


def fail_from(error: FgoError) -> dict[str, Any]:
    return fail(error.code, error.message)
