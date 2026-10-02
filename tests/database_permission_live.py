"""OPT-IN future local permission gate. Never run as part of unit discovery.

Creates three disposable real Auth identities and scoped fixtures only AFTER the
reviewed schema is applied. Uses real PostgREST/HTTP API and limited SQL logins.
No socket mount; secrets travel in private binary stdin, not Docker configuration.
"""
import argparse
import asyncio
import getpass
import json
import logging
import os
from pathlib import Path
import re
import secrets
import socket
import subprocess
import sys
import threading
import time
from urllib.parse import quote
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools import database_gate as gate
from tools import database_live_resources as resources


def private_credentials(docker):
    """Only call after gate.verify_target; never return values to terminal/logging."""
    import httpx
    db = gate.verify_target(docker)
    env = dict(x.split('=', 1) for x in db['Config']['Env'] if '=' in x)
    inspect = subprocess.run([docker, 'inspect', 'supabase_kong_veriquest-local-test'],
                             capture_output=True, check=True, timeout=10)
    gateway = json.loads(inspect.stdout)[0]
    labels = gateway['Config']['Labels']
    if labels['com.supabase.cli.workdir'].casefold() != gate.PROJECT.casefold():
        raise gate.GateError('Gateway target mismatch')
    values = dict(x.split('=', 1) for x in gateway['Config']['Env'] if '=' in x)
    content = subprocess.run([docker, 'exec', 'supabase_kong_veriquest-local-test',
                              'cat', values['KONG_DECLARATIVE_CONFIG']],
                             capture_output=True, check=True, timeout=10).stdout.decode()
    import base64
    keys = {}
    for token in re.findall(r'eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+', content):
        part = token.split('.')[1]
        role = json.loads(base64.urlsafe_b64decode(part+'='*(-len(part)%4))).get('role')
        if role in ('anon', 'service_role'):
            keys[role] = token
    if set(keys) != {'anon', 'service_role'}:
        raise gate.GateError('Local credentials unavailable')
    with httpx.Client(trust_env=False, timeout=10) as client:
        if client.get('http://127.0.0.1:54321/auth/v1/health').status_code != 200:
            raise gate.GateError('Local Auth unavailable')
    return dict(operator_password=env['POSTGRES_PASSWORD'], keys=keys)


def dsn(role, password):
    # Container transport is NOT the token issuer.
    return 'postgresql://'+role+':'+quote(password, safe='')+'@host.docker.internal:54322/postgres'


