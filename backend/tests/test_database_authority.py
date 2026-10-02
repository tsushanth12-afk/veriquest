"""Production auth/handlers/pool guard, controlled DB only. Not live ACL proof."""
import asyncio
import base64
import time
from unittest.mock import AsyncMock, MagicMock

import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi.testclient import TestClient
from jose import jwt
from pydantic import ValidationError

from app.main import app
from app.core.config import Settings,get_settings
from app.core.database_config import validate_database_url
from app.core import security,rate_limit
from app.db import runtime,session
from app.db.session import get_db
from app.profile.router import update_profile

TEST_DSN='postgresql://vq_api:unit-only@127.0.0.1:1/postgres'


def test_signed_admin_claim_requires_database_grant_and_revocation(monkeypatch):
    settings=Settings(_env_file=None,database_url=TEST_DSN)
    key=ec.generate_private_key(ec.SECP256R1()); n=key.public_key().public_numbers()
    b64=lambda v:base64.urlsafe_b64encode(v.to_bytes(32,'big')).decode().rstrip('=')
    document={'keys':[dict(kid='authority-unit',alg='ES256',kty='EC',crv='P-256',x=b64(n.x),y=b64(n.y))]}
    monkeypatch.setattr(security,'get_jwks',lambda *_a,**_k:document)
    token=jwt.encode(dict(sub='11111111-1111-4111-8111-111111111111',role='admin',
        iss=settings.jwt_issuer,aud=settings.jwt_audience,exp=int(time.time())+300),key,
        algorithm='ES256',headers={'kid':'authority-unit'})
    conn=MagicMock();conn.fetchval=AsyncMock(return_value=None);conn.fetch=AsyncMock(return_value=[])
    pool=MagicMock();pool.acquire.return_value.__aenter__=AsyncMock(return_value=conn)
    app.dependency_overrides[get_db]=lambda:pool
    app.dependency_overrides[get_settings]=lambda:settings
    monkeypatch.setattr(rate_limit,'check_rate_limit',AsyncMock(return_value=True))
    client=TestClient(app)
    try:
        headers={'Authorization':'Bearer '+token}
        assert client.get('/api/v1/admin/challenges',headers=headers).status_code==403
        conn.fetchval.assert_awaited_once()
        conn.fetchval.return_value='admin'
        assert client.get('/api/v1/admin/challenges',headers=headers).status_code==200
        conn.fetchval.return_value=None
        assert client.get('/api/v1/admin/challenges',headers=headers).status_code==403
        conn.fetchval.side_effect=OSError('NEVER_LOG_DRIVER_SECRET')
        response=client.get('/api/v1/admin/challenges',headers=headers)
        assert response.status_code==503 and 'NEVER_LOG' not in response.text
    finally:
        client.close();app.dependency_overrides.clear()


@pytest.mark.parametrize('value',[None,'','postgresql://postgres:unit@localhost/postgres',
 'postgresql://service_role:unit@localhost/postgres','postgresql://vq_api@localhost/postgres',
 'mysql://vq_api:unit@localhost/postgres','postgresql://vq_api:unit@localhost/postgres?user=postgres'])
def test_database_configuration_fails_closed(value):
    with pytest.raises((ValidationError,ValueError)):
        Settings(_env_file=None,database_url=value)


def test_secret_configuration_is_redacted_and_roles_are_distinct():
    settings=Settings(_env_file=None,database_url=TEST_DSN)
    assert 'unit-only' not in repr(settings) and 'unit-only' not in settings.model_dump_json()
    with pytest.raises(ValueError):validate_database_url(TEST_DSN,'vq_worker')
    with pytest.raises(ValidationError) as exc:
        Settings(_env_file=None,database_url='postgresql://postgres:NEVER_LOG@localhost/postgres')
    assert 'NEVER_LOG' not in str(exc.value)


def test_missing_database_configuration_is_not_defaulted(monkeypatch):
    monkeypatch.delenv('DATABASE_URL',raising=False)
    with pytest.raises(ValidationError): Settings(_env_file=None)


