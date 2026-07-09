"""Database engine + session management.

A single :class:`Database` owns the SQLAlchemy engine and a session factory.
``init_db`` builds the schema; tests can pass an in-memory path.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from ..core.config import DEFAULT_DB_PATH
from .models import Base


def make_engine(db_path: Optional[str | Path] = None) -> Engine:
    """Create a SQLite engine. ``None`` or ``:memory:`` yields an in-memory DB.

    For in-memory mode we use :class:`StaticPool` so a single connection (and
    thus a single in-memory database) is shared across threads — otherwise each
    worker thread would see its own empty database.
    """
    if db_path in (None, ":memory:"):
        engine = create_engine(
            "sqlite://",
            future=True,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    else:
        path = Path(db_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        engine = create_engine(
            f"sqlite:///{path}", future=True, connect_args={"check_same_thread": False}
        )
    return engine


# Enable foreign-key enforcement on SQLite (harmless if no FKs are declared).
@event.listens_for(Engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record) -> None:  # noqa: ANN001
    try:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()
    except Exception:  # noqa: BLE001
        pass


class Database:
    """Owns the engine + session factory for the app."""

    def __init__(self, db_path: Optional[str | Path] = None) -> None:
        self.engine = make_engine(db_path)
        self.SessionLocal = sessionmaker(bind=self.engine, autoflush=False, future=True)

    def create_all(self) -> None:
        Base.metadata.create_all(self.engine)

    def drop_all(self) -> None:
        Base.metadata.drop_all(self.engine)

    def session(self) -> Session:
        return self.SessionLocal()


# Lazily-initialized app-wide database (set by app startup / tests).
_db: Optional[Database] = None


def init_db(db_path: Optional[str | Path] = None) -> Database:
    """Create the schema and store a global Database singleton."""
    global _db
    _db = Database(db_path or DEFAULT_DB_PATH)
    _db.create_all()
    return _db


def get_db() -> Database:
    if _db is None:
        init_db()
    return _db


def reset_db(db_path: Optional[str | Path] = None) -> Database:
    """Replace the singleton (used by tests to get a fresh in-memory DB)."""
    return init_db(db_path or ":memory:")
