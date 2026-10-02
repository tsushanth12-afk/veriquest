"""Exact predeclared permission-test resources and bounded native SQL helpers.

No schema changes, migrations, broad prefix searches, or credential logging.
The Windows driver seals intent before the Linux harness can create resources.
"""
from contextlib import asynccontextmanager
import json
import re
import time
from uuid import UUID, uuid4

from tools import database_gate as gate


class UnrelatedFixtureReference(gate.GateError):
    """Safe typed refusal; callers never need to report the referenced identity."""


def new_plan(target, manifest):
    nonce=uuid4().hex
    return {'format':1,'project':'veriquest-local-test','container_id':target['Id'],
            'manifest':manifest,'nonce':nonce,'container_name':'vq-db-live-'+nonce,
            'emails':['vq-db-gate-'+nonce+'-'+str(i)+'@example.com' for i in range(3)],
            'slugs':['permission-'+nonce+'-'+str(i) for i in range(3)]+['denied-'+nonce],
            'quests':[str(uuid4()) for _ in range(2)],
            'badges':[str(uuid4()) for _ in range(3)],
            'xp':[str(uuid4()) for _ in range(2)],
            'awards':[str(uuid4()) for _ in range(2)],
            'streaks':[str(uuid4()) for _ in range(2)]}


def validate_plan(plan, target, manifest):
    try:
        n=plan['nonce']
        if (plan['format']!=1 or plan['project']!='veriquest-local-test'
            or plan['container_id']!=target['Id'] or plan['manifest']!=manifest
            or not re.fullmatch(r'[0-9a-f]{32}',n)
            or plan['container_name']!='vq-db-live-'+n
            or plan['emails']!=['vq-db-gate-'+n+'-'+str(i)+'@example.com' for i in range(3)]
            or plan['slugs']!=['permission-'+n+'-'+str(i) for i in range(3)]+['denied-'+n]):
            raise ValueError
        values=[]
        for key,count in [('quests',2),('badges',3),('xp',2),('awards',2),('streaks',2)]:
            if len(plan[key])!=count:raise ValueError
            for value in plan[key]:
                if str(UUID(value))!=value:raise ValueError
                values.append(value)
        if len(values)!=len(set(values)):raise ValueError
    except (KeyError,TypeError,ValueError,AttributeError):
        raise gate.GateError('Invalid private resource intent or target drift') from None


async def bounded(conn):
    # Session only; no ALTER ROLE/database configuration or larger timeouts.
    await conn.execute("SET statement_timeout='10s'; SET lock_timeout='1500ms'; SET idle_in_transaction_session_timeout='10s'")


class TimedConnection:
    """Delegates to real asyncpg; aggregate timings contain no SQL/parameters."""
    def __init__(self,connection,report,role):
        self.connection=connection;self.report=report;self.role=role

    def transaction(self,*args,**kwargs):return self.connection.transaction(*args,**kwargs)

    async def call(self,method,sql,*args,**kwargs):
        operation=sql.strip().split()[0].upper()
        if operation not in {'SELECT','INSERT','UPDATE','DELETE','SET','CREATE'}:operation='OTHER'
        match=re.search(r'(?:FROM|INTO|UPDATE)\s+([a-z_]+\.[a-z_]+)',sql,re.I)
        table=match[1].lower() if match and match[1].lower() in gate.TABLES else 'catalog_or_control'
        label=self.role+' '+method+' '+operation+' '+table
        stats=self.report.setdefault('sql_timings',{}).setdefault(label,{'count':0,'total_ms':0,'max_ms':0,'errors':{}})
        start=time.monotonic()
        try:return await getattr(self.connection,method)(sql,*args,**kwargs)
        except Exception as exc:
            code=getattr(exc,'sqlstate',None)
            if not isinstance(code,str) or not re.fullmatch(r'[A-Z0-9]{5}',code):code=type(exc).__name__
            stats['errors'][code]=stats['errors'].get(code,0)+1
            self.report['last_sql_error_step']=label  # Also records expected denials.
            raise
        finally:
            elapsed=round((time.monotonic()-start)*1000,2)
            stats['count']+=1;stats['total_ms']=round(stats['total_ms']+elapsed,2)
            stats['max_ms']=max(stats['max_ms'],elapsed)

    async def fetch(self,sql,*a,**k):return await self.call('fetch',sql,*a,**k)
    async def fetchrow(self,sql,*a,**k):return await self.call('fetchrow',sql,*a,**k)
    async def fetchval(self,sql,*a,**k):return await self.call('fetchval',sql,*a,**k)
    async def execute(self,sql,*a,**k):return await self.call('execute',sql,*a,**k)


