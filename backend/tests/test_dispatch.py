"""Production handlers/dependencies/publisher; DB and broker transport controlled.

No application lifespan, external database, Redis service or real account.
Run in actual backend image: python -B -m pytest tests -p no:cacheprovider
"""
import asyncio
import base64
import json
import threading
import time
from uuid import UUID
from unittest.mock import AsyncMock, MagicMock

import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi.testclient import TestClient
from jose import jwt

from app.main import app
from app.core import security, rate_limit, task_publisher as publisher
from app.core.config import Settings, get_settings
from app.core.security import get_current_user, get_optional_user
from app.db.session import get_db
from app.submissions import router as submissions
from app.admin import router as admin

SID = '22222222-2222-4222-8222-222222222222'
CID = '33333333-3333-4333-8333-333333333333'


@pytest.fixture
def http(monkeypatch, student_user, mock_settings):
    conn = MagicMock()
    conn.execute = AsyncMock(return_value='UPDATE 1')
    conn.fetchrow = AsyncMock()
    conn.fetchval = AsyncMock()
    conn.transaction.return_value.__aenter__ = AsyncMock()
    pool = MagicMock()
    pool.acquire.return_value.__aenter__ = AsyncMock(return_value=conn)
    app.dependency_overrides[get_db] = lambda: pool
    app.dependency_overrides[get_settings] = lambda: mock_settings
    app.dependency_overrides[get_current_user] = lambda: student_user
    app.dependency_overrides[get_optional_user] = lambda: student_user
    monkeypatch.setattr(rate_limit, 'check_rate_limit', AsyncMock(return_value=True))
    # Do not enter TestClient context: that would call production DB lifespan.
    client = TestClient(app)
    yield client, conn, pool
    client.close()
    app.dependency_overrides.clear()


def test_main_openapi_and_fixtures(mock_settings, student_user, admin_user):
    schema = app.openapi()
    assert '/api/v1/submissions' in schema['paths']
    assert '/api/v1/admin/challenges/{challenge_id}/validate' in schema['paths']
    assert schema['paths']['/api/v1/submissions']['post'].get('parameters', []) == []
    assert mock_settings.allowed_origins == 'http://localhost:5173'
    assert student_user.role == admin_user.role == 'authenticated'


def test_limiter_uses_signature_verified_subject_not_headers(monkeypatch):
    settings = Settings(_env_file=None, database_url='postgresql://vq_api:unit-only@127.0.0.1:1/postgres')
    key = ec.generate_private_key(ec.SECP256R1())
    numbers = key.public_key().public_numbers()
    b64 = lambda n: base64.urlsafe_b64encode(n.to_bytes(32, 'big')).decode().rstrip('=')
    document = {'keys': [dict(kid='unit-key', alg='ES256', kty='EC', crv='P-256',
                               x=b64(numbers.x), y=b64(numbers.y), use='sig')]}
    # Only JWKS acquisition mocked; signatures/claims and auth dependencies real.
    monkeypatch.setattr(security, 'get_jwks', lambda *_args, **_kw: document)
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_db] = lambda: None
    seen = []
    async def quota(name, maximum, window, settings):
        seen.append(name)
        return rate_limit._check_memory_rate_limit(name, maximum, window)
    monkeypatch.setattr(rate_limit, 'check_rate_limit', quota)
    rate_limit._memory_store.clear()
    client = TestClient(app)
    def token(subject):
        return jwt.encode(dict(sub=subject, aud='authenticated', iss=settings.jwt_issuer,
                               exp=int(time.time())+120), key, algorithm='ES256', headers={'kid': 'unit-key'})
    try:
        # DB dependency stubbed; invalid body never reaches handler/database writes.
        for i in range(10):
            result = client.post('/api/v1/submissions', json={}, headers={
                'Authorization': 'Bearer '+token(SID), 'X-User-ID': CID,
                'X-Forwarded-For': str(i), 'X-Real-IP': str(i)})
            assert result.status_code == 422
        assert client.post('/api/v1/submissions', json={}, headers={
            'Authorization': 'Bearer '+token(SID), 'X-User-ID': CID}).status_code == 429
        assert client.post('/api/v1/submissions', json={}, headers={
            'Authorization': 'Bearer '+token(CID)}).status_code == 422
        assert seen[:11] == ['submission:user:'+SID]*11
        assert seen[-1] == 'submission:user:'+CID
        for headers in [{}, {'Authorization': 'Basic bad'}, {'Authorization': 'Bearer tampered'}]:
            assert client.post('/api/v1/submissions', json={}, headers=headers).status_code == 401
    finally:
        client.close()
        app.dependency_overrides.clear()
        rate_limit._memory_store.clear()


