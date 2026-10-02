"""Production profile handler with controlled DB, not direct-database RLS proof.

Current worker parser tests live in tests/test_verdict_integrity.py; backend
tests must not depend on a worker package absent from the actual API image.
"""
import asyncio
from unittest.mock import AsyncMock, MagicMock
from app.profile.router import update_profile


def test_protected_fields_cannot_be_updated_by_users(student_user):
    conn = MagicMock()
    conn.execute = AsyncMock()
    pool = MagicMock()
    pool.acquire.return_value.__aenter__ = AsyncMock(return_value=conn)
    result = asyncio.run(update_profile(
        {'display_name': 'New Name', 'xp': 99999, 'level': 99, 'role': 'admin',
         'is_admin': True, 'total_solved': 100}, student_user, pool))
    assert result['updated_fields'] == ['display_name']
    sql, *args = conn.execute.call_args.args
    assert 'SET display_name = $2' in sql
    assert args == [student_user.user_id, 'New Name']


def test_protected_only_request_does_not_write(student_user):
    pool = MagicMock()
    result = asyncio.run(update_profile({'xp': 99999}, student_user, pool))
    assert result == {'message': 'No valid fields to update'}
    pool.acquire.assert_not_called()