class TimedPool:
    def __init__(self,pool,report,role):self.pool=pool;self.report=report;self.role=role
    @asynccontextmanager
    async def acquire(self):
        async with self.pool.acquire() as conn:
            await bounded(conn)
            yield TimedConnection(conn,self.report,self.role)
    async def close(self):
        import asyncio
        try:await asyncio.wait_for(self.pool.close(),10)
        except Exception:
            self.pool.terminate()
            raise


async def resolve(conn,plan):
    """Exact equality lookups recover generated IDs even before response delivery."""
    accounts=await conn.fetch('SELECT id,email,raw_user_meta_data FROM auth.users WHERE email=ANY($1::text[])',plan['emails'])
    for row in accounts:
        metadata=json.loads(row['raw_user_meta_data']) if isinstance(row['raw_user_meta_data'],str) else row['raw_user_meta_data']
        if metadata.get('vq_gate_run')!=plan['nonce']:raise gate.GateError('Account marker drift; recovery refuses deletion')
    challenges=await conn.fetch('SELECT id,slug,title FROM public.challenges WHERE slug=ANY($1::text[])',plan['slugs'])
    for row in challenges:
        if row['title'] not in ('Permission gate fixture','denied'):
            raise gate.GateError('Challenge marker drift; recovery refuses deletion')
    for key,table,field,expected in [('quests','public.quests','title',['Permission fixture']*2),
                                    ('badges','public.badges','name',['permission-'+plan['nonce']+'-'+str(i) for i in range(3)])]:
        rows=await conn.fetch('SELECT id,'+field+' FROM '+table+' WHERE id=ANY($1::uuid[])',plan[key])
        for row in rows:
            index=plan[key].index(str(row['id']))
            if row[field]!=expected[index]:raise gate.GateError('Fixture marker drift; recovery refuses deletion')
    return [row['id'] for row in accounts],[row['id'] for row in challenges]


async def assert_unused(conn,plan):
    users,challenges=await resolve(conn,plan)
    if users or challenges:raise gate.GateError('Resource intent is already used; live replay refused')
    for key,table in [('quests','public.quests'),('badges','public.badges'),('xp','public.xp_transactions'),
                      ('awards','public.user_badges'),('streaks','public.streak_activity')]:
        if await conn.fetchval('SELECT count(*) FROM '+table+' WHERE id=ANY($1::uuid[])',plan[key]):
            raise gate.GateError('Predeclared resource ID collision; no writes permitted')


