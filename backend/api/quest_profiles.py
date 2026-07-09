"""Quest profile CRUD (spec 4.3)."""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.core import response
from backend.db import repositories as r
from .deps import db_session

router = APIRouter(prefix="/api/quest-profiles", tags=["quest-profiles"])


class QuestProfileIn(BaseModel):
    name: str
    category: str = "custom"
    entry_mode: str = "current_quest"
    server_region: str = "cn"
    navigation_config: Optional[dict[str, Any]] = None


@router.get("")
def list_quest_profiles(db: Session = Depends(db_session)):
    items = [q.to_dict() for q in r.list_quest_profiles(db)]
    return response.ok(items)


@router.post("")
def create_quest_profile(data: QuestProfileIn, db: Session = Depends(db_session)):
    qp = r.create_quest_profile(db, data.model_dump())
    return response.ok(qp.to_dict())


@router.get("/{profile_id}")
def get_quest_profile(profile_id: str, db: Session = Depends(db_session)):
    return response.ok(r.get_quest_profile(db, profile_id).to_dict())


@router.put("/{profile_id}")
def update_quest_profile(profile_id: str, data: QuestProfileIn, db: Session = Depends(db_session)):
    qp = r.update_quest_profile(db, profile_id, data.model_dump())
    return response.ok(qp.to_dict())


@router.delete("/{profile_id}")
def delete_quest_profile(profile_id: str, db: Session = Depends(db_session)):
    r.delete_quest_profile(db, profile_id)
    return response.ok({"deleted": profile_id})
