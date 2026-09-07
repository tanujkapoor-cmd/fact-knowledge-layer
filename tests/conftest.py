"""Shared pytest fixtures."""

import pytest
from fastapi.testclient import TestClient

from backend.config import Settings
from backend.main import create_app


@pytest.fixture
def client() -> TestClient:
    settings = Settings(database_url="sqlite:///:memory:", environment="test")
    with TestClient(create_app(settings)) as test_client:
        yield test_client