async def reject_external_references(conn,users,challenges,plan):
    """Refuse cascades/cleanup if an unrelated actor or definition references us."""
    for table in ('submissions','user_challenge_progress','xp_transactions'):
        if await conn.fetchval('SELECT count(*) FROM public.'+table+
                ' WHERE challenge_id=ANY($1::uuid[]) AND NOT(user_id=ANY($2::uuid[]))',challenges,users):
            raise UnrelatedFixtureReference('Unrelated fixture reference; cleanup refused')
    checks=[('SELECT count(*) FROM public.user_badges WHERE badge_id=ANY($1::uuid[]) AND NOT(user_id=ANY($2::uuid[]))',plan['badges'],users),
        ('SELECT count(*) FROM public.admin_audit_log WHERE target_id=ANY($1::uuid[]) AND NOT(admin_user_id=ANY($2::uuid[]))',challenges,users),
        ('SELECT count(*) FROM public.user_roles WHERE granted_by=ANY($1::uuid[]) AND NOT(user_id=ANY($2::uuid[]))',users,users),
        ('SELECT count(*) FROM public.challenge_prerequisites WHERE (challenge_id=ANY($1::uuid[]) OR prerequisite_id=ANY($1::uuid[])) AND NOT(challenge_id=ANY($1::uuid[]) AND prerequisite_id=ANY($1::uuid[]))',challenges,challenges),
        ('SELECT count(*) FROM public.quest_challenges WHERE (quest_id=ANY($1::uuid[]) OR challenge_id=ANY($2::uuid[])) AND NOT(quest_id=ANY($1::uuid[]) AND challenge_id=ANY($2::uuid[]))',plan['quests'],challenges)]
    for sql,left,right in checks:
        # The prerequisite predicate uses one placeholder; do not send an extra arg.
        args=(left,) if '$2' not in sql else (left,right)
        if await conn.fetchval(sql,*args):raise UnrelatedFixtureReference('Unrelated fixture reference; cleanup refused')


async def cleanup(conn,client,headers,plan,report):
    """Idempotent transaction + supported Auth deletion; no retry loop for writes."""
    await bounded(conn)
    async with conn.transaction():
        users,challenges=await resolve(conn,plan)
        # Key-share FK insertions cannot race a checked parent-row deletion.
        # Lock only this plan's rows, not whole platform/application tables.
        for table,ids in [('public.profiles',users),('public.challenges',challenges),
                          ('public.quests',plan['quests']),('public.badges',plan['badges'])]:
            await conn.fetch('SELECT id FROM '+table+' WHERE id=ANY($1::uuid[]) FOR UPDATE',ids)
        await reject_external_references(conn,users,challenges,plan)
        report['resolved_account_count']=len(users);report['resolved_challenge_count']=len(challenges)
        # Audits and XP FKs must be removed before submissions/challenges/accounts.
        await conn.execute('DELETE FROM public.admin_audit_log WHERE admin_user_id=ANY($1::uuid[]) OR target_id=ANY($2::uuid[])',users,challenges)
        await conn.execute('DELETE FROM public.xp_transactions WHERE user_id=ANY($1::uuid[])',users)
        await conn.execute('DELETE FROM public.submissions WHERE user_id=ANY($1::uuid[])',users)
        await conn.execute('DELETE FROM public.challenges WHERE id=ANY($1::uuid[])',challenges)
        await conn.execute('DELETE FROM public.quests WHERE id=ANY($1::uuid[])',plan['quests'])
        await conn.execute('DELETE FROM public.badges WHERE id=ANY($1::uuid[])',plan['badges'])
    report['fixture_transaction_committed']=True
    report['auth_delete_statuses']=[]
    for identifier in users:
        deleted=client.delete('/auth/v1/admin/users/'+str(identifier),headers=headers)
        absent=client.get('/auth/v1/admin/users/'+str(identifier),headers=headers)
        report['auth_delete_statuses'].append({'delete':deleted.status_code,'verify':absent.status_code})
        if deleted.status_code not in (200,204,404) or absent.status_code!=404:
            raise gate.GateError('Exact Auth account cleanup failed; journal retained')
    async with conn.transaction(readonly=True):
        left_users,left_challenges=await resolve(conn,plan)
        if left_users or left_challenges:raise gate.GateError('Journal-owned resources remain')
        for key,table in [('quests','public.quests'),('badges','public.badges'),('xp','public.xp_transactions'),
                          ('awards','public.user_badges'),('streaks','public.streak_activity')]:
            if await conn.fetchval('SELECT count(*) FROM '+table+' WHERE id=ANY($1::uuid[])',plan[key]):
                raise gate.GateError('Journal-owned fixture rows remain')
        if await conn.fetchval('SELECT count(*) FROM public.profiles WHERE id=ANY($1::uuid[])',users):
            raise gate.GateError('Journal account profile remains')
    report['resources_absent']=True
