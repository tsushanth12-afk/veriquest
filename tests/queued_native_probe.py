"""Private stdin fixture/read/recovery SQL, not the API/worker or a grader."""
import asyncio
import json
import logging
import sys
sys.path.insert(0, '/gate')
sys.path.insert(0, '/app')
from tools import database_gate as gate
from tools import database_live_resources as resources


async def run(c):
    import asyncpg
    import httpx
    if c['mode'] == 'runtime':
        from app.db.runtime import create_runtime_pool, close_runtime_pool
        pool = await create_runtime_pool(c['dsn'], c['role']); await close_runtime_pool(pool)
        return {'runtime_pool_verified': c['role']}
    conn = await asyncpg.connect(c['operator_dsn'], timeout=5, command_timeout=15)
    try:
        await resources.bounded(conn)
        if await conn.fetchval('SELECT current_user') != 'supabase_admin': raise gate.GateError('Fixture operator mismatch')
        plan = c['plan']; users, challenges = await resources.resolve(conn, plan)
        if c['mode'] == 'setup':
            if len(users) != 2 or challenges: raise gate.GateError('Unexpected fixture baseline')
            profiles = await conn.fetch('SELECT xp,total_solved,total_attempts,level FROM public.profiles WHERE id=ANY($1::uuid[])', users)
            if len(profiles)!=2 or any(dict(r)!=dict(xp=0,total_solved=0,total_attempts=0,level=1) for r in profiles): raise gate.GateError('Nonzero signup profiles')
            if await conn.fetchval("SELECT count(*) FROM public.user_roles WHERE user_id=ANY($1::uuid[]) AND role!='student'",users): raise gate.GateError('Privileged student')
            for table in ('quests','badges','quest_challenges'):
                if await conn.fetchval('SELECT count(*) FROM public.'+table): raise gate.GateError('Unrelated accounting definitions present')
            ids=[]
            async with conn.transaction():
                for index,deadline in enumerate((5000,1000)):
                    identifier=await conn.fetchval('''INSERT INTO public.challenges(slug,title,description,difficulty,xp_reward,is_published,validation_status,published_at)
                        VALUES($1,'Permission gate fixture','Authorized native gate fixture, NOT admin validation','Easy',1,TRUE,'published',NOW()) RETURNING id''',plan['slugs'][index])
                    await conn.execute('''INSERT INTO private.challenge_secrets(challenge_id,official_solution,hidden_testbench,evaluator_type,execution_profile)
                        VALUES($1,$2,$3,'hidden_testbench',$4::jsonb)''',identifier,c['fixture']['solution'],c['fixture']['bench'],
                        json.dumps(dict(timeout_ms=deadline,memory_mb=64,cpu_limit='0.25',pids_limit=64,max_output_bytes=65536)))
                    ids.append(str(identifier))
            return {'challenge_ids':ids,'zero_profiles':2,'students_only':True,'fixture_reward':1,'publication_not_validation':True}
        if c['mode']=='state':
            async with conn.transaction(readonly=True):
                rows=await conn.fetch('''SELECT id::text,challenge_id::text,status,error_code,xp_awarded,tests_total,tests_passed,tests_failed,
                    started_at IS NOT NULL AS started,completed_at IS NOT NULL AS completed,worker_id IS NOT NULL AS worker
                    FROM public.submissions WHERE user_id=ANY($1::uuid[]) ORDER BY submitted_at''',users)
                students=[]
                for index,email in enumerate(plan['emails'][:2]):
                    uid=await conn.fetchval('SELECT id FROM auth.users WHERE email=$1',email)
                    if uid is None: continue
                    profile=await conn.fetchrow('''SELECT xp,level,total_solved,total_attempts,easy_solved,medium_solved,hard_solved,current_streak,longest_streak
                        FROM public.profiles WHERE id=$1''',uid)
                    progress=await conn.fetch('''SELECT challenge_id::text,status,attempts,completed_at IS NOT NULL AS completed
                        FROM public.user_challenge_progress WHERE user_id=$1 ORDER BY challenge_id''',uid)
                    ledger=await conn.fetch('''SELECT amount,reason,challenge_id::text,submission_id::text FROM public.xp_transactions WHERE user_id=$1 ORDER BY created_at''',uid)
                    streaks=await conn.fetch('SELECT activity_type,activity_count FROM public.streak_activity WHERE user_id=$1',uid)
                    students.append({'student':'A' if index==0 else 'B','profile':dict(profile),'progress':[dict(r) for r in progress],
                        'ledger':[dict(r) for r in ledger],'streaks':[dict(r) for r in streaks],
                        'badge_count':await conn.fetchval('SELECT count(*) FROM public.user_badges WHERE user_id=$1',uid)})
                return {'submissions':[dict(r) for r in rows],'accounting':students,
                    'quest_definitions':await conn.fetchval('SELECT count(*) FROM public.quests'),
                    'badge_definitions':await conn.fetchval('SELECT count(*) FROM public.badges')}
        if c['mode']=='cleanup':
            report={}; headers={'apikey':c['service_key'],'authorization':'Bearer '+c['service_key']}
            with httpx.Client(base_url='http://host.docker.internal:54321',trust_env=False,timeout=10) as auth:
                await resources.cleanup(conn,auth,headers,plan,report)
            return report
        raise gate.GateError('Unknown probe mode')
    finally: await asyncio.wait_for(conn.close(),5)


if __name__=='__main__':
    logging.disable(logging.CRITICAL)
    try: print(json.dumps(asyncio.run(run(json.loads(sys.stdin.buffer.read())))))
    except Exception as e:
        print(json.dumps({'failed':True,'failure_type':type(e).__name__,'sqlstate':getattr(e,'sqlstate',None)})); sys.exit(1)