@pytest.mark.parametrize('phase,uncertain', [('connect', False), ('send', True), ('cleanup', True)])
def test_publisher_classifies_phase_without_retry(monkeypatch, mock_settings, phase, uncertain):
    celery = MagicMock()
    connection = celery.connection_for_write.return_value.__enter__.return_value
    if phase == 'connect':
        connection.ensure_connection.side_effect = OSError('private transport error')
    elif phase == 'send':
        celery.send_task.side_effect = OSError('private transport error')
    else:
        celery.connection_for_write.return_value.__exit__.side_effect = OSError('private cleanup error')
    factory = MagicMock(return_value=celery)
    monkeypatch.setattr(publisher, 'Celery', factory)
    with pytest.raises(publisher.PublicationError) as error:
        publisher._publish(publisher.EXECUTE_TASK, [SID], mock_settings)
    assert error.value.uncertain is uncertain
    assert 'private' not in str(error.value)
    assert UUID(error.value.task_id)
    assert celery.send_task.call_count == (0 if phase == 'connect' else 1)
    connection.ensure_connection.assert_called_once_with(max_retries=0, timeout=2)
    celery.close.assert_called_once()


@pytest.mark.parametrize('task,args', [(publisher.EXECUTE_TASK, [SID]), (publisher.VALIDATE_TASK, [CID, SID])])
def test_publisher_canonical_contract(monkeypatch, mock_settings, task, args):
    celery = MagicMock()
    monkeypatch.setattr(publisher, 'Celery', MagicMock(return_value=celery))
    task_id = publisher._publish(task, args, mock_settings)
    name = celery.send_task.call_args.args[0]
    options = celery.send_task.call_args.kwargs
    assert name == task
    assert options['args'] == args
    assert options['queue'] == 'hdl_execution'
    assert options['serializer'] == 'json' and options['retry'] is False
    assert options['ignore_result'] is True and options['task_id'] == task_id
    assert celery.conf.update.call_args.kwargs['broker_transport_options'] == {
        'socket_connect_timeout': 2, 'socket_timeout': 2, 'retry_on_timeout': False}


def test_publisher_offloads_and_invalid_contract(monkeypatch, mock_settings):
    main_thread = threading.get_ident()
    def send(*_args):
        assert threading.get_ident() != main_thread
        return 'task'
    monkeypatch.setattr(publisher, '_publish', send)
    assert asyncio.run(publisher.publish_task(publisher.EXECUTE_TASK, [SID], mock_settings)) == 'task'


@pytest.mark.parametrize('task,args', [('arbitrary', [SID]), (publisher.EXECUTE_TASK, ['bad']),
                                      (publisher.VALIDATE_TASK, [SID])])
def test_bad_task_contract_is_definite(mock_settings, task, args):
    with pytest.raises(publisher.PublicationError) as error:
        publisher._publish(task, args, mock_settings)
    assert error.value.uncertain is False


@pytest.mark.parametrize('uncertain', [False, True])
def test_submission_failure_persists_truthfully(http, monkeypatch, uncertain):
    client, conn, _ = http
    conn.fetchrow.return_value = {'id': CID}
    send = AsyncMock(side_effect=publisher.PublicationError(uncertain=uncertain, task_id=SID))
    monkeypatch.setattr(submissions, 'publish_task', send)
    result = client.post('/api/v1/submissions', json={'challenge_id': CID, 'submitted_code': 'module a; endmodule'})
    assert result.status_code == 503
    assert result.json()['error']['code'] == ('DISPATCH_UNCERTAIN' if uncertain else 'DISPATCH_FAILED')
    sql, sid, flag, code, message = conn.execute.call_args.args
    assert UUID(sid) and sid in result.json()['error']['message']
    assert "AND status = 'queued'" in sql
    assert "'system_error'" in sql and flag is uncertain
    assert code == result.json()['error']['code']
    send.assert_awaited_once()


def test_success_submission_publishes_actual_created_id(http, monkeypatch):
    client, conn, _ = http
    conn.fetchrow.return_value = {'id': CID}
    send = AsyncMock(return_value=SID)
    monkeypatch.setattr(submissions, 'publish_task', send)
    result = client.post('/api/v1/submissions', json={'challenge_id': CID, 'submitted_code': 'module a; endmodule'})
    assert result.status_code == 201 and result.json()['status'] == 'queued'
    assert send.call_args.args[:2] == (publisher.EXECUTE_TASK, [result.json()['submission_id']])


@pytest.mark.parametrize('status', ['queued', 'running', 'accepted', 'system_error'])
def test_duplicate_never_republishes(http, monkeypatch, status):
    client, conn, _ = http
    conn.fetchrow.return_value = {'id': SID, 'status': status}
    send = AsyncMock()
    monkeypatch.setattr(submissions, 'publish_task', send)
    result = client.post('/api/v1/submissions', json={'challenge_id': CID, 'submitted_code': 'code', 'idempotency_key': 'same'})
    assert result.status_code == 201 and result.json() == {'submission_id': SID, 'status': status}
    send.assert_not_called()
    conn.execute.assert_not_called()


