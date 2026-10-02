"""
Pytest configuration and shared fixtures for VeriQuest backend testing.
"""

import pytest
import os
os.environ['DATABASE_URL'] = 'postgresql://vq_api:unit-only@127.0.0.1:1/postgres'
from unittest.mock import MagicMock, AsyncMock
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.security import AuthenticatedUser


@pytest.fixture
def mock_settings():
    return Settings(
        _env_file=None,
        supabase_url="https://test-project.supabase.co",
        database_url=os.environ['DATABASE_URL'],
        redis_url="redis://localhost:6379/0",
        allowed_origins="http://localhost:5173",
    )


@pytest.fixture
def student_user():
    return AuthenticatedUser(
        user_id="11111111-1111-1111-1111-111111111111",
        email="student@veriquest.dev",
        role="authenticated",
    )


@pytest.fixture
def admin_user():
    return AuthenticatedUser(
        user_id="99999999-9999-9999-9999-999999999999",
        email="admin@veriquest.dev",
        role="authenticated",
    )
