"""Battle plan CRUD (spec 4.3). Waves are validated on write."""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.core import response
from backend.db import repositories as r
from .deps import db_session
from worker.fgo.battle_executor import parse_battle_plan

router = APIRouter(prefix="/api/battle-plans", tags=["battle-plans"])


class BattlePlanIn(BaseModel):
    name: str
    expected_party: Optional[dict[str, Any]] = None
    waves: Optional[list[dict[str, Any]]] = None
    version: int = 1


@router.get("")
def list_battle_plans(db: Session = Depends(db_session)):
    return response.ok([b.to_dict() for b in r.list_battle_plans(db)])


@router.post("")
def create_battle_plan(data: BattlePlanIn, db: Session = Depends(db_session)):
    payload = data.model_dump()
    parse_battle_plan(payload)  # validate structure before storing
    bp = r.create_battle_plan(db, payload)
    return response.ok(bp.to_dict())


@router.get("/{plan_id}")
def get_battle_plan(plan_id: str, db: Session = Depends(db_session)):
    return response.ok(r.get_battle_plan(db, plan_id).to_dict())


@router.put("/{plan_id}")
def update_battle_plan(plan_id: str, data: BattlePlanIn, db: Session = Depends(db_session)):
    payload = data.model_dump()
    parse_battle_plan(payload)
    bp = r.update_battle_plan(db, plan_id, payload)
    return response.ok(bp.to_dict())


@router.delete("/{plan_id}")
def delete_battle_plan(plan_id: str, db: Session = Depends(db_session)):
    r.delete_battle_plan(db, plan_id)
    return response.ok({"deleted": plan_id})