def admin_rows(conn, *, published=False, pending=False):
    conn.fetchrow.side_effect = [dict(id=CID, is_published=published,
                                    validation_status='validating' if pending else 'draft'),
                               dict(official_solution='module a; endmodule', hidden_testbench='bench')]
    conn.fetchval.side_effect = ['admin', CID]


def test_admin_authorization_before_publication(http, monkeypatch):
    client, conn, _ = http
    conn.fetchval.return_value = None
    send = AsyncMock()
    monkeypatch.setattr(admin, 'publish_task', send)
    assert client.post(f'/api/v1/admin/challenges/{CID}/validate').status_code == 403
    send.assert_not_called()
    conn.execute.assert_not_called()


def test_admin_validation_is_pending_not_validated(http, monkeypatch):
    client, conn, _ = http
    admin_rows(conn)
    send = AsyncMock(return_value=SID)
    monkeypatch.setattr(admin, 'publish_task', send)
    result = client.post(f'/api/v1/admin/challenges/{CID}/validate')
    assert result.status_code == 202
    assert result.json()['challenge_id'] == CID and result.json()['status'] == 'validating'
    send.assert_awaited_once()
    assert send.call_args.args[:2] == (publisher.VALIDATE_TASK, [CID, '11111111-1111-1111-1111-111111111111'])


@pytest.mark.parametrize('published,pending', [(True, False), (False, True)])
def test_admin_rejects_published_or_pending(http, monkeypatch, published, pending):
    client, conn, _ = http
    admin_rows(conn, published=published, pending=pending)
    send = AsyncMock()
    monkeypatch.setattr(admin, 'publish_task', send)
    assert client.post(f'/api/v1/admin/challenges/{CID}/validate').status_code == 409
    send.assert_not_called()
    conn.execute.assert_not_called()


@pytest.mark.parametrize('uncertain', [False, True])
def test_admin_publication_failure_states(http, monkeypatch, uncertain):
    client, conn, _ = http
    admin_rows(conn)
    monkeypatch.setattr(admin, 'publish_task', AsyncMock(side_effect=publisher.PublicationError(uncertain=uncertain, task_id=SID)))
    result = client.post(f'/api/v1/admin/challenges/{CID}/validate')
    assert result.status_code == 503
    assert result.json()['error']['code'] == ('DISPATCH_UNCERTAIN' if uncertain else 'DISPATCH_FAILED')
    writes = [call.args[0] for call in conn.execute.call_args_list]
    assert any("SET validation_status = 'validation_failed'" in sql for sql in writes) is (not uncertain)
    assert any('dispatch_error' in sql for sql in writes)


def test_broker_configuration_rejects_unsupported():
    for url in ['', 'http://localhost', 'memory://', 'redis://']:
        with pytest.raises(ValueError):
            Settings(_env_file=None, redis_url=url)
    for value in [0, 6]:
        with pytest.raises(ValueError):
            Settings(_env_file=None, task_publish_timeout_seconds=value)


def test_submission_error_recording_failure_is_not_hidden(http, monkeypatch):
    client, conn, _ = http
    conn.fetchrow.return_value = {'id': CID}
    # Original submission + attempt writes succeed; failure state write fails.
    conn.execute.side_effect = ['INSERT 0 1', 'UPDATE 1', OSError('private DB detail')]
    monkeypatch.setattr(submissions, 'publish_task', AsyncMock(side_effect=publisher.PublicationError(uncertain=False, task_id=SID)))
    result = client.post('/api/v1/submissions', json={'challenge_id': CID, 'submitted_code': 'code'})
    assert result.status_code == 503
    assert result.json()['error']['code'] == 'DISPATCH_STATE_UNKNOWN'
    assert 'private' not in result.text


def test_admin_error_recording_failure_is_not_hidden(http, monkeypatch):
    client, conn, _ = http
    admin_rows(conn)
    conn.execute.side_effect = ['INSERT 0 1', OSError('private DB detail')]
    monkeypatch.setattr(admin, 'publish_task', AsyncMock(side_effect=publisher.PublicationError(uncertain=False, task_id=SID)))
    result = client.post(f'/api/v1/admin/challenges/{CID}/validate')
    assert result.status_code == 503 and result.json()['error']['code'] == 'DISPATCH_STATE_UNKNOWN'
    assert CID in result.json()['error']['message'] and 'private' not in result.text


def test_admin_conditional_claim_rejects_racing_state(http, monkeypatch):
    client, conn, _ = http
    admin_rows(conn)
    conn.fetchval.side_effect = ['admin', None]
    send = AsyncMock()
    monkeypatch.setattr(admin, 'publish_task', send)
    assert client.post(f'/api/v1/admin/challenges/{CID}/validate').status_code == 409
    send.assert_not_called()
