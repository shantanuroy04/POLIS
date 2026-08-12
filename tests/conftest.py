"""Shared pytest fixtures — Implementation Plan task 1.9."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.config import Settings
from backend.main import create_app


@pytest.fixture
def settings() -> Settings:
    """Test settings. Never reads the developer's real .env."""
    return Settings(
        polis_env="test",
        polis_debug=False,
        jwt_secret="test-secret-at-least-32-characters-long",
        cors_allowed_origins="http://localhost:5173",
        _env_file=None,
    )


@pytest.fixture
def client(settings: Settings) -> TestClient:
    return TestClient(create_app(settings))
