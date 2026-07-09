"""Shared pytest fixtures."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.app import create_app
from backend.db.session import get_db, reset_db


@pytest.fixture
def app_client():
    """A FastAPI TestClient backed by a fresh in-memory database."""
    reset_db(":memory:")
    app = create_app(db=get_db())
    with TestClient(app) as client:
        yield client
