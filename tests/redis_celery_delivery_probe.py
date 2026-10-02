"""Private stdin-only fixture/recovery probe, run in the real API image.

NOT the application service: only this short-lived fixture operator receives
setup authority. API/worker services each receive only their own runtime DSN.
"""
import asyncio
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, '/gate')
sys.path.insert(0, '/app')  # Use the actual packaged API, not a host source mount.
from tools import database_live_resources as resources
from tools import database_gate as gate


async def run(capsule):
    import asyncpg
    import httpx
    from app.db.runtime import create_runtime_pool, close_runtime_pool
    mode = capsule['mode']
    if mode == 'runtime':
        pool = await create_runtime_pool(capsule['dsn'], capsule['role'])
        await close_runtime_pool(pool)
        return {'runtime_pool_verified': capsule['role']}
    plan = capsule['plan']
    conn = await asyncpg.connect(capsule['operator_dsn'], timeout=5, command_timeout=15)
    try:
        await resources.bounded(conn)
        if await conn.fetchval('SELECT current_user') != 'supabase_admin':
            raise gate.GateError('Fixture operator identity mismatch')
        users, challenges = await resources.resolve(conn, plan)
        if mode == 'grant':
            if len(users) != 2 or challenges:
                raise gate.GateError('Unexpected pre-fixture resources')
            identifier = await conn.fetchval('SELECT id FROM auth.users WHERE email=$1', plan['emails'][1])
            profiles = await conn.fetch('SELECT xp,total_solved,level FROM public.profiles WHERE id=ANY($1::uuid[])', users)
            if len(profiles) != 2 or any(dict(row) != dict(xp=0,total_solved=0,level=1) for row in profiles):
                raise gate.GateError('Signup did not provision zero-progress profiles')
            await conn.execute("INSERT INTO public.user_roles(user_id,role) VALUES($1,'admin')", identifier)
            return {'zero_progress_profiles': 2, 'admin_fixture_granted': True}
        if mode == 'publish_fixture':
            # Deliberate publication by authorized test setup; NO native validation.
            async with conn.transaction():
                row = await conn.fetchrow('SELECT id,title,is_published FROM public.challenges WHERE slug=$1 FOR UPDATE', plan['slugs'][0])
                if not row or row['title'] != 'Permission gate fixture' or row['is_published']:
                    raise gate.GateError('Publication fixture drift')
                bench = await conn.fetchval('SELECT hidden_testbench FROM private.challenge_secrets WHERE challenge_id=$1', row['id'])
                if bench != '':
                    raise gate.GateError('Expected deliberately empty evaluator')
                await conn.execute("UPDATE public.challenges SET is_published=TRUE,validation_status='published',published_at=NOW() WHERE id=$1", row['id'])
            return {'fixture_published_without_native_validation': True}
        if mode == 'state':
            async with conn.transaction(readonly=True):
                submissions = await conn.fetch('''SELECT s.id::text,status,error_code,xp_awarded,
                    completed_at IS NOT NULL AS completed,started_at IS NOT NULL AS started,
                    worker_id IS NOT NULL AS worker,tests_total,tests_passed,tests_failed
                    FROM public.submissions s WHERE user_id=ANY($1::uuid[]) ORDER BY submitted_at''', users)
                validation = await conn.fetchrow('''SELECT validation_status,is_published,validated_at IS NULL AS not_validated
                    FROM public.challenges WHERE slug=$1''', plan['slugs'][1])
                audits = await conn.fetch('''SELECT action,details FROM public.admin_audit_log
                    WHERE target_id=ANY($1::uuid[]) AND action IN
                    ('challenge_validation_requested','challenge_validated') ORDER BY created_at''', challenges)
                profiles = await conn.fetch('SELECT xp,total_solved FROM public.profiles WHERE id=ANY($1::uuid[])', users)
                xp = await conn.fetchval('SELECT count(*) FROM public.xp_transactions WHERE user_id=ANY($1::uuid[])', users)
                completed = await conn.fetchval("SELECT count(*) FROM public.user_challenge_progress WHERE user_id=ANY($1::uuid[]) AND status='completed'", users)
            return {'submissions': [dict(r) for r in submissions],
                    'validation': dict(validation) if validation else None,
                    'audits': [{'action': r['action'], 'details': json.loads(r['details'])} for r in audits],
                    'no_awards': xp == 0 and completed == 0 and all(r['xp']==0 and r['total_solved']==0 for r in profiles)}
        if mode == 'cleanup':
            report = {}
            headers = {'apikey': capsule['service_key'], 'authorization': 'Bearer '+capsule['service_key']}
            with httpx.Client(base_url='http://host.docker.internal:54321', trust_env=False, timeout=10) as client:
                await resources.cleanup(conn, client, headers, plan, report)
            return report
        raise gate.GateError('Unknown private probe mode')
    finally:
        await asyncio.wait_for(conn.close(), 5)


if __name__ == '__main__':
    logging.disable(logging.CRITICAL)
    try:
        print(json.dumps(asyncio.run(run(json.loads(sys.stdin.buffer.read())))))
    except Exception as exc:
        # No SQL, exception text, account identifiers, source or credentials.
        print(json.dumps({'failed': True, 'failure_type': type(exc).__name__}))
        sys.exit(1)
