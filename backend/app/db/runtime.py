"""Shared API/worker pool guard. Never propagate driver credential diagnostics."""
import asyncpg
from ..core.database_config import validate_database_url


async def verify_runtime_role(conn, expected_role: str):
    row = await conn.fetchrow("""
        SELECT current_user = $1 AS correct_role,
          NOT (r.rolsuper OR r.rolbypassrls OR r.rolcreaterole OR
               r.rolcreatedb OR r.rolreplication OR r.rolinherit) AS limited,
          NOT EXISTS (SELECT 1 FROM pg_catalog.pg_auth_members WHERE member=r.oid) AS no_memberships,
          NOT EXISTS (SELECT 1 FROM pg_catalog.pg_class WHERE relowner=r.oid) AS no_owned_relations,
          NOT EXISTS (SELECT 1 FROM pg_catalog.pg_proc WHERE proowner=r.oid) AS no_owned_functions,
          NOT pg_catalog.has_schema_privilege(r.oid,'auth','USAGE')
            AND NOT pg_catalog.has_schema_privilege(r.oid,'vault','USAGE') AS no_private_platform
        FROM pg_catalog.pg_roles r WHERE r.rolname=current_user
    """, expected_role)
    if not row or not all(row[key] is True for key in (
            'correct_role', 'limited', 'no_memberships', 'no_owned_relations',
            'no_owned_functions', 'no_private_platform')):
        raise RuntimeError('Database runtime role violates the permission gate')


async def close_runtime_pool(pool):
    try:
        await pool.close()
    except Exception:
        raise RuntimeError('Database pool cleanup failed') from None


async def create_runtime_pool(dsn: str, role: str, min_size=1, max_size=2):
    pool = None
    try:
        validate_database_url(dsn, role)
        pool = await asyncpg.create_pool(dsn=dsn, min_size=min_size, max_size=max_size,
                                        timeout=5, command_timeout=30)
        async with pool.acquire() as conn:
            await verify_runtime_role(conn, role)
        return pool
    except Exception:
        if pool is not None:
            try:
                await pool.close()
            except Exception:
                pass
        raise RuntimeError('Database initialization failed; check private configuration and permission gate') from None
