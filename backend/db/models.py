"""SQLAlchemy ORM models for the five core domain entities (spec section 3).

IDs are short strings so they read well in logs and the UI
(e.g. ``inst_4f2a1b9c0d3e``). JSON columns hold the flexible, version-tolerant
config blobs (waves, preferred support, loop_config, ap_recovery).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import JSON, DateTime, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def new_id(prefix: str) -> str:
    """Generate a readable prefixed id, e.g. ``inst_a1b2c3d4e5f6``."""
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


class Base(DeclarativeBase):
    pass


class EmulatorInstance(Base):
    """A MuMu emulator instance reachable over ADB (spec 3.1)."""

    __tablename__ = "instances"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(128))
    emulator_type: Mapped[str] = mapped_column(String(32), default="mumu")
    adb_device_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    resolution_width: Mapped[int] = mapped_column(Integer, default=1280)
    resolution_height: Mapped[int] = mapped_column(Integer, default=720)
    screenshot_interval_ms: Mapped[int] = mapped_column(Integer, default=700)
    status: Mapped[str] = mapped_column(String(32), default="offline")
    current_task_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    last_heartbeat_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "emulator_type": self.emulator_type,
            "adb_device_id": self.adb_device_id,
            "resolution_width": self.resolution_width,
            "resolution_height": self.resolution_height,
            "screenshot_interval_ms": self.screenshot_interval_ms,
            "status": self.status,
            "current_task_id": self.current_task_id,
            "last_heartbeat_at": self.last_heartbeat_at.isoformat()
            if self.last_heartbeat_at
            else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class QuestProfile(Base):
    """A quest / daily-quest configuration (spec 3.2)."""

    __tablename__ = "quest_profiles"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(128))
    category: Mapped[str] = mapped_column(String(32), default="custom")
    entry_mode: Mapped[str] = mapped_column(String(32), default="current_quest")
    server_region: Mapped[str] = mapped_column(String(16), default="cn")
    navigation_config: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "entry_mode": self.entry_mode,
            "server_region": self.server_region,
            "navigation_config": self.navigation_config or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class SupportProfile(Base):
    """Support filtering configuration (spec 3.3)."""

    __tablename__ = "support_profiles"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(128))
    class_filter: Mapped[str] = mapped_column(String(32), default="all")
    preferred: Mapped[list] = mapped_column(JSON, default=list)
    fallback_mode: Mapped[str] = mapped_column(String(32), default="first_recommended")
    max_scroll_pages: Mapped[int] = mapped_column(Integer, default=5)
    max_refresh_count: Mapped[int] = mapped_column(Integer, default=3)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "class_filter": self.class_filter,
            "preferred": self.preferred or [],
            "fallback_mode": self.fallback_mode,
            "max_scroll_pages": self.max_scroll_pages,
            "max_refresh_count": self.max_refresh_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class BattlePlan(Base):
    """A battle script: waves -> turns -> actions + card policy (spec 3.4)."""

    __tablename__ = "battle_plans"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(128))
    expected_party: Mapped[dict] = mapped_column(JSON, default=dict)
    waves: Mapped[list] = mapped_column(JSON, default=list)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "expected_party": self.expected_party or {},
            "waves": self.waves or [],
            "version": self.version,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class RunTask(Base):
    """A single run task binding instance + profiles + plan (spec 3.5)."""

    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    instance_id: Mapped[str] = mapped_column(String(64), index=True)
    quest_profile_id: Mapped[str] = mapped_column(String(64))
    support_profile_id: Mapped[str] = mapped_column(String(64))
    battle_plan_id: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32), default="pending")
    loop_config: Mapped[dict] = mapped_column(JSON, default=dict)
    ap_recovery: Mapped[dict] = mapped_column(JSON, default=dict)
    completed_count: Mapped[int] = mapped_column(Integer, default=0)
    failure_count: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "instance_id": self.instance_id,
            "quest_profile_id": self.quest_profile_id,
            "support_profile_id": self.support_profile_id,
            "battle_plan_id": self.battle_plan_id,
            "status": self.status,
            "loop_config": self.loop_config or {},
            "ap_recovery": self.ap_recovery or {},
            "completed_count": self.completed_count,
            "failure_count": self.failure_count,
            "last_error": self.last_error,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
        }