def live_inside(capsule):
    """Runs inside the actual API image; emits only safe assertion names/statuses."""
    import asyncpg
    import httpx
    import uvicorn
    logging.disable(logging.CRITICAL)
    # Require the actual API image to contain the current reviewed implementation.
    for relative, expected in capsule['source_sha256'].items():
        if gate.checksum(ROOT/'app'/relative)!=expected:
            raise gate.GateError('API image source differs from the reviewed working tree')
    api = 'http://host.docker.internal:54321'
    operator_dsn = dsn('supabase_admin', capsule['operator_password'])
    os.environ.update(DATABASE_URL=dsn('vq_api', capsule['api_password']),
                      JWT_ISSUER='http://127.0.0.1:54321/auth/v1',
                      JWT_JWKS_URL=api+'/auth/v1/.well-known/jwks.json',
                      JWT_ALGORITHMS='ES256', REDIS_URL='redis://127.0.0.1:1/0')
    # No dependency overrides: real verifier, real pool, real lifespan, real limiter.
    from app.main import app
    from app.db.runtime import create_runtime_pool, close_runtime_pool
    from app.submissions.service import create_submission, record_publication_failure
    from app.gamification.xp import award_xp, update_streak, check_quest_completion

    report = {'assertions': 0, 'cases': [], 'cleanup': {}, 'live': True, 'failed': False}
    accounts = []; challenges = []; quests = []; badges = []
    plan=capsule['resource_plan']
    suffix=plan['nonce']
    server = thread = bound = None
    cleanup_allowed=False
    admin = {'apikey': capsule['keys']['service_role'],
             'authorization': 'Bearer '+capsule['keys']['service_role']}
    public = {'apikey': capsule['keys']['anon']}

    def check(ok, name):
        if not ok:
            raise AssertionError(name)
        report['assertions'] += 1

    def interrupt(point):
        if capsule.get('interrupt_point')==point:
            # Deliberately bypass Python finally: only the durable PRE-write
            # intent remains. No returned account/challenge ID is journalled.
            print(json.dumps({'controlled_interruption':point,'assertions':report['assertions'],
                              'cases':report['cases']}),flush=True)
            os._exit(86)

    async def operator(sql, *args):
        start=time.monotonic()
        conn = await asyncpg.connect(operator_dsn, timeout=5, command_timeout=15,
            server_settings={'statement_timeout':'10000','lock_timeout':'1500',
                             'idle_in_transaction_session_timeout':'10000'})
        report.setdefault('operator_connect_ms',[]).append(round((time.monotonic()-start)*1000,2))
        try:
            return await resources.TimedConnection(conn,report,'fixture_operator').fetch(sql, *args)
        finally:
            await conn.close(timeout=5)

    def op(sql, *args):
        return asyncio.run(operator(sql, *args))

    with httpx.Client(base_url=api, trust_env=False, timeout=20) as client:
        def rest(method, table, identity=None, body=None, query=''):
            headers = dict(public)
            if identity is not None: headers['authorization'] = 'Bearer '+accounts[identity]['token']
            headers['Prefer'] = 'return=representation'
            response = client.request(method, '/rest/v1/'+table+query, headers=headers, json=body)
            evidence={'surface':'PostgREST', 'operation':method+' '+table, 'status':response.status_code}
            if response.is_error:
                code=response.json().get('code')
                if isinstance(code,str) and re.fullmatch(r'[A-Z0-9]{5,12}',code):
                    evidence['error_code']=code  # Never include messages, rows or credentials.
            report['cases'].append(evidence)
            return response

        def snapshot():
            ids = [a['id'] for a in accounts]
            # A bounded fingerprint detects mixed-write partial success and protected changes.
            return [tuple(r) for r in op('SELECT id,username,display_name,bio,avatar_url,xp,level,current_streak,longest_streak,total_solved,easy_solved,medium_solved,hard_solved,total_attempts FROM public.profiles WHERE id=ANY($1::uuid[]) ORDER BY id', ids)]

        try:
            # BYPASSRLS alone is not object write permission. Require the actual
            # platform migration operator for explicitly authorized test fixtures.
            authority=op("SELECT current_user='supabase_admin' AND rolsuper AS trusted FROM pg_catalog.pg_roles WHERE rolname=current_user")
            check(authority and authority[0]['trusted'] is True,'Verified local fixture operator login')
            async def unused():
                conn=await asyncpg.connect(operator_dsn,timeout=5,command_timeout=15)
                try:
                    await resources.bounded(conn)
                    await resources.assert_unused(conn,plan)
                finally:await conn.close(timeout=5)
            asyncio.run(unused())
            cleanup_allowed=True
            # Real Auth administration/sign-in; role/scoring metadata deliberately hostile.
            for index in range(3):
                email = plan['emails'][index]
                password = secrets.token_urlsafe(40)
                meta = {'username':'same-requested-name', 'role':'admin', 'xp':999999,'vq_gate_run':suffix,
                        'display_name':'D'*150 if index == 0 else {'malformed':True}}
                if index<2:
                    response=client.post('/auth/v1/signup',headers=public,
                        json={'email':email,'password':password,'data':meta})
                    auth_path='POST /auth/v1/signup'
                else:
                    response = client.post('/auth/v1/admin/users', headers=admin,
                        json={'email':email,'password':password,'email_confirm':True,'user_metadata':meta})
                    auth_path='POST /auth/v1/admin/users'
                report['cases'].append({'surface':'Auth','operation':auth_path,'status':response.status_code})
                if index==0 and response.status_code in (200,201):interrupt('signup_response')
                if response.status_code in (200,201):
                    document=response.json()
                    accounts.append({'id':document.get('user',document)['id']})  # Retain before next request.
                check(response.status_code in (200,201), 'Auth account creation')
                signed = client.post('/auth/v1/token?grant_type=password', headers=public,
                                     json={'email':email,'password':password})
                report['cases'].append({'surface':'Auth','operation':'POST /auth/v1/token?grant_type=password','status':signed.status_code})
                check(signed.status_code == 200, 'Real Auth sign-in')
                accounts[-1]['token'] = signed.json()['access_token']
                del password, signed, response
            a,b,c = [x['id'] for x in accounts]
            for index, account in enumerate(accounts):
                rows = op('SELECT username,display_name,xp,level,total_attempts,total_solved,current_streak FROM public.profiles WHERE id=$1::uuid', account['id'])
                row = rows[0]
                check(row['username']=='vq_user_'+account['id'].replace('-',''), 'Full UUID reserved username')
                check(row['display_name']==('D'*100 if index==0 else 'Student'), 'Bounded/malformed metadata')
                check(tuple(row[k] for k in ('xp','level','total_attempts','total_solved','current_streak'))==(0,1,0,0,0), 'Zero initial scoring')
                check([r['role'] for r in op('SELECT role FROM public.user_roles WHERE user_id=$1::uuid', account['id'])]==['student'], 'Metadata cannot grant admin')
            op("INSERT INTO public.user_roles(user_id,role) VALUES($1::uuid,'admin')", c)

            bound = socket.socket(); bound.bind(('127.0.0.1',0))
            port = bound.getsockname()[1]
            server = uvicorn.Server(uvicorn.Config(app, access_log=False, log_level='critical'))
            thread = threading.Thread(target=lambda:server.run(sockets=[bound]), daemon=True); thread.start()
            base = 'http://127.0.0.1:'+str(port)
            deadline = time.monotonic()+30
            while time.monotonic()<deadline:
                try:
                    if httpx.get(base+'/health', trust_env=False, timeout=1).status_code==200: break
                except httpx.HTTPError: pass
                time.sleep(.1)
            else: raise AssertionError('Real API lifespan startup')
            check(server.started, 'Production limited-role HTTP startup')
            report['api_startup']={'full_lifespan':True,'health_status':200,
                                   'bind_address':bound.getsockname()[0],
                                   'ephemeral_port':bound.getsockname()[1]}

            def request(method, path, index=0, body=None):
                headers={'authorization':'Bearer '+accounts[index]['token']}
                response=httpx.request(method,base+path,headers=headers,json=body,trust_env=False,timeout=20)
                safe_path=re.sub(r'[0-9a-fA-F]{8}-(?:[0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}','<resource>',path.split('?')[0])
                report['cases'].append({'surface':'API','operation':method+' '+safe_path, 'status':response.status_code})
                return response

            check(request('GET','/api/v1/admin/challenges').status_code==403, 'Student admin API denied')
            check(request('GET','/api/v1/admin/challenges',2).status_code==200, 'Operator-provisioned admin API')
            # Creation must use real server ID. Fixture publication below is NOT native validation.
            for index in range(3):
                created=request('POST','/api/v1/admin/challenges',2,dict(slug=plan['slugs'][index],title='Permission gate fixture',official_solution='fixture only',hidden_testbench='fixture only'))
                if index==0 and created.status_code==201:interrupt('challenge_response')
                if created.status_code==201: challenges.append(created.json()['challenge_id'])
                check(created.status_code==201, 'Real admin draft/secret/audit insertion')
            published,draft,archived=challenges
            op("UPDATE public.challenges SET is_published=true,validation_status='published',is_archived=(id=$2::uuid) WHERE id=ANY($1::uuid[])", [published,archived],archived)
            for left,right in [(published,draft),(published,archived)]:
                op('INSERT INTO public.challenge_prerequisites(challenge_id,prerequisite_id) VALUES($1::uuid,$2::uuid)',left,right)
            for index,active in enumerate((True,False)):
                q=plan['quests'][index];quests.append(q)
                op("INSERT INTO public.quests(id,title,category,is_active) VALUES($1::uuid,'Permission fixture','Fundamentals',$2)",q,active)
                for ch in challenges: op('INSERT INTO public.quest_challenges(quest_id,challenge_id) VALUES($1::uuid,$2::uuid)',q,ch)
            for index,badge in enumerate(plan['badges']):
                badges.append(badge)
                op("INSERT INTO public.badges(id,name) VALUES($1::uuid,$2)",badge,'permission-'+suffix+'-'+str(index))
            badge=badges[0]
            for method,path,body in [('GET','/api/v1/admin/challenges/'+published,None),
                ('POST','/api/v1/admin/challenges',dict(slug=plan['slugs'][3],title='denied')),
                ('PUT','/api/v1/admin/challenges/'+published,dict(title='denied')),
                ('POST','/api/v1/admin/challenges/'+draft+'/validate',None),
                ('POST','/api/v1/admin/challenges/'+draft+'/publish',None),
                ('POST','/api/v1/admin/challenges/'+published+'/unpublish',None),
                ('GET','/api/v1/admin/audit-log',None)]:
                check(request(method,path,0,body).status_code==403,'Student staff operation denied')

            for identity in (None,0,1,2):
                response=rest('GET','challenges',identity,query='?select=id&id=in.('+','.join(challenges)+')')
                check(response.status_code==200 and {x['id'] for x in response.json()}=={published}, 'Published nonarchived catalog only')
                response=rest('GET','challenge_prerequisites',identity,query='?select=id&challenge_id=eq.'+published)
                check(response.status_code==200 and response.json()==[], 'No draft/archived prerequisites')
                response=rest('GET','quest_challenges',identity,query='?select=quest_id,challenge_id&quest_id=in.('+','.join(quests)+')')
                check(response.status_code==200 and response.json()==[{'quest_id':quests[0],'challenge_id':published}], 'Active quest and visible challenge links only')

            check(rest('GET','profiles',0,query='?select=id').json()==[{'id':a}], 'Own profile only')
            check(rest('PATCH','profiles',0,{'bio':'safe'},'?id=eq.'+a).status_code==200,'Own safe display edit')
            check(rest('PATCH','profiles',0,{'bio':'other'},'?id=eq.'+b).json()==[], 'Other profile invisible on update')
            stable=snapshot()
            for field,value in {'id':b,'username':'forged','xp':100,'level':4,'current_streak':4,'longest_streak':4,'total_solved':1,'easy_solved':1,'medium_solved':1,'hard_solved':1,'total_attempts':2}.items():
                for body in ({field:value},{'bio':'mixed-must-not-apply',field:value}):
                    response=rest('PATCH','profiles',0,body,'?id=eq.'+a)
                    check(response.status_code==403 and response.json().get('code')=='42501','Protected/mixed profile write denied')
                    check(snapshot()==stable,'Denied profile state unchanged')
            response=rest('PATCH','profiles',0,{'display_name':'x'*101},'?id=eq.'+a)
            check(response.status_code==400 and response.json().get('code')=='23514','Display constraint')
            check(snapshot()==stable,'Constraint denial unchanged')

            async def runtime_checks():
                api_pool=resources.TimedPool(await create_runtime_pool(dsn('vq_api',capsule['api_password']),'vq_api'),report,'vq_api')
                worker_pool=None
                try:
                    worker_pool=resources.TimedPool(await create_runtime_pool(dsn('vq_worker',capsule['worker_password']),'vq_worker'),report,'vq_worker')
                    report['runtime_tcp_pools']=['vq_api','vq_worker']
                    for role,pool in [('vq_api',api_pool),('vq_worker',worker_pool)]:
                        report['active_sql_step']=role+' column ACLs and denied capabilities'
                        async with pool.acquire() as conn:
                            spec=json.loads((ROOT/'tools/database_policy.json').read_text())
                            for table,columns in spec['columns'].items():
                                for col in columns:
                                    for operation in ('SELECT','INSERT','UPDATE','REFERENCES'):
                                        actual=await conn.fetchval('SELECT pg_catalog.has_column_privilege(current_user,$1,$2,$3)',table,col,operation)
                                        expected=col in spec['rights'][role].get(table,{}).get(operation,[])
                                        check(actual==expected,'Runtime exact column ACL')
                            # Real statements, not operator SET ROLE or catalog-only evidence.
                            denied=['SET ROLE vq_owner','SET ROLE vq_api' if role=='vq_worker' else 'SET ROLE vq_worker',
                                    'SET ROLE authenticated','CREATE TABLE public.forbidden_probe(id int)',
                                    'SELECT id FROM auth.users','SELECT secret FROM vault.secrets',
                                    'SELECT version FROM private.schema_migrations',
                                    'SELECT private.handle_new_user()',
                                    "INSERT INTO public.user_roles(user_id,role) VALUES('"+a+"','admin')",
                                    "UPDATE public.profiles SET username='forged' WHERE id='"+a+"'"]
                            if role=='vq_api': denied += ["UPDATE public.submissions SET xp_awarded=1", "UPDATE public.profiles SET xp=100"]
                            else: denied += ['SELECT private_notes FROM private.challenge_secrets','UPDATE public.submissions SET submitted_code=\'forged\'', 'UPDATE public.challenges SET is_published=true']
                            for sql in denied:
                                tx=conn.transaction();await tx.start()
                                try:
                                    try: await conn.execute(sql)
                                    except asyncpg.InsufficientPrivilegeError: check(True,'Actual runtime capability denied')
                                    else: raise AssertionError('Runtime forbidden statement succeeded')
                                finally: await tx.rollback()
                    # Controlled contention proves bounded handling, not the cause
                    # of the historical timeout. No retry and no committed update.
                    report['active_sql_step']='Controlled row-lock and statement bounds'
                    blocker=await asyncpg.connect(operator_dsn,timeout=5,command_timeout=15)
                    lock=blocker.transaction();await lock.start()
                    try:
                        await resources.bounded(blocker)
                        await blocker.fetchval('SELECT id FROM public.profiles WHERE id=$1::uuid FOR UPDATE',a)
                        async with api_pool.acquire() as conn:
                            tx=conn.transaction();await tx.start()
                            try:
                                await conn.execute("SET LOCAL lock_timeout='250ms'")
                                start=time.monotonic()
                                try:await conn.execute("UPDATE public.profiles SET bio='must-not-commit' WHERE id=$1::uuid",a)
                                except asyncpg.LockNotAvailableError:check(True,'Controlled lock cutoff 55P03')
                                else:raise AssertionError('Controlled row lock did not fail closed')
                                report['controlled_lock_ms']=round((time.monotonic()-start)*1000,2)
                            finally:await tx.rollback()
                    finally:
                        await lock.rollback();await blocker.close(timeout=5)
                    async with api_pool.acquire() as conn:
                        check(await conn.fetchval('SELECT bio FROM public.profiles WHERE id=$1::uuid',a)=='safe','Lock cutoff unchanged and connection recovered')
                        tx=conn.transaction();await tx.start()
                        try:
                            await conn.execute("SET LOCAL statement_timeout='150ms'")
                            start=time.monotonic()
                            try:await conn.fetchval('SELECT pg_catalog.pg_sleep(2)')
                            except asyncpg.QueryCanceledError:check(True,'Controlled statement cutoff 57014')
                            else:raise AssertionError('Statement bound was not enforced')
                            report['controlled_statement_ms']=round((time.monotonic()-start)*1000,2)
                        finally:await tx.rollback()
                        check(await conn.fetchval('SELECT 1')==1,'Valid SQL after cancellation')
                    # Current real service INSERT + duplicate + progress upsert + narrow failure.
                    report['active_sql_step']='API create submission'
                    first=await create_submission(api_pool,a,published,'module fixture; endmodule',suffix)
                    check(first and first['status']=='queued','Production submission service under vq_api')
                    duplicate=await create_submission(api_pool,a,published,'ignored',suffix)
                    check(duplicate['is_duplicate'] and duplicate['submission_id']==first['submission_id'],'Real duplicate lookup')
                    second=await create_submission(api_pool,a,published,'module fixture; endmodule')
                    report['active_sql_step']='API record publication failure'
                    await record_publication_failure(api_pool,second['submission_id'],False)
                    async with api_pool.acquire() as conn:
                        tx=conn.transaction();await tx.start()
                        try:
                            try: await conn.execute("INSERT INTO public.submissions(user_id,challenge_id,status,submitted_code) VALUES($1::uuid,$2::uuid,'accepted','forged')",a,published)
                            except asyncpg.InsufficientPrivilegeError: check(True,'API forged pregraded row RLS denial')
                            else: raise AssertionError('API accepted insertion succeeded')
                        finally: await tx.rollback()
                    async with worker_pool.acquire() as conn:
                        report['active_sql_step']='Worker rollback scoring fixture'
                        tx=conn.transaction();await tx.start()
                        try:
                            await conn.fetchrow('SELECT official_solution,hidden_testbench,execution_profile FROM private.challenge_secrets WHERE challenge_id=$1::uuid',published)
                            await conn.execute("UPDATE public.submissions SET status='compiling',started_at=now(),worker_id='permission-probe' WHERE id=$1::uuid",first['submission_id'])
                            # SQL capability fixture only: no claim of real grader execution or XP correctness.
                            result=await award_xp(conn,a,published,first['submission_id'],50)
                            check(result['xp_awarded']==50,'Real worker award SQL/row lock under restricted login')
                            await update_streak(conn,a);await update_streak(conn,a)
                            await check_quest_completion(conn,a,published)
                            await conn.execute('INSERT INTO public.user_badges(user_id,badge_id) VALUES($1::uuid,$2::uuid) ON CONFLICT(user_id,badge_id) DO NOTHING',a,badge)
                            await conn.execute("INSERT INTO public.admin_audit_log(admin_user_id,action,target_type,target_id) VALUES($1::uuid,'permission_probe','challenge',$2::uuid)",c,published)
                        finally: await tx.rollback()
                    # Conditional validation rights, deliberately not simulator evidence.
                    report['active_sql_step']='Operator pending validation fixture'
                    await operator("UPDATE public.challenges SET validation_status='validating' WHERE id=$1::uuid",draft)
                    async with worker_pool.acquire() as conn:
                        tx=conn.transaction();await tx.start()
                        try:
                            check(await conn.fetchval("UPDATE public.challenges SET validation_status='validated',validated_at=now() WHERE id=$1::uuid AND NOT is_published AND validation_status='validating' RETURNING id",draft) is not None,'Worker pending validation update')
                            check(await conn.execute("UPDATE public.challenges SET validation_status='validation_failed' WHERE id=$1::uuid",published)=='UPDATE 0','Worker cannot change published validation')
                        finally: await tx.rollback()
                    return first['submission_id']
                finally:
                    if worker_pool: await close_runtime_pool(worker_pool)
                    await close_runtime_pool(api_pool)

            submission=asyncio.run(runtime_checks())
            check(op('SELECT xp FROM public.profiles WHERE id=$1::uuid',a)[0]['xp']==0,'Worker SQL fixture rollback leaves zero XP')
            # Committed permission fixtures, NOT grading/accounting outputs.
            for index,identifier in enumerate((a,b)):
                op("INSERT INTO public.xp_transactions(id,user_id,amount,reason) VALUES($1::uuid,$2::uuid,$3,'permission_fixture')",plan['xp'][index],identifier,(17,29)[index])
                op('INSERT INTO public.user_badges(id,user_id,badge_id) VALUES($1::uuid,$2::uuid,$3::uuid)',plan['awards'][index],identifier,badges[index+1])
                op("INSERT INTO public.streak_activity(id,user_id,activity_date,activity_count) VALUES($1::uuid,$2::uuid,$3::date,$4)",plan['streaks'][index],identifier,__import__('datetime').date(2026,9,27+index),index+1)
                op('UPDATE public.profiles SET xp=$2,current_streak=$3 WHERE id=$1::uuid',identifier,(17,29)[index],index+1)
            report['populated_fixture_counts']={'xp_transactions':2,'user_badges':2,'streak_activity':2}
            interrupt('populated_fixtures')
            def authoritative_snapshot():
                ids=[x['id'] for x in accounts]
                tables=('submissions','user_challenge_progress','xp_transactions','user_badges','streak_activity','user_roles')
                return [op('SELECT coalesce(jsonb_agg(to_jsonb(t) ORDER BY id),\'[]\'::jsonb) AS data FROM public.'+table+' t WHERE user_id=ANY($1::uuid[])',ids)[0]['data'] for table in tables]
            protected_before=authoritative_snapshot()
            populated_specs=[('xp_transactions',plan['xp'],'id,user_id,amount',lambda i,row:row['amount']==(17,29)[i]),
                ('user_badges',plan['awards'],'id,user_id,badge_id',lambda i,row:row['badge_id']==badges[i+1]),
                ('streak_activity',plan['streaks'],'id,user_id,activity_count',lambda i,row:row['activity_count']==i+1)]
            for table,identifiers,columns,matches in populated_specs:
                for identity in (0,1):
                    response=rest('GET',table,identity,query='?select='+columns+'&id=in.('+','.join(identifiers)+')')
                    rows=response.json()
                    check(response.status_code==200 and len(rows)==1 and rows[0]['id']==identifiers[identity] and rows[0]['user_id']==(a,b)[identity] and matches(identity,rows[0]),'Populated own records exact')
                    response=rest('GET',table,identity,query='?select='+columns+'&id=eq.'+identifiers[1-identity])
                    check(response.status_code==200 and response.json()==[],'Populated other record invisible')
                response=rest('GET',table,None,query='?select='+columns+'&id=in.('+','.join(identifiers)+')')
                check(response.status_code==401 and response.json().get('code')=='42501','Anonymous populated records denied')
                for identity in (None,0,1):
                    for method,body in [('POST',{'user_id':a,'amount':999,'reason':'forged'} if table=='xp_transactions' else {'user_id':a,'badge_id':badges[1]} if table=='user_badges' else {'user_id':a,'activity_date':'2026-09-27'}),
                        ('PATCH',{'amount':999} if table=='xp_transactions' else {'badge_id':badges[2]} if table=='user_badges' else {'activity_count':999}),('DELETE',None)]:
                        response=rest(method,table,identity,body,'?id=eq.'+identifiers[0])
                        check(response.status_code==(401 if identity is None else 403) and response.json().get('code')=='42501','Populated authoritative mutation denied')
                        check(authoritative_snapshot()==protected_before,'Populated denied mutation leaves exact state unchanged')
            for identity in (0,1):
                response=request('GET','/api/v1/profile?user_id='+(b,a)[identity],identity)
                document=response.json()
                check(response.status_code==200 and document['id']==(a,b)[identity] and document['stats']['currentXP']==(17,29)[identity] and document['stats']['currentStreak']==identity+1 and {row['id'] for row in document['badges']}=={badges[identity+1]},'Real API populated profile ignores identity spoof and isolates badge/stats')
            anonymous=httpx.get(base+'/api/v1/profile',trust_env=False,timeout=20)
            report['cases'].append({'surface':'API','operation':'GET /api/v1/profile anonymous','status':anonymous.status_code})
            check(anonymous.status_code==401,'Anonymous populated API profile denied')
            for table in ('submissions','user_challenge_progress','xp_transactions','user_badges','streak_activity','user_roles'):
                response=rest('GET',table,1,query='?select=user_id&user_id=eq.'+a)
                check(response.status_code==200 and response.json()==[],'Other user private rows isolated')
            for status in ('queued','accepted'):
                response=rest('POST','submissions',0,dict(user_id=a,challenge_id=published,status=status,submitted_code='forged',tests_total=1,tests_passed=1,xp_awarded=100))
                check(response.status_code==403,'Client queued/pregraded insertion denied')
            for table,body in [('user_challenge_progress',dict(user_id=a,challenge_id=published,status='completed')),
                ('xp_transactions',dict(user_id=a,amount=100,reason='forged')),
                ('user_roles',dict(user_id=a,role='admin')),('user_badges',dict(user_id=a,badge_id=badge)),
                ('streak_activity',dict(user_id=a,activity_date='2026-10-01')),('admin_audit_log',dict(admin_user_id=a,action='forged',target_type='challenge'))]:
                check(rest('POST',table,0,body).status_code==403,'Client authoritative insertion denied')
                # Target the fixture owner; unfiltered updates can fail a platform
                # safeguard before column permissions are evaluated.
                response=rest('PATCH',table,0,body,'?'+('admin_user_id' if table=='admin_audit_log' else 'user_id')+'=eq.'+a)
                check(response.status_code==403 and response.json().get('code')=='42501','Client authoritative update denied')
                check(rest('DELETE',table,0,query='?'+('admin_user_id' if table=='admin_audit_log' else 'user_id')+'=eq.'+a).status_code==403,'Client authoritative deletion denied')
            check(rest('PATCH','submissions',0,dict(status='accepted',tests_passed=10,xp_awarded=100),'?id=eq.'+submission).status_code==403,'Client result modification denied')
            check(rest('DELETE','submissions',0,query='?id=eq.'+submission).status_code==403,'Client submission deletion denied')
            check(authoritative_snapshot()==protected_before,'All denied authoritative writes leave rows unchanged')
            hidden=client.get('/rest/v1/challenge_secrets?select=challenge_id',headers={**public,'authorization':'Bearer '+accounts[0]['token'],'Accept-Profile':'private'})
            check(hidden.status_code==406,'Private schema not exposed')
            check(request('GET','/api/v1/admin/challenges/'+published).status_code==403,'Student hidden API denied')
            check(request('GET','/api/v1/submissions/'+submission,1).status_code==404,'API submission ownership')
            check(request('GET','/api/v1/submissions/'+submission).status_code==200,'API own submission read')
            check(request('PATCH','/api/v1/profile',0,{'bio':'API safe'}).status_code==200,'API safe profile edit')
            check(request('PATCH','/api/v1/profile',0,{'bio':'API mixed safe','xp':99999,'role':'admin'}).json().get('updated_fields')==['bio'],'API mixed payload filters protected fields')
            check(request('PATCH','/api/v1/profile',0,{'xp':99999}).json().get('message')=='No valid fields to update','API protected-only truthful no-op')
            http_key=suffix+'-http-owner'
            dispatched=request('POST','/api/v1/submissions',0,dict(challenge_id=published,submitted_code='module fixture; endmodule',user_id=b,role='admin',idempotency_key=http_key))
            check(dispatched.status_code==503 and dispatched.json()['error']['code']=='DISPATCH_FAILED','Real unavailable broker failure persisted under vq_api')
            check(str(op('SELECT user_id FROM public.submissions WHERE idempotency_key=$1',http_key)[0]['user_id'])==a,'HTTP body cannot spoof submission identity')
            op("DELETE FROM public.user_roles WHERE user_id=$1::uuid AND role='admin'",c)
            check(request('GET','/api/v1/admin/challenges',2).status_code==403,'Admin grant revocation with same live token')
            check([op('SELECT xp FROM public.profiles WHERE id=$1::uuid',u)[0]['xp'] for u in (a,b)]==[17,29],'Permission fixture profile values remain unchanged')
            ledger=op('SELECT version,sha256 FROM private.schema_migrations ORDER BY version')
            check({r['version']:r['sha256'] for r in ledger}=={m['version']:m['sha256'] for m in gate.load_plan()['migrations']},'Exact live migration tracking and no 002')
        except Exception as exc:
            report['failed']=True;report['failure_type']=type(exc).__name__
            if isinstance(exc,AssertionError): report['failed_assertion']=str(exc)
            sqlstate=getattr(exc,'sqlstate',None)
            if isinstance(sqlstate,str) and re.fullmatch(r'[A-Z0-9]{5}',sqlstate):report['failure_sqlstate']=sqlstate
        finally:
            if server: server.should_exit=True
            if thread: thread.join(timeout=10);report['cleanup']['api_stopped']=not thread.is_alive()
            if bound: bound.close()
            # One FK-ordered SQL transaction, then supported Auth deletion. Intent
            # resolves generated IDs even when their creation response was lost.
            if cleanup_allowed and (thread is None or not thread.is_alive()):
                async def clean():
                    conn=await asyncpg.connect(operator_dsn,timeout=5,command_timeout=15)
                    try:await resources.cleanup(resources.TimedConnection(conn,report,'cleanup_operator'),client,admin,plan,report['cleanup'])
                    finally:await conn.close(timeout=5)
                try:asyncio.run(clean())
                except Exception as exc:
                    report['cleanup']['resources_absent']=False
                    report['cleanup']['failure_type']=type(exc).__name__
                    code=getattr(exc,'sqlstate',None)
                    if isinstance(code,str) and re.fullmatch(r'[A-Z0-9]{5}',code):report['cleanup']['sqlstate']=code
            else:report['cleanup']['resources_absent']=False
    return report