def test_http_driver_exception_does_not_escape_to_asgi_logging(caplog):
    from app.core.security import get_current_user,AuthenticatedUser
    conn=MagicMock();conn.fetchrow=AsyncMock(side_effect=OSError('NEVER_LOG_DRIVER_SECRET'))
    pool=MagicMock();pool.acquire.return_value.__aenter__=AsyncMock(return_value=conn)
    app.dependency_overrides[get_db]=lambda:pool
    app.dependency_overrides[get_current_user]=lambda:AuthenticatedUser(user_id='11111111-1111-4111-8111-111111111111',role='authenticated')
    client=TestClient(app)
    try:
        # Default raise_server_exceptions=True: an ASGI rethrow would fail this test.
        response=client.get('/api/v1/profile')
        assert response.status_code==500 and response.json()['error']['code']=='SYSTEM_ERROR'
        assert 'NEVER_LOG' not in response.text and 'NEVER_LOG' not in caplog.text
    finally:
        client.close();app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_real_pool_guard_and_connection_errors_are_sanitized(monkeypatch):
    conn=MagicMock();conn.fetchrow=AsyncMock(return_value={k:True for k in (
      'correct_role','limited','no_memberships','no_owned_relations','no_owned_functions','no_private_platform')})
    pool=MagicMock();pool.acquire.return_value.__aenter__=AsyncMock(return_value=conn);pool.close=AsyncMock()
    create=AsyncMock(return_value=pool);monkeypatch.setattr(runtime.asyncpg,'create_pool',create)
    assert await runtime.create_runtime_pool(TEST_DSN,'vq_api') is pool
    assert create.call_args.kwargs['timeout']==5
    for key in conn.fetchrow.return_value:
        conn.fetchrow.return_value[key]=False
        with pytest.raises(RuntimeError):await runtime.create_runtime_pool(TEST_DSN,'vq_api')
        conn.fetchrow.return_value[key]=True
    create.side_effect=OSError('NEVER_LOG_DRIVER_SECRET')
    with pytest.raises(RuntimeError) as exc:await runtime.create_runtime_pool(TEST_DSN,'vq_api')
    assert 'NEVER_LOG' not in str(exc.value) and exc.value.__suppress_context__


@pytest.mark.asyncio
async def test_session_connection_log_and_cleanup_are_sanitized(monkeypatch,caplog):
    monkeypatch.setattr(session,'get_settings',lambda:Settings(_env_file=None,database_url=TEST_DSN))
    monkeypatch.setattr(session,'create_runtime_pool',AsyncMock(side_effect=OSError('NEVER_LOG_DRIVER_SECRET')))
    with pytest.raises(RuntimeError):await session.init_db()
    assert 'NEVER_LOG' not in caplog.text
    pool=MagicMock();pool.close=AsyncMock(side_effect=OSError('NEVER_LOG_DRIVER_SECRET'))
    with pytest.raises(RuntimeError) as exc:await runtime.close_runtime_pool(pool)
    assert 'NEVER_LOG' not in str(exc.value)


@pytest.mark.parametrize('body',[{'display_name':1},{'bio':'x'*2001},{'avatar_url':[]}])
def test_profile_display_bounds_call_production(body,student_user):
    from app.core.errors import AppError
    pool=MagicMock()
    with pytest.raises(AppError):asyncio.run(update_profile(body,student_user,pool))
    pool.acquire.assert_not_called()


def test_missing_profile_is_not_reported_updated(student_user):
    from app.core.errors import AppError
    conn=MagicMock();conn.execute=AsyncMock(return_value='UPDATE 0')
    pool=MagicMock();pool.acquire.return_value.__aenter__=AsyncMock(return_value=conn)
    with pytest.raises(AppError) as exc:asyncio.run(update_profile({'bio':'safe'},student_user,pool))
    assert exc.value.status_code==404
