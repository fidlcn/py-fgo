"""Support profile CRUD (spec 4.3)."""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.core import response
from backend.db import repositories as r
from .deps import db_session

router = APIRouter(prefix="/api/support-profiles", tags=["support-profiles"])


class SupportProfileIn(BaseModel):
    name: str
    class_filter: str = "all"
    preferred: Optional[list[dict[str, Any]]] = None
    fallback_mode: str = "first_recommended"
    max_scroll_pages: int = 5
    max_refresh_count: int = 3


@router.get("")
def list_support_profiles(db: Session = Depends(db_session)):
    return response.ok([s.to_dict() for s in r.list_support_profiles(db)])


@router.post("")
def create_support_profile(data: SupportProfileIn, db: Session = Depends(db_session)):
    sp = r.create_support_profile(db, data.model_dump())
    return response.ok(sp.to_dict())


@router.get("/{profile_id}")
def get_support_profile(profile_id: str, db: Session = Depends(db_session)):
    return response.ok(r.get_support_profile(db, profile_id).to_dict())


@router.put("/{profile_id}")
def update_support_profile(profile_id: str, data: SupportProfileIn, db: Session = Depends(db_session)):
    sp = r.update_support_profile(db, profile_id, data.model_dump())
    return response.ok(sp.to_dict())


@router.delete("/{profile_id}")
def delete_support_profile(profile_id: str, db: Session = Depends(db_session)):
    r.delete_support_profile(db, profile_id)
    return response.ok({"deleted": profile_id})