def recovery_inside(capsule):
    import asyncpg
    import httpx
    logging.disable(logging.CRITICAL)
    report={'recovery':True,'failed':False,'cleanup':{}}
    headers={'apikey':capsule['keys']['service_role'],'authorization':'Bearer '+capsule['keys']['service_role']}
    with httpx.Client(base_url='http://host.docker.internal:54321',trust_env=False,timeout=20) as client:
        async def clean():
            conn=await asyncpg.connect(dsn('supabase_admin',capsule['operator_password']),timeout=5,command_timeout=15)
            try:
                trusted=await conn.fetchval("SELECT current_user='supabase_admin' AND rolsuper FROM pg_catalog.pg_roles WHERE rolname=current_user")
                if trusted is not True:raise gate.GateError('Recovery operator identity mismatch')
                await resources.cleanup(resources.TimedConnection(conn,report,'recovery_operator'),client,headers,capsule['resource_plan'],report['cleanup'])
            finally:await conn.close(timeout=5)
        try:asyncio.run(clean())
        except Exception as exc:
            report['failed']=True;report['failure_type']=type(exc).__name__
            code=getattr(exc,'sqlstate',None)
            if isinstance(code,str) and re.fullmatch(r'[A-Z0-9]{5}',code):report['sqlstate']=code
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--docker');parser.add_argument('--image')
    parser.add_argument('--live',action='store_true')
    parser.add_argument('--authorize-local-test-writes',action='store_true')
    parser.add_argument('--inside',action='store_true',help=argparse.SUPPRESS)
    parser.add_argument('--journal')
    parser.add_argument('--recover',action='store_true')
    parser.add_argument('--interrupt-point',choices=['signup_response','challenge_response','populated_fixtures'])
    args=parser.parse_args()
    if args.inside:
        capsule=json.loads(sys.stdin.buffer.read())
        report=recovery_inside(capsule) if capsule.get('recover') else live_inside(capsule)
        print(json.dumps(report))
        return 1 if report['failed'] or any(x is False for x in report['cleanup'].values()) else 0
    if not args.live or not args.authorize_local_test_writes or not args.docker or not args.image or not args.journal:
        print('Refused: requires separate live-test authorization, --live, --authorize-local-test-writes, --docker, --image and private --journal',file=sys.stderr);return 2
    name='vq-db-live-'+uuid4().hex
    started=False
    child=None
    try:
        from tools import database_live_gate as private
        manifest=gate.load_plan();target=gate.verify_target(args.docker)
        if gate.preflight(args.docker,manifest)['state']!='complete': raise gate.GateError('Reviewed migration gate must be applied first')
        gate.psql(args.docker,'BEGIN TRANSACTION READ ONLY;'+gate.assertions_sql()+'ROLLBACK;')
        path=Path(args.journal).resolve();directory=private.checked_directory(path.parent)
        private.secure_directory(directory);private.journal_path(directory,str(path))
        plan=private.read_sealed(path);resources.validate_plan(plan,target,manifest)
        if args.recover:
            # Refuse recovery while the original writer container still exists.
            original=subprocess.run([args.docker,'inspect',plan['container_name']],capture_output=True)
            if original.returncode==0:raise gate.GateError('Original writer exists; stop it before recovery')
        else:name=plan['container_name']
        capsule=private_credentials(args.docker)
        capsule['resource_plan']=plan;capsule['recover']=args.recover
        capsule['interrupt_point']=args.interrupt_point
        capsule['source_sha256']={str(p.relative_to(ROOT/'backend/app')).replace('\\','/'):gate.checksum(p)
                                 for p in (ROOT/'backend/app').rglob('*.py')}
        capsule['api_password']=getpass.getpass('Private vq_api password: ')
        capsule['worker_password']=getpass.getpass('Private vq_worker password: ')
        command=[args.docker,'run','--rm','-i','--name',name,'--label','com.veriquest.permission-run='+plan['nonce'],'--read-only','--cap-drop=ALL',
                 '--security-opt=no-new-privileges:true','--memory=384m','--pids-limit=64',
                 '--tmpfs','/tmp:rw,noexec,nosuid,size=16m']
        for source,target in [('tools','/app/tools'),('supabase','/app/supabase'),('tests/database_permission_live.py','/app/tests/database_permission_live.py')]:
            command+=['--mount','type=bind,source='+str(ROOT/source)+',target='+target+',readonly']
        command += [args.image,'python','-B','/app/tests/database_permission_live.py','--inside']
        started=True
        # No timeout kill: interrupt/process death requires the scoped recovery described in runbook.
        # Inspect the real created container before releasing any secret capsule
        # or allowing its account/fixture writes. No environment is reported.
        child=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        deadline=time.monotonic()+15
        while True:
            inspected=subprocess.run([args.docker,'inspect',name],capture_output=True)
            if inspected.returncode==0 and json.loads(inspected.stdout)[0]['State']['Running']: break
            if child.poll() is not None or time.monotonic()>=deadline:
                raise gate.GateError('Temporary container inspection unavailable; account writes not authorized')
            time.sleep(.1)
        obj=json.loads(inspected.stdout)[0]; host=obj['HostConfig']
        isolation={'running':obj['State']['Running'],'port_bindings':host['PortBindings'],
                   'readonly_rootfs':host['ReadonlyRootfs'],'cap_drop':host['CapDrop'],
                   'security_opt':host['SecurityOpt'],'memory':host['Memory'],'pids_limit':host['PidsLimit'],
                   'network_mode':host['NetworkMode'],
                   'no_socket_mount':not any('docker.sock' in m['Destination'] for m in obj['Mounts']),
                   'bind_mounts_readonly':all(not m['RW'] for m in obj['Mounts'] if m['Type']=='bind')}
        if (isolation['port_bindings'] or not isolation['readonly_rootfs']
            or isolation['cap_drop']!=['ALL'] or not isolation['no_socket_mount']
            or not isolation['bind_mounts_readonly'] or isolation['memory']!=384*1024*1024
            or isolation['pids_limit']!=64 or 'no-new-privileges:true' not in isolation['security_opt']):
            raise gate.GateError('Temporary container isolation drift; account writes not authorized')
        output,diagnostics=child.communicate(input=json.dumps(capsule).encode())
        capsule=None
        report=json.loads(output);report['container_inspection']=isolation
        print(json.dumps(report,indent=2));return child.returncode
    except Exception as exc:
        print('Live gate failed: '+(str(exc) if isinstance(exc,gate.GateError) else 'private diagnostics withheld'),file=sys.stderr);return 1
    finally:
        if started:
            removed=subprocess.run([args.docker,'rm','-f',name],capture_output=True)
            # --rm normally already removed it. Only owned name is ever targeted.
            if removed.returncode and b'No such container' not in removed.stderr:
                print('Temporary live container cleanup failed',file=sys.stderr)
                return 1
            if child is not None:
                child.communicate(timeout=10)


if __name__=='__main__':sys.exit(main())
