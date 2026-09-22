"""
Pytest configuration and shared fixtures for VeriQuest backend testing.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.security import AuthenticatedUser


@pytest.fixture
def mock_settings():
    return Settings(
        supabase_url="https://test-project.supabase.co",
        supabase_anon_key="test-anon-key",
        supabase_service_role_key="test-service-key",
        supabase_jwt_secret="test-jwt-secret",
        database_url="postgresql://test:test@localhost:5432/test",
        redis_url="redis://localhost:6379/0",
        backend_cors_origins=["http://localhost:5173"],
        environment="test",
    )


@pytest.fixture
def student_user():
    return AuthenticatedUser(
        user_id="11111111-1111-1111-1111-111111111111",
        email="student@veriquest.dev",
        role="authenticated",
        is_admin=False,
    )


@pytest.fixture
def admin_user():
    return AuthenticatedUser(
        user_id="99999999-9999-9999-9999-999999999999",
        email="admin@veriquest.dev",
        role="authenticated",
        is_admin=True,
    )
