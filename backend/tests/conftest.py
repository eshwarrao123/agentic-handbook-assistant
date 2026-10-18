"""Pytest fixtures for backend tests."""

import sys

if sys.version_info.major == 3 and sys.version_info.minor != 13:
    sys.path = [p for p in sys.path if "Python313" not in p]

import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    """Synchronous FastAPI TestClient fixture backed by httpx."""
    with TestClient(app) as test_client:
        yield test_client
