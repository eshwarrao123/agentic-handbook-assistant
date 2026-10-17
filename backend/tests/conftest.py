"""Pytest fixtures for backend tests."""

import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    """Synchronous FastAPI TestClient fixture backed by httpx."""
    with TestClient(app) as test_client:
        yield test_client
