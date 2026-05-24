"""Shared test fixtures for D2CAgent tests."""

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.database.database import get_db


@pytest.fixture
def client():
    """Test client using real database with seeded data."""
    with TestClient(app) as c:
        yield c